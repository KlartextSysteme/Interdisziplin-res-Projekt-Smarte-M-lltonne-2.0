# Uebergabe Linienfolger mit PD-Regler und Schrittmotoren

Stand: 19.06.2026

Diese Datei dokumentiert die heute erstellten und geaenderten Codezeilen fuer den Pico-Linienfolger der smarten Muelltonne. Der aktuelle Code liegt in:

`linienfolger_pd_stepper.py`

## Ziel

Die Muelltonne soll mit zwei Schrittmotoren einer Linie folgen. Die Liniensensoren werden ueber einen CD74HC4067 Multiplexer eingelesen. Die Motoren werden ueber STEP/DIR/ENABLE-Treiber angesteuert. Die Korrektur der Fahrtrichtung erfolgt ueber einen PD-Regler.

Zusatzfunktionen:

- Wenn die Linie kurz verloren geht, wird die letzte berechnete Motoransteuerung beibehalten.
- Wenn die Linie laenger verloren bleibt, stoppen die Motoren nach 5 Sekunden.
- Wenn alle fuenf Liniensensoren gleichzeitig Linie erkennen, stoppt die Muelltonne, weil sie an der Strasse angekommen ist.
- Der vordere Ultraschallsensor stoppt die Muelltonne bei einem Hindernis vor der Tonne.

## Pinbelegung

### Multiplexer CD74HC4067

```python
MUX_S0_PIN = 2
MUX_S1_PIN = 3
MUX_S2_PIN = 4
MUX_S3_PIN = 5
MUX_SIGNAL_PIN = 28
```

### Liniensensoren

Die Liniensensoren liegen auf den Multiplexer-Kanaelen `C0` bis `C4`.

```python
LINE_CHANNELS = [0, 1, 2, 3, 4]
```

Wichtiges Ergebnis aus den Tests: Die Sensoren sind mechanisch bzw. logisch von rechts nach links angeordnet. Deshalb ist die Gewichtung aktuell:

```python
LINE_WEIGHTS = [2, 1, 0, -1, -2]
```

Die Sensoren liefern bei erkannter Linie aktuell `1`.

```python
LINE_DETECTED_VALUE = 1
```

Falls die Sensoren spaeter invertiert betrieben werden, muss dieser Wert auf `0` geaendert werden.

### Ultraschallsensor vorne

Der vordere Ultraschallsensor wurde heute in den Code integriert.

```python
US_TRIGGER_PIN = 6
US_FRONT_CHANNEL = 5
US_STOP_CM = 30
US_INTERVAL_MS = 120
US_TIMEOUT_US = 30000
```

Der Trigger ist direkt an `GP6` angeschlossen. Das Echo-Signal kommt ueber den Multiplexer-Kanal `C5` und wird deshalb ueber `MUX_SIGNAL_PIN = 28` eingelesen.

Wenn die gemessene Entfernung kleiner oder gleich `30 cm` ist, stoppen die Motoren sofort.

### Motoren

Die Motorpins wurden an die getestete Motoransteuerung angepasst:

```python
LEFT_DIR_PIN = 10
LEFT_STEP_PIN = 11
LEFT_ENABLE_PIN = 12

RIGHT_DIR_PIN = 13
RIGHT_STEP_PIN = 8
RIGHT_ENABLE_PIN = 9
```

Die getestete Vorwaertsfahrt ist:

```python
LEFT_FORWARD_DIR = 0
RIGHT_FORWARD_DIR = 1
```

## Motoransteuerung

Die Schrittmotoren werden nicht mit festen Schrittbloecken gefahren, sondern ueber PWM auf den STEP-Pins. Die Frequenz der PWM bestimmt die Motorgeschwindigkeit.

Die Klasse dafuer ist:

```python
class DualStepperMotorPWM:
```

Die wichtigste Methode ist:

```python
drive_forward_differential(left_speed, right_speed)
```

Diese Methode setzt getrennte Geschwindigkeiten fuer linken und rechten Motor. Dadurch kann der PD-Regler lenken.

Die Umrechnung von Prozent-Geschwindigkeit in Frequenz passiert hier:

```python
def _speed_to_frequency(self, speed, trim_factor):
```

Aktuelle Frequenzgrenzen:

```python
MIN_FREQ = 2000
MAX_FREQ = 4500
```

Formel:

```text
Frequenz = MIN_FREQ + (MAX_FREQ - MIN_FREQ) * speed / 100
```

Bei `speed = 0` wird keine PWM ausgegeben.

## PD-Regler

Der PD-Regler berechnet aus der Linienposition eine Korrektur.

Aktuelle Parameter:

```python
KP = 32
KD = 2
MAX_CORRECTION = 60
MAX_DERIVATIVE_PER_S = 45
```

Aktuelle Fahrparameter:

```python
BASE_SPEED = 45
MIN_SPEED = 0
MAX_SPEED = 95
```

Die Korrektur wird symmetrisch auf die Motoren verteilt:

```python
left_speed = BASE_SPEED - correction
right_speed = BASE_SPEED + correction
```

Das bedeutet:

- Positive Korrektur: linker Motor langsamer, rechter Motor schneller.
- Negative Korrektur: linker Motor schneller, rechter Motor langsamer.

Diese symmetrische Variante wurde zum Schluss wiederhergestellt, weil die asymmetrische Variante mit nur einem verlangsamten Motor nicht ausreichend gut funktionierte.

## Wichtige Erkenntnisse aus den Tests

### 1. Sensorreihenfolge war gespiegelt

In den Ausgaben wurde sichtbar, dass z.B. Sensor `C3` zuerst als falsche Seite interpretiert wurde. Die Gewichtung musste deshalb auf:

