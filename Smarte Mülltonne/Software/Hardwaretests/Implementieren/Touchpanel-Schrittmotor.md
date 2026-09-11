# Uebergabe: Touchpanel mit PD-Schrittmotor-Regelung

Datum: 19.06.2026

## Ziel

Die bestehende Touchpanel-Firmware der smarten Muelltonne wurde mit der vorhandenen PD-Schrittmotor-Regelung fuer den Linienfolger verbunden. Die Fahrt zur Strasse soll ueber das Touchpanel gestartet werden.

Startpfad in der UI:

```text
PIN -> Fahren -> Abholung
```

Beim Druecken von `Abholung` startet die Muelltonne die Fahrt zur Strasse mit der PD-Regelung.

## Verwendete Ausgangsdateien

Aktuelle Touchpanel-Firmware:

```text
C:\Users\tpelz\OneDrive - fhsuedwf\2_Semester\Interdisziplinäres Projekt\Interdisziplin-res-Projekt-Smarte-M-lltonne-2.0\Smarte Mülltonne\Software\Flottenmanagement\firmware\pico_touchpanel
```

Wichtige vorhandene Dateien im Touchpanel-Projekt:

```text
main.py
config.py
display.py
touch.py
ui.py
wireframe.py
assets\
```

Vorhandener PD-Motorcode als fachliche Grundlage:

```text
C:\Users\tpelz\OneDrive - fhsuedwf\2_Semester\Interdisziplinäres Projekt\Interdisziplin-res-Projekt-Smarte-M-lltonne-2.0\Smarte Mülltonne\Software\Hardwaretests\pd_motor_linien.py
```

## Heute erzeugte und geaenderte Dateien

### 1. Neue integrierte `main.py`

Die aktuelle Touchpanel-`main.py` wurde durch eine integrierte Testversion ersetzt.

Zielpfad:

```text
C:\Users\tpelz\OneDrive - fhsuedwf\2_Semester\Interdisziplinäres Projekt\Interdisziplin-res-Projekt-Smarte-M-lltonne-2.0\Smarte Mülltonne\Software\Flottenmanagement\firmware\pico_touchpanel\main.py
```

Inhaltlich neu in dieser Datei:

- Import von `PWM` und Zeitfunktionen fuer die Motorsteuerung.
- Vollstaendige PD-Regler-Logik direkt in `main.py`.
- Multiplexer-Auswahl fuer CD74HC4067.
- Liniensensor-Auswertung ueber C0-C4.
- Ultraschallmessung vorne ueber Trigger GP6 und Echo auf Multiplexer-Kanal C5.
- Schrittmotorsteuerung ueber STEP/DIR/ENABLE.
- Start der Fahrt bei Touchpanel-Aktion `goto_street`.
- Anzeige von Zwischen- und Ergebnisbildschirmen:
  - `FAEHRT / PD REGLER AKTIV`
  - `ZIEL / STRASSE ERREICHT`
  - `STOPP / HINDERNIS`
  - `STOPP / LINIE VERLOREN`

### 2. Backup der alten `main.py`

Vor dem Ersetzen wurde die bisherige Datei gesichert:

```text
C:\Users\tpelz\OneDrive - fhsuedwf\2_Semester\Interdisziplinäres Projekt\Interdisziplin-res-Projekt-Smarte-M-lltonne-2.0\Smarte Mülltonne\Software\Flottenmanagement\firmware\pico_touchpanel\main_backup_before_pd_integration.py
```

Diese Datei enthaelt die vorherige reine Touchpanel-Startlogik ohne Motorintegration.

### 3. Zwischenversionen im Arbeitsordner

Im lokalen Arbeitsordner wurden zusaetzlich Test-/Zwischendateien erstellt:

```text
C:\Users\tpelz\OneDrive\Dokumente\Interdisziplinäres Projekt\main_integrated_touch_pd.py
C:\Users\tpelz\OneDrive\Dokumente\Interdisziplinäres Projekt\pd_motor_linien_touch.py
```

Wichtig: Fuer den Pico-Test ist aktuell nur die integrierte `main.py` entscheidend. Die separate Datei `pd_motor_linien_touch.py` wird von der aktuellen Pico-`main.py` nicht mehr importiert.

## Warum die Integration direkt in `main.py` gemacht wurde

Zuerst wurde eine modulare Loesung mit separatem Motor-Modul erstellt:

```python
from pd_motor_linien_touch import create_motors, run_to_street
```

Dabei trat beim Ausfuehren auf dem Pico das Problem auf, dass `pd_motor_linien_touch.py` nicht bekannt war. Ursache: Beim Ausfuehren ueber MicroPico oder "Run current file" wird haeufig nur die aktuell geoeffnete Datei uebertragen, nicht automatisch alle lokalen Zusatzmodule.

Gemeinsame Erkenntnis:

Fuer einen schnellen Hardwaretest ist eine Ein-Datei-Integration robuster, weil dann die Motorlogik direkt in `main.py` liegt und kein zusaetzliches Python-Modul auf dem Pico vorhanden sein muss.

## Aktueller Stand auf dem Pico

Die neue integrierte `main.py` wurde mit `mpremote` auf den Pico kopiert.

Pruefung auf dem Pico ergab:

```text
main.py 14847 Bytes
```

Danach wurde ein Reset ausgefuehrt:

```powershell
python -m mpremote reset
```

Damit startet der Pico beim Booten direkt mit der neuen Touchpanel-PD-Testversion.

## Testablauf

1. Pico einschalten oder resetten.
2. Touchpanel startet.
3. In der UI den Wartungs-/PIN-Bereich oeffnen.
4. PIN eingeben.
5. Menuepunkt `Fahren` auswaehlen.
6. `Abholung` druecken.
7. Display zeigt `FAEHRT / PD REGLER AKTIV`.
8. Die PD-Regelung uebernimmt die Schrittmotorsteuerung.

