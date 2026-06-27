# Übergabeprotokoll: Fahrlogik & Pico-Firmware (2026-06-27)

Dieses Dokument beschreibt den Stand der **autonomen Fahrlogik** der Smarten Mülltonne nach
der Testsession am 2026-06-27. Es dient als **Übergabe an weitere Entwickler:innen** und enthält:
was funktioniert, wie es funktioniert, wo man schraubt, bekannte Grenzen und der Betriebs-Runbook.

> TL;DR: Der **volle Fahrzyklus läuft in den Tests wie gewollt** — Hinfahrt zur Abholposition,
> Rückfahrt nach Hause inkl. zweier 180°-Drehungen, ausgelöst per Touchpanel **und** Web-App,
> mit funktionierendem Sofort-Stopp während der Fahrt.

> **Ergänzt am 2026-06-27 (Diagnose-Session):** Verifikation, dass die Pico-Firmware byte-identisch
> zum Repo ist (§1, §6.6), eine erfolgreich am Touch-Display ausgelöste Linienfahrt mit Sensor-Belegen
> (§4) sowie Serial-Debug-Workflow (§6.7) und neue Learnings (§7.10–7.12, v.a. „aufgebockt testen geht
> nicht").

---

## 1. Wichtig zuerst: Welcher Code läuft wirklich?

Es gibt im Repo **zwei parallele Code-Stacks**. Das ist die größte Stolperfalle bei der Übergabe.

| Stack | Pfad | Status |
|---|---|---|
| **Inline-Stack (LIVE auf dem Pico)** | `firmware/pico_touchpanel/main.py` | ✅ **Das ist der produktive Stand.** Eine einzige `main.py`, die Touchpanel-UI, Sensoren, Motoren, Bridge-Client und die komplette Fahrlogik inline enthält. |
| Modularer Stack | `../Quellcode/Client/` (`main.py`, `global_controller_test.py`, `network_*`) | ⚠️ **Läuft NICHT auf dem Pico.** State-Machine-Variante mit Hindernis-Umfahrung. Wurde getestet, aber wegen schlechterer Linienverfolgung (siehe §7) wieder verworfen. |

**Alle Änderungen dieser Session wurden im Inline-Stack `firmware/pico_touchpanel/main.py` gemacht.**
Wer an der Fahrlogik arbeitet, editiert diese Datei und flasht sie auf den Pico (§6).

> **Verifiziert am 2026-06-27 (Diagnose-Session):** Nach einem Rollback an der Motorlogik bestand die
> Sorge, die funktionierende Touch-Display-Firmware sei vom Pico verschwunden. Per `mpremote` ausgelesen
> und byteweise gegen `firmware/pico_touchpanel/` geprüft: **`main.py`, `ui.py`, `config.py`,
> `tcp_bridge_client.py` und alle 351 Assets sind byte-identisch zum Repo**; `display.py`, `touch.py`,
> `wireframe.py` unterscheiden sich nur in den Zeilenenden (CRLF auf dem Pico vs. LF im Repo — für
> MicroPython irrelevant). **Der Rollback hat nichts gelöscht.** Der Pico-Stand entspricht dem Repo.
> Wer „ist auf dem Pico wirklich der Repo-Code?" prüfen will, nutzt den Vergleich aus §6.6.

---

## 2. Systemarchitektur (Demo-Setup)

```
Touchpanel (am Pico)  ─┐
                       ├─► Pico (main.py)  ──TCP/WLAN──►  TCP-Bridge (Mac)  ──HTTP──►  Backend (FastAPI)  ◄──►  Web-App
Web-App ──► Backend ───┘        ▲                          (bridge/tcp_bridge.py)         (uvicorn :8000)
                                └── Befehle: CMD_GOTO_STREET / CMD_RETURN_HOME / CMD_STOP
```

- **Zwei Auslöse-Wege**, beide funktionieren:
  - **Touchpanel**: löst direkt `handle_action()` → `start_goto_street()` / `start_return_home()` aus.
  - **Web-App**: erzeugt ein Backend-Command → Bridge pollt `/bins/22/pending-command` → schickt
    `CMD_*` an den Pico → `handle_bridge_command()`.
- **Bridge-Protokoll** (zeilenbasiert, `\n`): Pico sendet `Pico ist bereit`, `STATUS:<state>`,
  `ACK CMD_*`, `ARRIVED: STREET|HOME`. Pico empfängt `CMD_GOTO_STREET`, `CMD_RETURN_HOME`, `CMD_STOP`.
- **Test-Tonne** ist `bin_id = 22` (FH Campus). Die Bridge läuft mit `--bin-id 22`.
- **Netzwerk**: WLAN `SmartBinDemo` / `SmartBin2026!`, Bridge unter `192.168.50.10:50002`.

---

## 3. Was diese Session umgesetzt wurde (und jetzt funktioniert)

Alles in `firmware/pico_touchpanel/main.py`:

### 3.1 Echte Heimfahrt (`run_to_home`)
Vorher war „Heim" nur ein Stub (faked sofort `ARRIVED: HOME`). Jetzt:
1. **180°-Drehung an der Abholposition** (`pivot_180()`),
2. **Linie zurück folgen** bis zum Heim-**T-Stück** (5 Sensoren = Pad),
3. **180°-Drehung an der Heimposition**, dann `ARRIVED: HOME` → `STANDBY`.

### 3.2 Leave-Pad-Guard (Kern-Fix)
Beide Streckenenden sind **T-Stücke**, die alle 5 Liniensensoren auslösen (`position == "street"`).
Ohne Guard würde die Tonne nach der ersten Drehung sofort wieder „Pad erkannt" melden (sie steht ja
noch drauf) und nie zurückfahren. Lösung: `follow_line(leave_pad_first=True)` wertet das End-Pad
**erst dann** als Ziel, wenn die Tonne das Start-Pad **einmal verlassen** hat (Linie gesehen).

