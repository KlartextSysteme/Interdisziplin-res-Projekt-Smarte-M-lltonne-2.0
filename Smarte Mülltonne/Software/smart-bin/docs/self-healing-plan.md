# Self-Healing / Resilienz — Plan für spätere Umsetzung

Stand 2026-07-04. Sammlung der Robustheits-Lücken, die beim Hardware-Testlauf real
aufgetreten sind, plus konkrete Fixes. **Noch nicht umgesetzt** — dieses Dokument ist
die Vorlage für eine spätere Umsetzungs-Session.

## Baseline: was sich heute schon selbst heilt

- **Pico ↔ WLAN (Nano-Router):** `Quellcode/Client/tcp_bridge_client.py` prüft
  `wlan.isconnected()` und verbindet neu.
- **Pico ↔ Bridge (TCP):** reconnectet nach Abriss automatisch (mehrfach beobachtet).
- **Bridge ↔ Backend:** `_poll_commands`-Schleife mit `try/except` übersteht kurzes
  Backend-Ausfallen.
- **Leitstand ↔ Backend (WebSocket):** `frontend/lib/useWebSocket.ts` `onclose →
  reconnect nach 3 s`.
- **Befehls-Zustellung:** at-least-once seit dem Bridge-Fix vom 2026-07-04
  (`_send_backend_command_to_pico` markiert erst nach erfolgreichem Senden; verlorener
  Befehl wird nach Reconnect erneut zugestellt).

## Offene Lücken (heute real getroffen)

1. Firmware-Crash friert den Pico ein (REPL) → nur per Stromtrennen wiederbelebbar.
2. Backend/Bridge-Prozesse haben keinen Supervisor → Crash bleibt unten (manuell
   neu gestartet).
3. Stale-Befehle können in der Queue hängen (heute manuell abgeräumt).
4. Grundursache: WLAN/TCP-Resets am Nano-Router (wird nur toleriert).

---

## Task 1 — Pico-Firmware: Watchdog + Crash-Reset (Prio hoch)

**Problem:** Unbehandelte Exception in `main.py` → Programm endet im REPL, Display
eingefroren, Touch tot. Kein automatischer Neustart.

**Design:**
- In `Quellcode/Client/main.py` einen Hardware-Watchdog anlegen:
  `from machine import WDT; wdt = WDT(timeout=8000)` (max. ~8388 ms auf RP2040).
- Im Haupt-`while True`-Loop pro Iteration `wdt.feed()` aufrufen (nach
  `controller.run()`). Solange der Loop läuft, kein Reset; hängt/crasht er, löst der
  WDT nach dem Timeout `machine.reset()` aus → Firmware bootet neu, Pico verbindet
  sich selbst wieder (WLAN/Bridge heilen bereits).
- Zusätzlich den Loop-Body in `try/except` wrappen: bei Exception `print` + kurze
  Pause, damit ein einzelner Fehler nicht sofort in den WDT-Reset läuft, aber ein
  echter Hänger trotzdem gefangen wird. **Nicht** die WDT-Fütterung in den
  `except`-Zweig legen (sonst maskiert man Dauerfehler).

**Achtung:** WDT lässt sich auf dem RP2040 nach dem Start **nicht deaktivieren** —
beim Flashen/Debuggen via `mpremote` bedenken (langes `fs cp` ohne Feed → Reset).
Für Entwicklung ggf. per Config-Flag (`ENABLE_WDT`) abschaltbar machen.

**Akzeptanz:** Künstlich provozierte Exception im Loop → Pico bootet innerhalb
~8 s selbst neu, Display + Touch + Bridge-Verbindung kommen von allein zurück.

**Dateien:** `Quellcode/Client/main.py`, ggf. `config.py` (`ENABLE_WDT`).

---

## Task 2 — Backend + Bridge unter Supervisor (Prio hoch)

**Problem:** `uvicorn` (Backend :8000) und `tcp_bridge.py` (:50002) laufen als nackte
Prozesse; Crash = manueller Neustart.

**Design (eine Option wählen):**
- **Einfach/portabel:** Start-Skript mit Auto-Restart-Loop, z.B.
  `scripts/run_backend.sh` / `scripts/run_bridge.sh` je:
  `while true; do <cmd>; echo "restart $(date)"; sleep 2; done`.
- **Sauber (macOS-Demo-Rechner):** `launchd`-plists mit `KeepAlive=true`.
- **Sauber (Linux):** `systemd`-Units mit `Restart=always`.
- Logs weiter nach Datei (Bridge bereits `/tmp/tcp_bridge.log`); Backend-Log analog.

**Akzeptanz:** `kill` des Backend- bzw. Bridge-Prozesses → Prozess ist binnen weniger
Sekunden wieder oben, Pico/Frontend verbinden sich automatisch neu (heilt bereits).

**Dateien:** neue `scripts/` (Wrapper) bzw. `deploy/`-plists/units. Kein App-Code.

---

## Task 3 — Befehls-TTL / Stale-Command-Expiry (Prio mittel)

**Problem:** Ein nie zugestellter/geackter Befehl bleibt „pending" an der Queue-Spitze
und blockiert bzw. feuert verspätet (heute #18/#19 `return_home` manuell abgeräumt).

**Design:**
- Backend `routers/commands.py`: beim `pending-command`-Abruf Kommandos älter als N s
  (z.B. 30 s) ohne Ack als **expired** markieren (eigener Status oder `ack_at` mit
  `success=false, error="expired"`), statt sie ewig zurückzugeben.
- Alternativ/zusätzlich Frontend: Kommando-Buttons kurz sperren + Feedback, wenn kein
  Ack kommt, damit nicht 5× `return_home` in die Queue läuft.

**Akzeptanz:** Ein Befehl, der 30 s lang nicht geackt wird, verschwindet aus
`pending-command`; ein späterer Klick erzeugt einen frischen Befehl, der sauber
zugestellt wird.

**Dateien:** `backend/routers/commands.py`, optional
`frontend/app/dashboard/components/FleetPanel.tsx`.

---

## Task 4 — WLAN-Stabilität am Nano-Router (Prio niedrig, Grundursache)

**Problem:** Die eigentlichen TCP-Resets kommen vermutlich von WLAN-Hickups am
Nano-Router. Task 1–3 tolerieren die Folgen, beseitigen aber nicht die Ursache.

**Ansätze (nicht spezifiziert, zum Untersuchen):**
- Router-Firmware/Kanal/Sendeleistung prüfen; feste IP/Lease für den Pico.
- Pico-seitig TCP-Keepalive/kürzere Reconnect-Intervalle in `tcp_bridge_client.py`.
- Signalstärke am Fahrweg messen (WAIT_AT_STREET-Position vs. Router-Standort).

**Akzeptanz:** Deutlich seltenere `Connection reset by peer` im Bridge-Log über eine
längere Fahrsession.

---

## Reihenfolge-Empfehlung

**Task 1 + 2 zuerst** (schließen die zwei Lücken, die wir heute real getroffen haben:
eingefrorene Firmware + manuell neugestartete Prozesse). Dann Task 3 (Komfort/Sauberkeit),
Task 4 nur bei Bedarf (Grundursachen-Analyse).
