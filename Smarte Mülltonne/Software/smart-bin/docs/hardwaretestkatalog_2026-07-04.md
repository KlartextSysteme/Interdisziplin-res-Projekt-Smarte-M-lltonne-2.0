# Hardware-Testkatalog (Pico) — Stand 2026-07-04

Offene End-to-End-Tests am **physischen Pico**, die sich seit dem letzten
Hardware-Lauf angesammelt haben. Alle Features sind codeseitig fertig, committet
und `py_compile`-grün — sie brauchen nur noch die Verifikation an der echten Tonne.

## Deploy (einmal vor den Tests)

Modularer Client-Stack auf den Pico (`DEV=/dev/cu.usbmodem14301`):

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

> Hinweis: Es gibt zwei `ui.py` (firmware = läuft auf dem Pico, + `Quellcode/Client/ui.py`
> für Repo-Konsistenz). Auf den Pico kommt die **firmware**-Variante.

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

---

## Reihenfolge-Empfehlung

**T1 zuerst** (MUX ist die Basis für alles Sensorische). Dann T2 (Füllstand),
T3 (Meldungen, braucht Bridge/Backend), T4 (Eco), T5 (Party — Spaß zum Schluss).