### 3.3 180°-Drehung auf der Stelle + Kalibrierung
- Neue Motor-Methoden `DualStepperMotorPWM.turn_in_place()` (eine Kette vor, andere zurück) und
  `steps_to_ms()`. Die Inline-Motorklasse konnte vorher **nicht** auf der Stelle drehen.
- Drehdauer aus Handtest kalibriert: **`TURN_180_STEPS = 43000`** bei **`TURN_SPEED = 35`**
  (≈ 15 s pro Drehung). Gilt für **beide** Drehungen.

### 3.4 1-Sekunden-Pause vor jeder Drehung
Auf Wunsch: vor jeder 180°-Drehung hält die Tonne **`PIVOT_PAUSE_MS = 1000` ms mit gestoppten
Motoren** an → sichtbares Zeichen, dass das 5-Sensor-End-Pad erkannt wurde. Auch während der Pause
sofort abbrechbar.

### 3.5 Sofort-Stopp mitten in der Fahrt (Bridge-seitig)
**Wichtigster Betriebs-Fix.** Der Fahr-Loop ist blockierend; vorher wurden Befehle (auch `Stopp`)
erst nach Fahrtende verarbeitet (~19 s Verzögerung gemessen). Jetzt pollt der Loch jeden
Regelzyklus die Bridge:
- `_drive_pump()` ruft `bridge_client.tick()` (liest Befehle, sendet Status) und meldet das
  Abbruch-Flag `_abort_drive`.
- `follow_line()` und `pivot_180()` prüfen das Flag und brechen mit `"aborted"` ab.
- `handle_bridge_command()` setzt bei `CMD_STOP` während `_driving` sofort `_abort_drive = True`.
- **Gemessen: Stopp greift in ~23 ms** (vorher ~19 s). Bonus: Status wird jetzt auch **während**
  der Fahrt live gesendet (Backend friert nicht mehr auf `en_route` ein).

### 3.6 Linienverfolgungs-Werte zurück auf verifizierten Stand
`MAX_CORRECTION = 80`, `MIN_SPEED = 0`, `MAX_SPEED = 95`, `BASE_SPEED = 45`, `KP = 32`, `KD = 2`.
Hinweis: Ein zwischenzeitlicher Wert `max_correction = 60` (aus dem modularen Stack) führte zu
Linienverlust in scharfen Kurven — siehe §7.

