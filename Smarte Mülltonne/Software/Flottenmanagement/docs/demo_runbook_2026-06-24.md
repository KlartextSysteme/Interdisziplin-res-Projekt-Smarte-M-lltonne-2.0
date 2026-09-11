# Demo-Runbook 2026-06-24

Stand: Testtag 2026-06-24, FH Soest.

Ziel: Web-App, FastAPI-Backend, TCP-Bridge und Pico arbeiten ueber dasselbe
Demo-Netz zusammen. Die Web-App schreibt Hardware-Kommandos in die Backend-Queue,
die TCP-Bridge holt sie dort ab und der Pico quittiert sie sichtbar per LED.

## Ergebnis des heutigen End-to-End-Tests

Der komplette Pfad funktioniert:

```text
Dashboard Hardware-Button
-> POST /bins/22/command
-> Backend-Queue
-> TCP-Bridge pollt /bins/22/pending-command
-> Pico bekommt CMD_*
-> Pico sendet ACK/STATUS/ARRIVED
-> TCP-Bridge postet /bins/22/ack und /bins/22/telemetry
-> Dashboard/Backend sehen den quittierten Zustand
```

Verifizierte Signale:

- Pico verbindet sich im Demo-WLAN mit `192.168.50.102`.
- Mac/Ethernet im Demo-Netz ist `192.168.50.10`.
- NanoRouter/Demo-Gateway ist `192.168.50.1`.
- Backend laeuft auf `127.0.0.1:8000`.
- TCP-Bridge lauscht auf `0.0.0.0:50002`.
- Test-Tonne fuer FH Campus ist `bin_id=22`.
- Klick auf Hardware-Buttons in der Web-App loest LED-Flackern am Test-Pico aus.
- `command-history` zeigt neue Commands mit gesetztem `ack_at`.

Beispiel fuer einen erfolgreichen Backend-Nachweis:

```text
[
  {"action":"goto_street","bin_id":22,"id":6,"ack_at":"2026-06-24T13:42:36.114060"},
  {"action":"goto_street","bin_id":22,"id":5,"ack_at":"2026-06-24T13:42:20.980394"},
  {"action":"goto_street","bin_id":22,"id":4,"ack_at":"2026-06-24T13:41:00.350071"}
]
```

## Netzwerk-Aufbau

Heute stabiler Demo-Aufbau:

```text
FH-WLAN / Internet
  Mac WLAN en0, z.B. 10.119.x.x

Privates Demo-Netz
  TP-Link TL-WR802N / SmartBinDemo
  Router-IP: 192.168.50.1
  Mac Ethernet: 192.168.50.10
  Pico WLAN: 192.168.50.102
```

Wichtig:

- Das Pico/Bridge-Netz braucht keinen Internetzugang.
- Der Mac darf gleichzeitig im FH-WLAN bleiben.
- Ethernet zum NanoRouter sollte keine Default-Route bekommen, damit das FH-WLAN
  weiterhin Internet liefert.
- WISP-Uplink zum FH-WLAN ist fuer den Pico-Test nicht noetig.

## TP-Link TL-WR802N Settings

Bewaehrte Demo-Einstellungen:

- Operation Mode: `WISP`
- Interne AP-SSID: `SmartBinDemo`
- Interner AP-Key: `SmartBin2026!`
- LAN-IP des TP-Link: `192.168.50.1`
- DHCP im Demo-Netz aktiv, damit Pico eine Adresse wie `192.168.50.102` bekommt.

Im TP-Link-Webinterface bedeutet:

- `Client Setting` / `SSID(to be bridged)` ist das externe WLAN, das der TP-Link
  als WISP-Client nutzen wuerde.
- `AP Setting` / `Wireless Network Name` ist das interne Demo-WLAN, in das sich
  Pico und ggf. weitere Demo-Geraete einloggen.

Fuer unseren heutigen lokalen Demo-Pfad ist entscheidend: Pico und Mac muessen im
internen `SmartBinDemo`-Netz sein. Der WISP-Uplink darf auch noch fehlen.

## Mac-Netz pruefen

WLAN-IP:

