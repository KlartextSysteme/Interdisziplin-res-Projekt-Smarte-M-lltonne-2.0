# Hardwarevertrag: Legacy-Pico ↔ TCP-Bridge ↔ Backend

> Stand: Mai 2026. Dieser Vertrag beschreibt den ersten Vertical Slice mit der
> bestehenden MicroPython-Firmware aus `Software/Quellcode/Client`.

## Zielbild

Die alte Pico-Firmware bleibt der autonome Echtzeit-Kern: Linienverfolgung,
Motorsteuerung, Hindernisverhalten, Füllstandsmessung, Buttons, LEDs und Buzzer
laufen lokal auf dem Pico. Die Web-App übernimmt Flottenmanagement,
Visualisierung und Missionsbefehle.

Eine kleine Bridge verbindet beide Welten:

```text
Pico MicroPython
  TCP Zeilenprotokoll
  ↕
TCP Bridge auf Laptop (:50002)
  HTTP/JSON
  ↕
FastAPI Backend (:8000)
  ↕
Dashboard / Agent
```

Damit bleibt das Team für den Prof flexibel:

- Kurzfristig: alter Pico-Code bleibt nutzbar, TCP-Demo funktioniert weiter.
- Langfristig: Bridge kann durch direkte HTTP-Polling-Firmware ersetzt werden,
  ohne Dashboard und Backend umzubauen.

---

## Lokalbetrieb

Auf dem Server-Laptop:

```bash
# Terminal 1
cd Software/smart-bin/backend
.venv/bin/uvicorn main:app --port 8000

# Terminal 2
cd Software/smart-bin
python bridge/tcp_bridge.py --bin-id 1 --backend http://localhost:8000

# Terminal 3
cd Software/smart-bin/frontend
npm run dev
```

Im alten Pico-Code:

```python
SERVER_IP = "<IP des Server-Laptops>"
SERVER_PORT = 50002
```

Ein Laptop reicht. Ein zweiter Laptop kann optional nur das Dashboard im Browser
öffnen.

---

## Pico ↔ Bridge: TCP-Zeilenprotokoll

Transport:

- TCP-Server: Bridge auf Port `50002`
- Client: Pico verbindet sich zum Laptop
- Framing: eine UTF-8-Zeile pro Nachricht, beendet mit `\n`

### Handshake

Pico sendet nach Connect:

```text
Pico ist bereit
```

Bridge interpretiert das als `STANDBY`-Telemetrie für das Backend.

### Statusmeldungen

Pico sendet regelmäßig:

```text
STATUS:STANDBY
STATUS:FULL
STATUS:LINE_FOLLOWING
STATUS:LINE_LOST
STATUS:OBSTACLE
STATUS:USER_PAUSED
STATUS:WAIT_AT_STREET
STATUS:EMPTIED
```

Bridge übersetzt diese Zustände in `POST /bins/{bin_id}/telemetry`.

### Ankunft

Pico sendet:

```text
ARRIVED: STREET
ARRIVED: HOME
```

Bridge setzt daraus:

| Pico | Backend-Telemetrie |
|---|---|
| `ARRIVED: STREET` | `pico_state = WAIT_AT_STREET` |
| `ARRIVED: HOME` | `pico_state = STANDBY` |

### Commands

Bridge sendet an den Pico:

```text
CMD_GOTO_STREET
CMD_RETURN_HOME
CMD_STOP
```

Pico bestätigt:

```text
ACK CMD_GOTO_STREET
ACK CMD_RETURN_HOME
ACK CMD_STOP
```

Bridge bestätigt danach zurück an den Pico:

```text
ACK_RECEIVED CMD_GOTO_STREET
ACK_RECEIVED CMD_RETURN_HOME
ACK_RECEIVED CMD_STOP
```

Das erhält die bestehende Hard-Offline-Startsequenz der alten Firmware.

---

## Bridge ↔ Backend: HTTP/JSON

### 1. Bridge pollt Backend-Commands

```http
GET /bins/{bin_id}/pending-command
```

Antwort, wenn kein Command wartet:

```json
null
```

Antwort mit Command:

```json
{
  "id": 42,
  "bin_id": 1,
  "action": "goto_street",
  "params": null,
  "created_at": "2026-05-20T12:00:00+00:00"
}
```

### 2. Command-Mapping

| Backend `action` | Bridge → Pico |
|---|---|
| `goto_street` / `go_to_street` / `start` | `CMD_GOTO_STREET` |
| `return_home` / `go_home` | `CMD_RETURN_HOME` |
| `stop` / `pause` / `lock` | `CMD_STOP` |

Nicht unterstützte Commands werden von der Bridge als fehlgeschlagen bestätigt,
damit die Queue nicht blockiert.

### 3. Bridge bestätigt Backend-Command

```http
POST /bins/{bin_id}/ack
Content-Type: application/json
```

```json
{
  "command_id": 42,
  "success": true,
  "pico_state": "LINE_FOLLOWING"
}
```

Bei Fehler:

```json
{
  "command_id": 42,
  "success": false,
  "error": "unsupported action: open_lid"
}
```

### 4. Bridge meldet Pico-Telemetrie

```http
POST /bins/{bin_id}/telemetry
Content-Type: application/json
```

Minimal:

```json
{
  "pico_state": "STANDBY"
}
```

Optional später:

```json
{
  "pico_state": "LINE_FOLLOWING",
  "fill_level": 87,
  "battery": 64,
  "deckel_offen": false,
  "target_destination": "STREET",
  "line_position": 12,
  "obstacle_cm": 48.5
}
```

Backend-Mapping:

| `pico_state` | Dashboard-Status |
|---|---|
| `STANDBY`, `FULL`, `USER_PAUSED` | `idle` |
| `LINE_FOLLOWING`, `LINE_LOST`, `OBSTACLE`, `ARRIVED` | `en_route` |
| `WAIT_AT_STREET` | `idle` |
| `EMPTIED` | `emptied` |

`FULL` setzt den Füllstand mindestens auf `95`, `EMPTIED` setzt ihn auf `0`,
falls kein expliziter `fill_level` mitgesendet wird.

---

## Test-Commands

Command in Backend-Queue legen:

```bash
curl -X POST http://localhost:8000/bins/1/command \
  -H 'Content-Type: application/json' \
  -d '{"action":"goto_street"}'
```

Pico-Status simulieren:

```bash
nc localhost 50002
Pico ist bereit
STATUS:FULL
ACK CMD_GOTO_STREET
ARRIVED: STREET
```

---

## Architekturentscheidung

Für diesen Slice ist TCP kein Gegenentwurf zur Web-App, sondern ein Adapter:

- Der Pico bleibt lokal autonom und echtzeitnah.
- Die Bridge kapselt Transportdetails.
- FastAPI bleibt zentrale Wahrheit für Dashboard, Agent und Commands.
- Ein späterer Wechsel auf direkte HTTP-Polling-Firmware betrifft nur die
  Transport-Schicht, nicht die Flottenmanagement-App.
