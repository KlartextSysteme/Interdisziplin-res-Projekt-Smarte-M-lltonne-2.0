# Demo-Runbook 2026-06-24

Ziel: Web-App, FastAPI-Backend, TCP-Bridge und Pico sprechen ueber ein lokales
WLAN. Der Backend-Briefkasten bleibt die Quelle fuer Web-App-Kommandos:

```text
Dashboard -> POST /bins/1/command -> Backend-Queue
TCP-Bridge -> GET /bins/1/pending-command -> Pico TCP
Pico -> ACK/STATUS/ARRIVED -> TCP-Bridge -> Backend /telemetry + /ack
```

## 1. Netzwerk festlegen

Prioritaet fuer morgen:

1. Handy-Hotspot oder bekanntes 2.4-GHz-WLAN, falls TP-Link-Passwort unklar ist.
2. TP-Link TL-WR802N nur verwenden, wenn SSID/Passwort sicher bekannt sind.
3. Mac und Pico muessen im gleichen Netz sein.

Mac-IP im Demo-WLAN finden:

```bash
ipconfig getifaddr en0
```

Diese IP kommt in die Pico-Datei `firmware/pico_touchpanel/config.py`:

```python
ENABLE_TCP_BRIDGE = True
WLAN_SSID = "<demo-wlan>"
WLAN_PASSWORD = "<demo-passwort>"
BRIDGE_HOST = "<mac-ip>"
BRIDGE_PORT = 50002
```

## 2. Services starten

Terminal 1:

```bash
cd "Smarte Mülltonne/Software/smart-bin/backend"
.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

Terminal 2:

```bash
cd "Smarte Mülltonne/Software/smart-bin"
python bridge/tcp_bridge.py --host 0.0.0.0 --port 50002 --bin-id 1 --backend http://127.0.0.1:8000
```

Terminal 3:

```bash
cd "Smarte Mülltonne/Software/smart-bin/frontend"
npm run dev
```

Dashboard im Browser:

```text
http://localhost:3000/dashboard
```

## 3. Pico-Test

Serielle Ausgabe beobachten. Erwartet:

```text
TCP bridge client aktiv: <mac-ip> 50002
TCP bridge connected: <mac-ip> 50002
```

Bridge-Log erwartet:

```text
Pico connected from ...
pico: Pico ist bereit
```

In der Web-App eine Tonne anklicken und unten auf `Abholung` klicken.
Erwarteter Ablauf:

```text
Backend-Queue: goto_street
Bridge: CMD_GOTO_STREET
Pico: ACK CMD_GOTO_STREET
Pico: STATUS:LINE_FOLLOWING
Pico: ARRIVED: STREET
Dashboard: Position Abholposition
```

## 4. Fallback ohne Pico

Falls Pico/WLAN nicht rechtzeitig stabil wird, koennen Backend, Web-App und
Bridge trotzdem end-to-end gezeigt werden.

Terminal 4:

```bash
cd "Smarte Mülltonne/Software/smart-bin"
python bridge/pico_tcp_simulator.py --host 127.0.0.1 --port 50002 --arrival-delay 3
```

Dann in der Web-App dieselben Hardware-Buttons verwenden.

## 5. Schnelltests per curl

Command direkt in die Queue legen:

```bash
curl -X POST http://127.0.0.1:8000/bins/1/command \
  -H "Content-Type: application/json" \
  -d '{"action":"goto_street"}'
```

Pending Command anschauen:

```bash
curl http://127.0.0.1:8000/bins/1/pending-command
```

Telemetry direkt simulieren:

```bash
curl -X POST http://127.0.0.1:8000/bins/1/telemetry \
  -H "Content-Type: application/json" \
  -d '{"pico_state":"WAIT_AT_STREET","target_destination":"STREET"}'
```