```bash
ipconfig getifaddr en0
```

Ethernet-IP, Interface kann je nach Adapter anders heissen:

```bash
ipconfig getifaddr en12
ipconfig getifaddr en11
ipconfig getifaddr en10
```

Default Route pruefen:

```bash
route -n get default | grep interface
```

Erwartung:

- Default Interface bleibt WLAN, z.B. `en0`.
- Ethernet hat die statische Demo-IP `192.168.50.10`.
- Router/Gateway auf Ethernet moeglichst leer lassen. Wenn macOS meckert, darf
  der Router auf `192.168.50.1` stehen, aber die Default Route sollte weiter
  ueber WLAN laufen.

## Terminal-Aufteilung fuer die Demo

Am wenigsten verwirrend sind vier feste Terminal-Fenster:

1. Backend
2. TCP-Bridge
3. Frontend/Web-App
4. Pico/mpremote

Nichts in diesen Fenstern schliessen, solange die Demo laeuft.

## Terminal 1: Backend starten

```bash
cd "/Users/jonaswiesner/Documents/GitHub/Interdisziplinäres Projekt: Smarte Mülltonne 2.0/Smarte Mülltonne/Software/Flottenmanagement/backend"
.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

Healthcheck in einem zusaetzlichen Terminal:

```bash
curl http://127.0.0.1:8000/health
```

Erwartet:

```text
{"status":"ok"}
```

## Terminal 2: TCP-Bridge starten

Wichtig: Fuer die FH-Campus-Tonne `--bin-id 22` verwenden.

```bash
cd "/Users/jonaswiesner/Documents/GitHub/Interdisziplinäres Projekt: Smarte Mülltonne 2.0/Smarte Mülltonne/Software/Flottenmanagement"
python bridge/tcp_bridge.py --host 0.0.0.0 --port 50002 --bin-id 22 --backend http://127.0.0.1:8000
```

Erwartete Bridge-Logs:

```text
TCP bridge listening on ('0.0.0.0', 50002); backend=http://127.0.0.1:8000 bin_id=22
Pico connected from ('192.168.50.102', ...)
pico: Pico ist bereit
pico: STATUS:STANDBY
```

## Terminal 3: Web-App starten

Für eine stabile Vorführung:

```bash
cd "/Users/jonaswiesner/Documents/GitHub/Interdisziplinäres Projekt: Smarte Mülltonne 2.0/Smarte Mülltonne/Software/Flottenmanagement/frontend"
npm run demo
```

Das baut die Web-App statisch und serviert den `out`-Ordner auf Port `3000`.
Falls die App plötzlich ungestylt aussieht, läuft sehr wahrscheinlich ein
staler Next-Dev-Server oder das CSS-Asset wurde nicht geladen. Dann Port `3000`
beenden, `.next` löschen und `npm run demo` neu starten.

Für Entwicklung mit Hot Reload:

```bash
cd "/Users/jonaswiesner/Documents/GitHub/Interdisziplinäres Projekt: Smarte Mülltonne 2.0/Smarte Mülltonne/Software/Flottenmanagement/frontend"
npm run dev -- --hostname 0.0.0.0 --port 3000
```

Browser:

```text
http://127.0.0.1:3000/dashboard
```

Nicht `0.0.0.0` im Browser oeffnen. `0.0.0.0` ist nur die Server-Bind-Adresse.

Falls Port 3000 belegt ist:

```bash
npm run dev -- --hostname 0.0.0.0 --port 3001
```

Dann:

```text
http://127.0.0.1:3001/dashboard
```

## Terminal 4: Test-Pico starten

Testdatei:

```text
Smarte Mülltonne/Software/Flottenmanagement/firmware/pico_touchpanel/bridge_command_led_test.py
```

Start:

```bash
cd "/Users/jonaswiesner/Documents/GitHub/Interdisziplinäres Projekt: Smarte Mülltonne 2.0"
python -m mpremote connect /dev/cu.usbmodem214301 run "Smarte Mülltonne/Software/Flottenmanagement/firmware/pico_touchpanel/bridge_command_led_test.py"
```

Der USB-Port kann anders heissen. Suchen mit:

```bash
ls /dev/cu.usbmodem*
```

Erwartete Pico-Ausgabe:

```text
Wi-Fi connected: ('192.168.50.102', '255.255.255.0', '192.168.50.1', '192.168.50.1')
Connecting bridge: 192.168.50.10 50002
pico -> Pico ist bereit
pico -> STATUS:STANDBY
Bridge connected. Waiting for CMD_*.
```

## Web-App-Test

1. Dashboard oeffnen.
2. Tonne `FH Campus` / `bin_id=22` auswaehlen.
3. Hardware-Button `Abholung` klicken.
4. Am Pico muss die LED sichtbar flackern.
5. Bridge muss `CMD_GOTO_STREET` loggen.
6. `command-history` muss einen neuen Eintrag mit `ack_at` zeigen.

Check per curl:

```bash
curl http://127.0.0.1:8000/bins/22/command-history
```

Ein direkter Command ohne Web-App:

```bash
curl -X POST http://127.0.0.1:8000/bins/22/command \
  -H "Content-Type: application/json" \
  -d '{"action":"goto_street"}'