### 3.7 Touchpanel-Status-Screens
Die alten weißen Text-Test-Screens (`TEST / HEIMFAHRT NICHT AKTIV` etc.) wurden entfernt; Anzeige
läuft über `ui.set_status()` (Wireframe-Assets: Haus/Müllwagen-Positionsicon, „Linie erkannt",
„Linie verloren", „Hindernis"). Müllwagen-Varianten der Fahr-Screens wurden erzeugt, indem das
bestehende, genehmigte Müllwagen-Icon aus `status_full_truck_clean` auf die Fahr-Screens kopiert
wurde (Icon-Box `x243–262, y6–20`). Touchpanel-Feinschliff ist als **nächster Schritt** geplant.

---

## 4. In Tests bestätigtes Verhalten (mit Belegen)

| Verhalten | Beleg (Bridge-Log) |
|---|---|
| **Voller Zyklus** Abholung → Abholpos → Heim → zuhause | `LINE_FOLLOWING → WAIT_AT_STREET`, später `LINE_FOLLOWING → ARRIVED: HOME → STANDBY` (Rückfahrt ~106 s inkl. beider Drehungen) |
| Auslösung per **Touchpanel** | `STATUS:MANUAL_GOTO_STREET_REQUEST` / `MANUAL_RETURN_HOME_REQUEST` |
| Auslösung per **Web-App** | `backend command #N goto_street -> pico CMD_GOTO_STREET` + `ACK` |
| **Sofort-Stopp** während Fahrt | `CMD_STOP` → `ACK` → `USER_PAUSED` innerhalb ~23 ms |
| Inline-Linienverfolgung hält die Strecke | Hinweg ~71 s bis `ARRIVED: STREET`, kein `LINE_LOST` |
| 1-Sek-Pause vor Drehung | physisch am Gerät sichtbar (kein eigener Status im Log) |
| **Touchpanel-ausgelöste Fahrt am Display** (voller Klickpfad Menü → PIN → Fahrtenmenü → „zur Abholpos") | `Touch action: goto_street` → `Starte Linienfolger` → durchgehende Regelung über 45 s, kein `T-Pad erkannt`/`LINE_LOST` (Diagnose-Session 2026-06-27, serielles Log) |
| **Liniensensorik liefert echte Muster** unter Last | gemessene Sensorzeilen `[0,0,1,0,0]`, `[0,1,0,0,0]`, `[1,1,0,0,0]` mit passenden PD-Korrekturen und differenziellen Rad-Speeds (45/45 geradeaus … 0/93 in Kurven) |

---

## 5. Parameter-Referenz (alle in `firmware/pico_touchpanel/main.py`)

| Konstante | Wert | Bedeutung / Tuning |
|---|---|---|
| `BASE_SPEED` | 45 | Grundgeschwindigkeit Linienfolge |
| `MIN_SPEED` / `MAX_SPEED` | 0 / 95 | Clamp der Rad-Speeds; `MIN_SPEED=0` erlaubt Innen-Kette = Stillstand (scharfe Kurve, Kettenfahrwerk) |
| `KP` / `KD` | 32 / 2 | PD-Regler |
| `MAX_CORRECTION` | 80 | **Lenkautorität** — zu klein (z.B. 60) → Linienverlust in Kurven |
| `MAX_DERIVATIVE_PER_S` | 45 | D-Anteil-Begrenzung |
| `CONTROL_INTERVAL_MS` | 25 | Regelzyklus (auch Bridge-Poll-Takt während Fahrt) |
| `LOST_LINE_STOP_MS` | 10000 | Nachlauf bei verlorener Linie, dann Abbruch |
| `TURN_SPEED` | 35 | Drehgeschwindigkeit 180° |
| `TURN_180_STEPS` | 43000 | **Kalibrierte 180°-Drehung** (Handtest). Bei falschem Winkel hier justieren |
| `PIVOT_PAUSE_MS` | 1000 | Pause (Motoren aus) vor jeder Drehung |
| `US_STOP_CM` | 15 | Hindernis-Stoppdistanz Frontsensor |
| `US_FRONT_CHANNEL` | 5 | Mux-Kanal Frontsensor |
| `LINE_CHANNELS` / `LINE_WEIGHTS` | `[0..4]` / `[2,1,0,-1,-2]` | Sensor-Reihenfolge & Gewichte (C0=rechts) |
| `MIN_FREQ` / `MAX_FREQ` | 2000 / 4500 | Stepper-PWM-Frequenzbereich |
| `LEFT_FORWARD_DIR` / `RIGHT_FORWARD_DIR` | 1 / 0 | Vorwärts-Richtung pro Kette |

Pins (Mux S0–S3 = 2,3,4,5; Signal = 28; Links Dir/Step/Enable = 10/11/12; Rechts = 13/8/9) stehen
ebenfalls oben in `main.py`.

---

## 6. Betriebs-Runbook

### 6.1 Bridge starten (Mac, eigenes Terminal empfohlen!)
```bash
cd ".../Smarte Mülltonne/Software/smart-bin"
backend/.venv/bin/python bridge/tcp_bridge.py \
  --host 0.0.0.0 --port 50002 --bin-id 22 --backend http://127.0.0.1:8000
```
Erfolg: Log zeigt `TCP bridge listening ... bin_id=22`, dann `Pico connected`, `pico: Pico ist bereit`,
`STATUS:STANDBY`. Backend (`uvicorn main:app --port 8000`) muss laufen.

### 6.2 Pico flashen
```bash
mpremote connect port:/dev/cu.usbmodem<XXXX> fs cp main.py :main.py
mpremote connect port:/dev/cu.usbmodem<XXXX> reset
```
Gerätename per `mpremote connect list` ermitteln (taucht als `MicroPython Board ... 2e8a:0005` auf).

### 6.3 Backend-Tonne zurücksetzen (ohne USB)
```bash
curl -X POST http://localhost:8000/bins/22/update -H "Content-Type: application/json" \
  -d '{"status":"idle","location_state":"home","movement_state":"home"}'
```

### 6.4 Stau-Commands leeren (wichtig, siehe §7!)
Alle unbestätigten Commands acken:
```bash
# pending listen
curl -s http://localhost:8000/bins/22/command-history?limit=60
# jedes per ID bestätigen
curl -X POST http://localhost:8000/bins/22/ack -H "Content-Type: application/json" -d '{"command_id":<ID>}'
```

### 6.5 Reset-Workflow im Demo-Alltag
- **Tonne hängt / soll stoppen** → in der Web-App **`Stopp`** (greift jetzt mitten in der Fahrt,
  ~25 ms, **kein USB nötig**).
- **Touchpanel/`main.py` reagiert gar nicht mehr** (z.B. nach Testskript am anderen Rechner) →
  Pico per USB `reset` (§6.2) — dann läuft `main.py` wieder.

### 6.6 Pico-Stand gegen Repo prüfen (Verifikation)
Belegt, dass der live laufende Code dem Repo entspricht (vgl. §1):
```bash
# Datei vom Pico ziehen und gegen Repo diffen (Zeilenenden ignorieren -> CRLF vs. LF egal)
mpremote connect /dev/cu.usbmodem<XXXX> fs cp :main.py /tmp/pico_main.py
diff <(tr -d '\r' < /tmp/pico_main.py) \
     <(tr -d '\r' < "firmware/pico_touchpanel/main.py") && echo "IDENTISCH"
```

### 6.7 Live-Debug der Fahrt über die serielle Konsole
Die Inline-`main.py` printet während der Fahrt periodisch (`PRINT_INTERVAL_MS=250`) die Sensorzeile,
`Position`, `Korrektur`, `Speed L/R`, `armed` und `US vorne`. Mitschneiden ohne Thonny:
```python
# /tmp/picolog.py  (braucht pyserial)
import sys, time, serial
s = serial.Serial("/dev/cu.usbmodem<XXXX>", 115200, timeout=0.1)
if "--reset" in sys.argv:                 # main.py sauber neu starten
    s.write(b"\r\x03\x03"); time.sleep(0.3); s.reset_input_buffer(); s.write(b"\x04")
end = time.time() + float(sys.argv[1] if len(sys.argv) > 1 else 10)
while time.time() < end:
    d = s.read(512)
    if d: sys.stdout.write(d.decode("utf-8", "replace")); sys.stdout.flush()
```
`python3 /tmp/picolog.py 45` → 45 s mitschneiden, dann am Touchpanel auslösen.

> **Port-Stolperfalle:** Die **MicroPico-Extension in VS Code** hält den seriellen Port belegt
> (`mpremote: failed to access ... it may be in use`). Vor jedem `mpremote`/Serial-Zugriff in VS Code
> unten in der Statusleiste **MicroPico → Disconnect**. Prüfen: `lsof /dev/tty.usbmodem<XXXX>`.

---

## 7. Bekannte Grenzen, Stolperfallen & Learnings

1. **Zwei Code-Stacks (§1).** Nicht verwechseln. Live = Inline-`main.py`.

2. **Modularer Stack hat schlechtere Linienverfolgung.** Gleiche PD-Werte, aber die modulare
   Hauptschleife macht pro Durchlauf Netzwerk + Touchpanel + `sleep_ms(20)` → Regelung reagiert
   seltener/ruckeliger → Kurven brechen weg (Tonne verlor die Linie nach ~12 s). Der Inline-`run_to_street`
   ist eine **enge, dedizierte Schleife** (alle 25 ms, sonst nichts) und fuhr dieselbe Strecke sauber
   durch. **Deshalb läuft die Fahrlogik im Inline-Stack.** Wer den modularen Stack reaktivieren will,
   muss zuerst dessen Regel-Loop straffen.

3. **`STATUS:LINE_FOLLOWING` heißt NICHT „fährt sauber auf der Linie".** Solange auch nur ein Sensor
   etwas erwischt, ist die Position ≠ `None` und der Zustand bleibt `LINE_FOLLOWING` — auch während
   die Tonne schon wegdriftet. Erst wenn alle Sensoren weg sind, kommt `LINE_LOST`. Beim Auswerten
   von Logs nicht täuschen lassen.

4. **Stau-Commands → Geister-Fahrten.** Web-App-Befehle stauen sich, während die Bridge mal weg ist,
   und werden beim **Reconnect alle auf einmal** ausgeliefert → die Tonne fährt ungewollt los. Vor
   jedem Pico-Reset die Queue leeren (§6.4). **Empfohlener nächster Fix:** Bridge so anpassen, dass
   sie beim Pico-Reconnect die Queue verwirft oder Commands älter als X Sekunden ignoriert.

5. **Blockierender Fahr-Loop.** Während einer Fahrt ist die Hauptschleife blockiert; nur die Bridge
   wird via `_drive_pump()` gepollt. Heißt: **Stopp funktioniert mitten in der Fahrt nur über die
   Web-App/Bridge**, nicht über das Touchpanel (dessen `tick()` läuft während der Fahrt nicht). Ein
   Touchpanel-Not-Stopp wäre ein sinnvolles nächstes Feature.

6. **Frontsensor am Streckenende.** In einem Lauf ging die Rückfahrt kurz vor dem Heim-T auf
   `OBSTACLE` — Verdacht: der Frontsensor erkennt die Wand/Struktur am T-Ende als Hindernis, bevor
   das 5-Sensor-Pad greift. Ggf. Hindernis-Stopp nahe des Ziel-Pads unterdrücken oder `US_STOP_CM`
   anpassen.

7. **Keine Hindernis-Umfahrung im Inline-Stack.** Bei Hindernis wird nur **gestoppt** (`"obstacle"`).
   Die volle Umfahrung (`avoid_left/avoid_right`) existiert nur im modularen Stack und ist noch nicht
   kalibriert.

8. **USB trennt sich häufig** (Mac sieht das Board zeitweise nicht). Für den Testbetrieb über
   Touchpanel/Web-App **egal** — USB wird nur zum Flashen/Reseten gebraucht.

9. **Mechanik/Strecke ist fragil.** Teststrecke und Kettenfahrwerk wurden mehrfach in Mitleidenschaft
   gezogen (u.a. durch die Drehung). Linienverluste können mechanische Ursachen haben — vor dem
   Schlussfolgern auf Software-Fehler die Strecke prüfen.

10. **„Aufgebockt" ist kein gültiger Fahrtest — Tonne startet sofort als „angekommen".** In der
    Diagnose-Session löste ein Test mit **aufgebockter Tonne** (Sensoren in der Luft) sofort
    `Stopp: T-Pad erkannt` aus, die Fahrt endete in <1 s → wirkte wie „Befehl ohne Wirkung".
    Ursache: Hängen alle 5 Liniensensoren in der Luft, lesen sie **alle `1`** (live verifiziert:
    `[1,1,1,1,1]`). `calculate_line_position()` wertet „alle == `LINE_DETECTED_VALUE`" als `"street"`
    = T-Pad/Ziel; bei `leave_pad_first=False` ist `armed=True` sofort → Instant-Stop. **Die Logik kann
    „aufgebockt" nicht von „auf dem breiten T-Pad stehend" unterscheiden** (beides `[1,1,1,1,1]`).
    → **Immer mit Tonne am Boden über echter Linie testen, und nicht direkt auf dem T-Pad starten.**
    Auf echter Linie lief derselbe Befehl danach einwandfrei (§4).

11. **Vor „der Rollback hat XY gelöscht": erst Pico-Stand gegen Repo diffen (§6.6).** Die o.g. Sorge
    um die verlorene Touch-Firmware war unbegründet — der Pico-Code war byte-identisch zum Repo
    (§1). CRLF-vs-LF-Unterschiede beim Diff nicht als „verändert" fehldeuten (`tr -d '\r'` nutzen).

12. **`ECONNRESET` der Bridge ≠ Fahrt-Problem.** Wenn die TCP-Bridge nicht läuft, spammt der Pico
    `TCP bridge connect failed: [Errno 104] ECONNRESET`. Das betrifft **nur** den Web-App-/Fernbefehl-
    Kanal — **Touchpanel-Fahrten laufen lokal und unabhängig davon**. Beim Log-Lesen herausfiltern.

---

## 8. Offene nächste Schritte (Vorschlag)

1. Touchpanel-Screens final überarbeiten (war bewusst zurückgestellt).
2. Bridge: Queue beim Pico-Reconnect verwerfen (gegen Geister-Fahrten, §7.4).
3. Frontsensor-Hindernis am Streckenende entschärfen (§7.6).
4. Optional: Hindernis-Umfahrung in den Inline-Stack portieren + kalibrieren.
5. Optional: Touchpanel-Not-Stopp während der Fahrt (§7.5).
6. Optional: Trockentest aufgebockt ermöglichen — z.B. T-Pad erst nach einmal gesehener Linie „armen"
   (wie `leave_pad_first=True` es für die Rückfahrt schon macht). Trade-off: dann startet die Hinfahrt
   nicht mehr direkt vom T-Pad. Nur umsetzen, wenn aufgebockte Tests wirklich gebraucht werden (§7.10).

---

## 9. Zentrale Dateien

| Datei | Inhalt |
|---|---|
| `firmware/pico_touchpanel/main.py` | **Live-Fahrlogik** (Inline-Stack): `follow_line`, `run_to_home`, `pivot_180`, `_drive_pump`, Motorklasse, Bridge-Handler, Touchpanel |
| `firmware/pico_touchpanel/ui.py` + `assets/` | Touchpanel-UI & Wireframe-Status-Assets |
| `firmware/pico_touchpanel/tcp_bridge_client.py` | Bridge-Client auf dem Pico (Protokoll) |
| `bridge/tcp_bridge.py` | TCP-Bridge auf dem Mac (Backend ↔ Pico) |
| `backend/` (FastAPI) | Command-Queue, Telemetrie, Bin-Status (`bin_id=22`) |
| `docs/fahrstreckenlogik_review_2026-06-27.md` | Vorheriger Logik-Review (Abgleich modular vs. Soll) |
| `../Quellcode/Client/` | Modularer Stack (NICHT live) |