Die Fahrt wird beendet bei:

- Zielmarkierung `street`: Alle fuenf Liniensensoren erkennen den Linienwert.
- Hindernis vorne: Ultraschallabstand kleiner/gleich `US_STOP_CM`.
- Linie verloren: Keine Linie fuer laenger als `LOST_LINE_STOP_MS`.

## Aktuelle Hardware-Pinbelegung aus dem integrierten Code

### Multiplexer CD74HC4067

```text
S0  -> GP2
S1  -> GP3
S2  -> GP4
S3  -> GP5
SIG -> GP28
```

### Ultraschall vorne

```text
Trigger -> GP6
Echo    -> Multiplexer C5
```

### Liniensensoren

```text
C0-C4 am Multiplexer
Reihenfolge im Code: [0, 1, 2, 3, 4]
Gewichte: [2, 1, 0, -1, -2]
```

### Schrittmotor links

```text
DIR    -> GP10
STEP   -> GP11
ENABLE -> GP12
```

### Schrittmotor rechts

```text
DIR    -> GP13
STEP   -> GP8
ENABLE -> GP9
```

## Aktuelle Regelparameter

```text
BASE_SPEED = 45
MIN_FREQ = 2000
MAX_FREQ = 4500
KP = 32
KD = 2
MAX_CORRECTION = 60
MAX_DERIVATIVE_PER_S = 45
CONTROL_INTERVAL_MS = 25
LOST_LINE_STOP_MS = 10000
US_STOP_CM = 15
```

## Wichtige Erkenntnisse

### 1. Der aktuelle Touchpanel-Code ist modular

Die aktuelle Firmware besteht nicht aus einer einzelnen Touchpanel-Datei, sondern aus mehreren Modulen:

```text
main.py
config.py
display.py
touch.py
ui.py
wireframe.py
assets\
```

Die UI-Aktion fuer die Fahrt zur Strasse existiert bereits:

```python
goto_street
```

Sie wird in der UI ueber das Untermenue `fahren` durch `Abholung` ausgeloest.

### 2. `goto_street` ist der richtige Anknuepfpunkt

In `ui.py` ist fuer das Fahrmenue definiert:

```python
if key == "fahren":
    return (("HEIM", "goto_home"), ("ABHOLUNG", "goto_street"))
```

Deshalb wurde die Motorfahrt nicht auf einen beliebigen Screen gelegt, sondern gezielt an `goto_street` angebunden.

### 3. Separate Module muessen auf dem Pico vorhanden sein

Wenn eine Datei auf dem Pico Folgendes importiert:

```python
from pd_motor_linien_touch import run_to_street
```

muss `pd_motor_linien_touch.py` ebenfalls auf dem Pico liegen. Sonst bricht der Start mit einem Importfehler ab.

Fuer den aktuellen Test wurde deshalb alles direkt in `main.py` integriert.

### 4. `mpremote` konnte den Pico spaeter erreichen

Ein frueherer Versuch meldete:

```text
mpremote: no device found
```

Spaeter war der Pico erreichbar, und die neue `main.py` konnte erfolgreich hochgeladen werden.

### 5. Syntax wurde geprueft

Die integrierte Datei wurde vor dem Hochladen mit Python kompiliert:

```powershell
python -m py_compile main_integrated_touch_pd.py
```

Die Ziel-`main.py` wurde ebenfalls syntaktisch geprueft. Wegen Schreibrechten im OneDrive-Zielordner wurde dafuer ein separater Cachepfad verwendet.

## Hinweise fuer den naechsten Test

- Falls die Muelltonne rueckwaerts faehrt, muessen diese Werte getauscht werden:

```python
LEFT_FORWARD_DIR = 1
RIGHT_FORWARD_DIR = 0
```

- Falls die Liniensensoren auf schwarzer Linie `0` statt `1` liefern, muss dieser Wert angepasst werden:

```python
LINE_DETECTED_VALUE = 1
```

- Falls die Zielmarkierung zu frueh oder gar nicht erkannt wird, liegt es wahrscheinlich an dieser Logik:

```python
if all(value == LINE_DETECTED_VALUE for value in values):
    return "street"
```

- Falls die Muelltonne zu stark pendelt:

```python
KP reduzieren
KD leicht erhoehen oder reduzieren
BASE_SPEED verringern
```

- Falls sie zu langsam oder unzuverlaessig startet:

```python
BASE_SPEED erhoehen
MIN_FREQ/MAX_FREQ pruefen
ENABLE_ACTIVE_VALUE pruefen
```

## Rueckweg zum alten Zustand

Wenn die alte reine Touchpanel-Version wiederhergestellt werden soll:

```powershell
python -m mpremote cp "C:\Users\tpelz\OneDrive - fhsuedwf\2_Semester\Interdisziplinäres Projekt\Interdisziplin-res-Projekt-Smarte-M-lltonne-2.0\Smarte Mülltonne\Software\Flottenmanagement\firmware\pico_touchpanel\main_backup_before_pd_integration.py" :main.py
python -m mpremote reset
```

## Aktueller Uebergabestatus

- Touchpanel-Firmware nutzt weiterhin die vorhandenen Module fuer Display, Touch, UI und Assets.
- Die Fahrt zur Strasse ist in der aktuellen `main.py` direkt integriert.
- Start der Fahrt erfolgt ueber `PIN -> Fahren -> Abholung`.
- Datei wurde auf den Pico kopiert und per Reset gestartet.
- Der naechste Schritt ist der reale Hardwaretest mit angeschlossenen Motoren, Liniensensoren, Multiplexer und Ultraschallsensor.