```python
LINE_WEIGHTS = [2, 1, 0, -1, -2]
```

geaendert werden.

### 2. Vorwaertsfahrt der Motoren

Die richtige Vorwaertsfahrt ist:

```python
LEFT_FORWARD_DIR = 0
RIGHT_FORWARD_DIR = 1
```

An diesen Werten sollte nicht weiter gedreht werden, solange der normale Geradeauslauf funktioniert.

### 3. Linksdrehung war zu schwach

In den Logs war zu sehen, dass der Regler zwar am Limit war, aber der langsame Motor trotzdem noch mit ca. `2125 Hz` lief. Ursache war `MIN_SPEED = 5`, was wegen `MIN_FREQ = 2000` immer noch eine relativ hohe Frequenz erzeugte.

Deshalb wurde gesetzt:

```python
MIN_SPEED = 0
MAX_CORRECTION = 60
KP = 32
KD = 2
```

Dadurch kann ein Motor bei starker Korrektur wirklich stehen bleiben.

### 4. D-Anteil war zeitweise zu aggressiv

In einem Log sprang die Korrektur kurz in die Gegenrichtung. Vermutlich kam das vom D-Anteil. Deshalb wurde `KD` reduziert:

```python
KD = 2
```

Wenn der Roboter spaeter stark schwingt, zuerst `KD` leicht erhoehen oder `KP` leicht senken. Wenn er zu traege reagiert, zuerst `KP` leicht erhoehen.

### 5. Verhalten bei verlorener Linie

Die erste Suchlogik mit fester `SEARCH_SPEED` wurde entfernt. Stattdessen behaelt der Code jetzt die zuletzt berechnete Geschwindigkeit bei:

```python
last_left_speed = left_speed
last_right_speed = right_speed
```

Wenn keine Linie erkannt wird:

```python
left_speed = last_left_speed
right_speed = last_right_speed
motors.drive_forward_differential(left_speed, right_speed)
```

Nach 5 Sekunden ohne Linie wird gestoppt:

```python
LOST_LINE_STOP_MS = 5000
```

### 6. Strassenerkennung

Wenn alle fuenf Liniensensoren gleichzeitig Linie erkennen, wird `"street"` zurueckgegeben:

```python
if all(value == LINE_DETECTED_VALUE for value in values):
    return "street"
```

Im Hauptprogramm stoppt die Muelltonne dann sofort.

### 7. Ultraschall hat Vorrang

Der vordere Ultraschallsensor wird alle `120 ms` gemessen:

```python
US_INTERVAL_MS = 120
```

Der Stopp bei Hindernis wird vor Linienfolge und Strassenerkennung geprueft:

```python
if obstacle_detected(front_distance_cm):
    motors.stop()
```

Damit hat ein Hindernis vor der Muelltonne Vorrang vor allen Linienentscheidungen.

## Debug-Ausgabe

Die Ausgabe enthaelt aktuell:

```text
Sensoren
Position
Korrektur
Speed L/R
Frequenz L/R
US vorne
```

Beispiel:

```text
Sensoren: [0, 0, 1, 0, 0] Position: 0.0 Korrektur: 0.0 Speed L/R: 45.0 45.0 Frequenz L/R: 3125 3125 US vorne: None
```

Diese Ausgabe ist fuer die weitere Abstimmung wichtig.

## Naechste sinnvolle Tests

1. Geradeausfahrt testen:
   - Erwartung bei mittlerem Sensor: `Position: 0.0`, beide Geschwindigkeiten gleich.

2. Linke und rechte Abweichung einzeln testen:
   - Linie unter rechtem/linkem Sensor halten.
   - Pruefen, ob sich die Geschwindigkeiten sinnvoll gegensaetzlich aendern.

3. Starke Kurve testen:
   - Bei `Position: 2.0` oder `Position: -2.0` sollte ein Motor sehr langsam oder aus sein.

4. Linienverlust testen:
   - Wenn alle Sensoren `0` melden, muss die letzte Geschwindigkeit fuer maximal 5 Sekunden beibehalten werden.
   - Danach muss `Speed L/R: 0 0` erscheinen.

5. Strassenerkennung testen:
   - Wenn alle Sensoren `1` melden, muss sofort gestoppt werden.

6. Ultraschall vorne testen:
   - Hindernis unter `30 cm` vor den Sensor halten.
   - Erwartung: Motoren stoppen sofort.

## Parameter fuer weitere Abstimmung

Wenn die Muelltonne zu langsam reagiert:

```python
KP = 36
```

Wenn sie schwingt:

```python
KP = 28
```

oder:

```python
KD = 3
```

Wenn sie insgesamt zu schnell ist:

```python
BASE_SPEED = 35
```

Wenn die Motoren bei niedriger Geschwindigkeit nicht sauber drehen, aber nicht komplett stoppen sollen:

```python
MIN_SPEED = 5
```

Wenn die maximale Korrektur zu aggressiv ist:

```python
MAX_CORRECTION = 45
```

## Aktueller wichtiger Codezustand

Die wichtigste Kombination am Ende des Tages ist:

```python
LINE_WEIGHTS = [2, 1, 0, -1, -2]
LEFT_FORWARD_DIR = 0
RIGHT_FORWARD_DIR = 1

BASE_SPEED = 45
MIN_SPEED = 0
MAX_SPEED = 95

KP = 32
KD = 2
MAX_CORRECTION = 60

LOST_LINE_STOP_MS = 5000

US_TRIGGER_PIN = 6
US_FRONT_CHANNEL = 5
US_STOP_CM = 30
```

Diese Werte sind der aktuelle Ausgangspunkt fuer die naechsten Fahrtests.
