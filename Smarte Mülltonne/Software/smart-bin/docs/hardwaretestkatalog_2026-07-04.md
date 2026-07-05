# Hardware-Testkatalog (Pico) — Stand 2026-07-04

Offene End-to-End-Tests am **physischen Pico**, die sich seit dem letzten
Hardware-Lauf angesammelt haben. Alle Features sind codeseitig fertig, committet
und `py_compile`-grün — sie brauchen nur noch die Verifikation an der echten Tonne.

## Setup vor den Tests

### A) Pico flashen (`DEV=/dev/cu.usbmodem14301`)

```bash
cd "Smarte Mülltonne/Software"; DEV=/dev/cu.usbmodem14301
mpremote connect port:$DEV fs cp Quellcode/Client/main.py :main.py
mpremote connect port:$DEV fs cp Quellcode/Client/global_controller_test.py :global_controller_test.py
mpremote connect port:$DEV fs cp Quellcode/Client/touchpanel.py :touchpanel.py
mpremote connect port:$DEV fs cp Quellcode/Client/config.py :config.py
# Touchpanel-UI + neues Confirm-Asset (laufende ui.py = firmware-Variante):
mpremote connect port:$DEV fs cp smart-bin/firmware/pico_touchpanel/ui.py :ui.py
mpremote connect port:$DEV fs cp smart-bin/firmware/pico_touchpanel/assets/confirm_report.rle :assets/confirm_report.rle
mpremote connect port:$DEV reset
```

Deckt ab: MUX-Pinout, Füllstand C8, Eco, Party, Meldungen, Deckel-Security.
> Zwei `ui.py` (firmware = läuft auf dem Pico, + `Client/ui.py` = Repo-Konsistenz) —
> auf den Pico kommt die **firmware**-Variante. **Nach dem `fs cp` nicht mehr `fs cat`
> aufrufen** (stoppt die laufende Firmware → sonst nochmal `reset`).

### B) Mac-Seite: Backend + Bridge neu starten (für T3 + T6 zwingend)

Beide **neu starten**, damit die neuen Endpoints/Poller aktiv sind
(Telemetry-`location_state`, `/arm-state`, Bridge-Arm-Poll, `UNAUTHORIZED_OPEN`):

```bash
# Backend (Port 8000)
cd "Smarte Mülltonne/Software/smart-bin/backend" && .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
# Bridge (Port 50002 -> Backend), in eigenem Terminal:
cd "Smarte Mülltonne/Software/smart-bin/bridge" && python tcp_bridge.py --backend http://127.0.0.1:8000 --bin-id 22
```

### C) Verbindung prüfen

- Demo-Netz: Mac = `192.168.50.10`, WLAN `SmartBinDemo`, Bridge `:50002`, Backend `:8000`.
- Nach Pico-Reset im Bridge-Log erwartet: `Pico connected` → `pico: Pico ist bereit` → `STATUS:STANDBY`.
- Falls „alles leer" im Leitstand: Admin-Dashboard → Szenario **Schichtbeginn** setzen.

---

## T1 — MUX-Pinout (fundamental, zuerst testen!)

Neues Pinout: MUX **S0–S3 = GP1–GP4**, **SIG = GP5**, Füllstand auf **Kanal C8**.
US links/rechts unverändert (LEFT=7, RIGHT=6).

- [ ] **Sensoren lesen roh:** auf blankem Weiß alle 5 Linien-Sensoren = 0; Linie
      quer schieben → jeder Kanal schaltet einzeln nacheinander.
- [ ] **Linienverfolgung:** Fahrt auslösen → Position pendelt um 0, wenige
      `LINE_LOST`, kein Rausfahren (wie im 4200-Hz-Referenzlauf).
- [ ] **Hindernis:** Hand vor Frontsensor (<30 cm) → `OBSTACLE_WAIT`.
- [ ] ⚠️ Falls nichts sauber liest → physische MUX-Verdrahtung ≠ GP1–5 prüfen.

## T2 — Füllstand auf Kanal C8

Eigener US-Sensor (statt Front-Sensor), gemeinsamer Trigger GP6.