```

## Admin-Reset für wiederholbare Demo-Zustände

Für mehrere Demo-Durchläufe gibt es einen schlanken Admin-Bereich:

```text
http://127.0.0.1:3000/admin
```

Dort können alle Tonnenwerte auf Knopfdruck neu gesetzt werden:

- `Schichtbeginn`: realistischer Startzustand mit gemischten Füllständen
- `FH-Fokus`: FH-Campus-Tonne voll, passend für Hardwaretests mit `bin_id=22`
- `Hohe Auslastung`: viele volle Tonnen, gut für Routen- und Kapazitätsdemo
- `Ruhiger Tag`: wenige Abholungen, gut für Basischecks
- `Zufallswerte`: alle Tonnen neu würfeln

Der Admin-Bereich kann außerdem Routen, offene Meldungen und alte Hardware-Befehle
löschen, eine Simulationsgeschwindigkeit setzen und die Simulation bei Bedarf
pausiert starten. Über das Seed-Feld lässt sich ein zufälliger Zustand exakt
wiederholen.

Direkter Backend-Call, falls die Web-App nicht offen ist:

```bash
curl -X POST http://127.0.0.1:8000/admin/demo/reset \
  -H "Content-Type: application/json" \
  -d '{"profile":"hardware_focus","seed":22,"clear_history":true,"include_alerts":false,"sim_speed":1,"sim_paused":false}'