- [ ] Serieller `Fuellstand-Test`-Log zeigt plausible Abstände/Prozent von **C8**.
- [ ] Tonne füllen/leeren → Füllstand ändert sich; Touchpanel-Statusleiste aktualisiert.

## T3 — Touchpanel-Meldungen → Leitstand

Voraussetzung: Bridge + Backend laufen, Tonne 22 verbunden.

- [ ] Panel: Menü → PIN `12#` → „problem" → **HYGIENE** tippen.
- [ ] Panel zeigt Screen **„Meldung gesendet"** (gelbes Häkchen, gleicher Stil wie „Auswahl bestätigt").
- [ ] Meldung erscheint **live im Leitstand** (Security-Panel, Icon `Sparkles`, „Hygieneproblem gemeldet").
- [ ] Analog **SCHADEN** → Icon `Wrench`, „Beschädigung gemeldet".
- [ ] Operator „Erledigen" → Meldung verschwindet.
- [ ] Bridge-Log: `REPORT:HYGIENE`/`REPORT:DAMAGE` → `POST /security/events`.

## T4 — Eco-Modus (Display dimmen)

Backlight an **GP15** per PWM. Voraussetzung: Backlight physisch an GP15 (via Transistor).

- [ ] Panel: PIN `12#` → „energy" → **ECO** → Display dimmt sichtbar auf ~40 %.
- [ ] Nochmal **ECO** → wieder volle Helligkeit.
- [ ] ⚠️ Falls „voll" dunkler als vorher → GP15 braucht Transistor als Treiber (zu wenig GPIO-Strom).

## T5 — Party-Modus (Easter-Egg)

- [ ] Voraussetzung: Tonne im **Leerlauf** (`AT_HOME`), Platz zum Drehen frei.
- [ ] Panel: PIN-Screen → **`***`** → OK.
- [ ] Tonne dreht sich **zügig auf der Stelle** (~10 s) + Buzzer klopft den
      **„Shave and a haircut"**-Rhythmus.
- [ ] Nach ~10 s: Stop → zurück in den Leerlauf.

## T6 — Unbefugte Deckelöffnung → Alarm

Voraussetzung: **Bridge + Backend neu gestartet** (neuer Arm-State-Poll + Endpoint),
Füllstand-Sensor auf C8 funktioniert (T2). Zusätzlich flashen: nichts Neues nötig
(Pico-Logik steckt in `global_controller_test.py`, schon in der Deploy-Liste oben).

- [ ] **Zuhause = Einwurf:** Tonne im Leerlauf (`AT_HOME`), Deckel öffnen (Füllstand
      abdecken/kein Echo) → **kein** Alarm, keine Meldung.
- [ ] **Scharf an der Straße:** `goto_street` (Web-App **oder** Touchpanel) → Tonne
      wartet an der Abholpos. Web-App zeigt sie **unterwegs/an der Straße** (nicht mehr
      „zuhause" — Telemetry-Fix). Deckel öffnen → **sofort Buzzer-Alarm** + Meldung
      **„Unbefugtes Öffnen"** (Lock-Icon, rot) live im Security-Panel.
- [ ] **Alarm nicht umgehbar:** Deckel offen lassen → Buzzer läuft weiter; erst beim
      **Schließen** hört er auf.
- [ ] **Entschärfen per Truck:** Sim-Truck an die Position von Tonne 22 fahren (≤10 m,
      Admin/Route) → Bridge-Log `arm-state -> pico: DISARM`. Deckel öffnen → **kein**
      Alarm (Leerung). Truck weg → `ARM` → wieder scharf.
- [ ] Bridge-Log: `REPORT:UNAUTHORIZED_OPEN` → `POST /security/events` bei Alarm.
- [ ] „Erledigen" im Leitstand entfernt die Meldung.

---

## Reihenfolge-Empfehlung

**T1 zuerst** (MUX ist die Basis für alles Sensorische). Dann T2 (Füllstand),
T3 (Meldungen, braucht Bridge/Backend), T4 (Eco), T5 (Party — Spaß zum Schluss),
**T6 (Deckel-Security — braucht T2 + Bridge/Backend + optional Sim-Truck).**