```

## Einführung für den Operator

Die Web-App hat eine kurze Leitstand-Einführung für den Müllwagen-Operator:

- startet beim ersten Dashboard-Besuch automatisch
- kann über den Header-Button `Einführung` jederzeit erneut geöffnet werden
- führt durch Leitstand, Routenplanung, Flotte, Tonnenbefehle, Karte,
  Detail-Panels und Live-Status
- ist bewusst aus Sicht der Primärpersona Stefan Krüger formuliert:
  Müllwagenfahrer und Tour-Disponent, mit wenig Zeit für verschachtelte Menüs
- funktioniert lokal auf `localhost` genauso wie in einem späteren Deployment,
  weil der Zustand nur im Browser-`localStorage` gespeichert wird.
- Reset für einen erneuten Erstnutzungs-Test in der Browser-Konsole:
  `localStorage.removeItem("smart-bin-operator-tour-v1")`

Für eine Präsentation aus Nutzersicht:

1. Dashboard öffnen.
2. Optional `Einführung` klicken.
3. Durch die Tour gehen und die Rolle des Operators erklären.
4. Danach `FH Campus` auswählen und `Abholung` klicken.
5. LED-Flackern am Pico als Hardware-Nachweis zeigen.

## Button- und Command-Mapping

Frontend/Backend Action:

```text
goto_street
return_home
stop
```

Bridge uebersetzt fuer den Pico:

```text
goto_street  -> CMD_GOTO_STREET
goto_pickup  -> CMD_GOTO_STREET
goto_home    -> CMD_RETURN_HOME
return_home  -> CMD_RETURN_HOME
stop         -> CMD_STOP
```

Pico antwortet:

```text
ACK CMD_GOTO_STREET
STATUS:LINE_FOLLOWING
ARRIVED: STREET
STATUS:WAIT_AT_STREET
```

Die Bridge bestaetigt danach ans Backend:

```text
POST /bins/22/ack
POST /bins/22/telemetry
```

## Relevante Dateien

- TCP-Bridge:
  `Smarte Mülltonne/Software/Flottenmanagement/bridge/tcp_bridge.py`
- Laptop/Pico-Simulator:
  `Smarte Mülltonne/Software/Flottenmanagement/bridge/pico_tcp_simulator.py`
- Test-Pico mit LED-Signal:
  `Smarte Mülltonne/Software/Flottenmanagement/firmware/pico_touchpanel/bridge_command_led_test.py`
- Einfacher Netzwerk-/LED-Test:
  `Smarte Mülltonne/Software/Flottenmanagement/firmware/pico_touchpanel/network_led_test.py`
- Touchpanel-Firmware Config:
  `Smarte Mülltonne/Software/Flottenmanagement/firmware/pico_touchpanel/config.py`
- Pico TCP Client fuer echte Touchpanel-Firmware:
  `Smarte Mülltonne/Software/Flottenmanagement/firmware/pico_touchpanel/tcp_bridge_client.py`
- Web-App API Helper:
  `Smarte Mülltonne/Software/Flottenmanagement/frontend/lib/api.ts`
- Dashboard-Hardware-Buttons:
  `Smarte Mülltonne/Software/Flottenmanagement/frontend/app/dashboard/components/FleetPanel.tsx`
- Operator-Einführung:
  `Smarte Mülltonne/Software/Flottenmanagement/frontend/app/dashboard/components/OperatorTour.tsx`
- Admin-Reset-Seite:
  `Smarte Mülltonne/Software/Flottenmanagement/frontend/app/admin/page.tsx`
- Admin-Reset-API:
  `Smarte Mülltonne/Software/Flottenmanagement/backend/routers/admin_demo.py`

## Fallback ohne echten Pico

Falls der Pico oder USB/Serial Stress macht, kann die Bridge gegen den lokalen
Simulator getestet werden:

```bash
cd "/Users/jonaswiesner/Documents/GitHub/Interdisziplinäres Projekt: Smarte Mülltonne 2.0/Smarte Mülltonne/Software/Flottenmanagement"
python bridge/pico_tcp_simulator.py --host 127.0.0.1 --port 50002 --arrival-delay 3
```

Dann Web-App wie oben bedienen. Der Simulator quittiert die Commands anstelle
des Picos.

## Troubleshooting

Backend-Port belegt:

```bash
lsof -iTCP:8000 -sTCP:LISTEN -n -P
kill <PID>
```

Pico-USB-Port durch anderes Terminal belegt:

```bash
lsof /dev/cu.usbmodem214301
kill <PID>
```

Bridge bekommt keinen Pico:

- Ist Pico im WLAN `SmartBinDemo`?
- Stimmt `BRIDGE_HOST = "192.168.50.10"` in der Testdatei/Firmware?
- Laeuft die Bridge auf `--host 0.0.0.0 --port 50002`?
- Hat der Mac auf Ethernet wirklich `192.168.50.10`?

Web-App laedt nicht:

- Frontend-Terminal offen lassen.
- URL `http://127.0.0.1:3000/dashboard` verwenden.
- Bei belegtem Port auf `3001` ausweichen.
- Backend-Healthcheck pruefen: `curl http://127.0.0.1:8000/health`.

Commands kommen nicht an:

- Bridge muss mit `--bin-id 22` laufen.
- In der Web-App muss `FH Campus` ausgewaehlt sein.
- `curl http://127.0.0.1:8000/bins/22/pending-command` pruefen.
- `curl http://127.0.0.1:8000/bins/22/command-history` pruefen.

## Merksatz

Backend legt Commands ab. Bridge holt Commands ab. Pico quittiert. Das Dashboard
ist nur die Bedienoberflaeche fuer denselben Backend-Briefkasten.
