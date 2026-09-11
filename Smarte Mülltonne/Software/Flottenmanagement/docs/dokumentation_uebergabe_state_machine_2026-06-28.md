# Dokumentation und Übergabe: State Machine / Fahrlogik

Stand: 28.06.2026

## Ziel

Diese Datei dokumentiert die heutigen Erkenntnisse und Änderungen an der Pico-Fahrlogik der smarten Mülltonne. Sie dient gleichzeitig als Übergabeprotokoll für andere Entwickler oder weitere Codex-Agenten.

Betroffene Hauptdateien:

- `global_controller_test.py`
- `liniensensor.py`
- `PDcontroller.py`
- `main.py`

## Aktueller Grundaufbau

Die zentrale Fahrlogik liegt in `global_controller_test.py`.

Die State Machine arbeitet mit Hauptzuständen wie:

- `AT_HOME`
- `LINE_FOLLOWING`
- `LINE_LOST`
- `OBSTACLE_WAIT`
- `AVOID_RIGHT`
- `AVOID_LEFT`
- `AVOID_NOT_POSSIBLE`
- `WAIT_AT_STREET`
- `TURN_AT_STREET`
- `TURN_AT_HOME`
- `USER_PAUSED`

Die Fahrtrichtung wird nicht über getrennte Fahrzustände abgebildet, sondern über:

```python
self.drive_target = "street"
self.drive_target = "home"
```

Damit bleibt `LINE_FOLLOWING` für Hin- und Rückfahrt gleich. Die Endmarkierung entscheidet abhängig vom Ziel, ob die Mülltonne an der Straße wartet oder zuhause die Abschlussdrehung ausführt.

## Endmarkierung

Vorher gab der Liniensensor bei allen fünf erkannten Liniensensoren den Sonderwert `"street"` zurück.

Das war unlogisch, weil dieselbe Markierung sowohl an der Straße als auch zuhause vorkommt.

Heute wurde dies vereinheitlicht:

```python
END_MARKER = "end_marker"
```

Der Liniensensor gibt nun bei fünf aktiven Sensoren zurück:

```python
"end_marker"
```

Die Methode:

```python
is_end_marker_detected()
```

wurde ergänzt.

Die alte Methode:

```python
is_street_detected()
```

bleibt als Kompatibilitätsmethode erhalten, verweist aber intern auf `is_end_marker_detected()`.

Wichtig:

- `"end_marker"` ist ein Sensorereignis.
- `"street"` bleibt weiterhin ein Fahrziel in `drive_target`.

## PD-Regler

Der PD-Regler ignoriert jetzt den Sonderwert `"end_marker"`, genauso wie `None`.

Das ist wichtig, weil auf einer Endmarkierung nicht geregelt werden soll.

Aktuelle Logik:

```python
if current_position is None or current_position == "end_marker":
    self.reset()
    return 0
```

## LINE_FOLLOWING

In `LINE_FOLLOWING` passiert:

- US vorne wird geprüft.
- Bei Hindernis: Wechsel nach `OBSTACLE_WAIT`.
- Liniensensoren werden gelesen.
- Bei `"end_marker"`:
  - Ziel `"home"` -> `TURN_AT_HOME`
  - Ziel `"street"` -> `WAIT_AT_STREET`
- Bei `None`: Wechsel nach `LINE_LOST`.
- Bei normaler Position: PD-Regler berechnet Motorgeschwindigkeiten.

## LINE_LOST

Die Logik wurde heute an das Zustandsdiagramm angepasst.

Aktuelles Verhalten:

- Wenn die Linie verloren geht, fährt die Mülltonne bis zu 10 Sekunden mit der letzten bekannten Geschwindigkeit weiter.
- Wenn die Linie wiedergefunden wird, geht es zurück zu `LINE_FOLLOWING`.
- Wenn eine Endmarkierung erkannt wird, wird abhängig von `drive_target` korrekt weitergeschaltet.
- Nach 10 Sekunden ohne Linie:
  - Motoren stoppen.
  - Buzzer wird aktiviert.
  - Touchpanel bleibt auf `line_lost`.
  - Zustand bleibt `LINE_LOST`.

Die Mülltonne springt also nicht mehr automatisch zurück nach `AT_HOME`.

## OBSTACLE_WAIT

Die Hindernislogik wurde an das Zustandsdiagramm angepasst.

Aktuelles Verhalten:

- Motoren stoppen sofort.
- Touchpanel zeigt Hindernis.
- Während der Wartezeit wird US vorne aktiv weiter gemessen.
- Wenn das Hindernis vorne innerhalb der Wartezeit entfernt wird:
  - Wechsel zurück nach `LINE_FOLLOWING`.
- Wenn das Hindernis nach 10 Sekunden noch vorhanden ist:
  - rechts messen
  - links messen
  - rechts frei -> `AVOID_RIGHT`
  - rechts blockiert und links frei -> `AVOID_LEFT`
  - beide blockiert -> `AVOID_NOT_POSSIBLE`

Rechts wird bewusst priorisiert.

## AVOID_NOT_POSSIBLE

Wenn keine Umfahrung möglich ist:

- Motoren stoppen.
- Buzzer läuft.
- Touchpanel zeigt Hilfe.
- US vorne wird weiter geprüft.
- Wenn vorne frei ist, muss dies 5 Sekunden stabil bleiben.
- Danach wird der Buzzer gestoppt und zurück zu `LINE_FOLLOWING` gewechselt.

## TURN_AT_STREET

Dieser Zustand wurde ergänzt.

Wenn die Mülltonne an der Straße steht und der Befehl `goto_home` ausgelöst wird:

```text
WAIT_AT_STREET -> MANUAL_RETURN_HOME_REQUEST -> TURN_AT_STREET -> LINE_FOLLOWING
```

`TURN_AT_STREET` macht eine 180-Grad-Drehung, bevor die Rückfahrt startet.

## TURN_AT_HOME

Wenn die Mülltonne auf der Rückfahrt zuhause die Endmarkierung erkennt:

```text
LINE_FOLLOWING -> TURN_AT_HOME
```

`TURN_AT_HOME` macht:

1. 180-Grad-Drehung.
2. Danach kurze Rückwärtsfahrt, bis die Endmarkierung wieder erkannt wird.
3. Danach Wechsel nach `AT_HOME`.

Es gibt einen Timeout für die Rückwärtsfahrt, damit die Mülltonne nicht endlos fährt, falls die Markierung nicht erkannt wird.

## Hindernisumfahrung Als Super-State

Die Zustände `AVOID_RIGHT` und `AVOID_LEFT` sind Hauptzustände.

Innerhalb dieser Zustände gibt es Unterzustände über:

```python
self.avoid_step
```

Vorher waren diese Unterzustände nur Zahlen `0` bis `10`.

Heute wurden sprechende Konstanten eingeführt.

Das Verhalten wurde nicht geändert, nur die Lesbarkeit und der Abgleich mit dem Zustandsdiagramm wurden verbessert.

## Unterzustände Für AVOID_RIGHT

```python
AVOID_RIGHT_TURN_OUT = 0
AVOID_RIGHT_FIND_OBSTACLE = 1
AVOID_RIGHT_PASS_OBSTACLE = 2
AVOID_RIGHT_EXTRA_AFTER_PASS = 3
AVOID_RIGHT_TURN_PARALLEL = 4
AVOID_RIGHT_FIND_OBSTACLE_AGAIN = 5
AVOID_RIGHT_PASS_OBSTACLE_AGAIN = 6
AVOID_RIGHT_EXTRA_AFTER_SECOND_PASS = 7
AVOID_RIGHT_TURN_TO_LINE = 8
AVOID_RIGHT_SEARCH_LINE = 9
AVOID_RIGHT_ALIGN_ON_LINE = 10
```

Inhaltliche Logik:

- rechts rausdrehen
- Hindernis links suchen
- am Hindernis links vorbeifahren
- Zusatzschritte
- parallel drehen
- Hindernis links erneut suchen
- erneut vorbeifahren
- Zusatzschritte
- zur Linie drehen
- Linie suchen
- auf Linie ausrichten

## Unterzustände Für AVOID_LEFT

```python
AVOID_LEFT_TURN_OUT = 0
AVOID_LEFT_FIND_OBSTACLE = 1
AVOID_LEFT_PASS_OBSTACLE = 2
AVOID_LEFT_EXTRA_AFTER_PASS = 3
AVOID_LEFT_TURN_PARALLEL = 4
AVOID_LEFT_FIND_OBSTACLE_AGAIN = 5
AVOID_LEFT_PASS_OBSTACLE_AGAIN = 6
AVOID_LEFT_EXTRA_AFTER_SECOND_PASS = 7
AVOID_LEFT_TURN_TO_LINE = 8
AVOID_LEFT_SEARCH_LINE = 9
AVOID_LEFT_ALIGN_ON_LINE = 10
```

Inhaltliche Logik:

- links rausdrehen
- Hindernis rechts suchen
- am Hindernis rechts vorbeifahren
- Zusatzschritte
- parallel drehen
- Hindernis rechts erneut suchen
- erneut vorbeifahren
- Zusatzschritte
- zur Linie drehen
- Linie suchen
- auf Linie ausrichten

## Spiegelprüfung AVOID_RIGHT / AVOID_LEFT

Die beiden Umfahrungen wurden heute gegeneinander geprüft.

Ergebnis:

- `AVOID_RIGHT` nutzt den linken US-Sensor.
- `AVOID_LEFT` nutzt den rechten US-Sensor.
- Die Drehrichtungen sind spiegelverkehrt korrekt.
- Beide Umfahrungen springen bei früh erkannter Linie in ihren jeweiligen `*_ALIGN_ON_LINE`-Unterzustand.
- Beide wechseln bei erfolgreichem Abschluss zurück nach `LINE_FOLLOWING`.
- Beide wechseln bei Such-Timeout nach `AVOID_NOT_POSSIBLE`.

## Darstellung Im Zustandsdiagramm

Im Zustandsdiagramm sollen keine Zahlen `0`, `1`, `2` stehen.

Die Zahlen sind nur interne Codewerte.

Im Diagramm sollen die benannten Unterzustände stehen, z.B.:

```text
AVOID_LEFT
  AVOID_LEFT_TURN_OUT
  AVOID_LEFT_FIND_OBSTACLE
  AVOID_LEFT_PASS_OBSTACLE
  ...
```

und:

```text
AVOID_RIGHT
  AVOID_RIGHT_TURN_OUT
  AVOID_RIGHT_FIND_OBSTACLE
  AVOID_RIGHT_PASS_OBSTACLE
  ...
```

## Bewusst Noch Nicht Umgesetzt

Folgende Punkte sind noch nicht integriert:

- Magnetschalter / Deckel-Logik in `USER_PAUSED`
- Webapp-/Netzwerkbefehle im neuen `global_controller_test.py`
- finale physische Kalibrierung der Schrittzahlen
- finale physische Kalibrierung der Ultraschall-Grenzwerte
- finale Kalibrierung des Füllstandsensors

## Offene Hinweise Für Den Nächsten Entwickler

1. `global_controller_test.py` ist aktuell die relevante Schritt-für-Schritt-Datei.
2. `global_controller.py` existiert ebenfalls, ist aber nicht der aktuelle Arbeitsstand.
3. Die Umfahrung ist nicht als echte verschachtelte Python-State-Machine umgesetzt, sondern als Hauptzustand plus `avoid_step`.
4. Das ist bewusst so gewählt, weil es in MicroPython einfacher und robuster ist.
5. Wenn später Netzwerk/Webapp integriert wird, sollten die Befehle nur `request_goto_street()` und `request_return_home()` auslösen.
6. Vor realen Fahrtests müssen `avoid_turn_90_steps`, `turn_home_180_steps`, `avoid_extra_steps`, `avoid_speed` und `avoid_turn_speed` kalibriert werden.
7. Die Touchpanel-Statusanzeigen sind angebunden, aber sollten bei realen Tests auf korrekte Screens geprüft werden.

## Wichtige Testfälle

Für die nächste Testsession sollten mindestens diese Fälle geprüft werden:

1. Start zuhause -> Linie folgen -> Endmarkierung Straße -> `WAIT_AT_STREET`
2. Straße -> `goto_home` -> `TURN_AT_STREET` -> Linie folgen
3. Rückfahrt -> Endmarkierung zuhause -> `TURN_AT_HOME` -> Rückwärtsfahrt -> `AT_HOME`
4. Linie verloren -> 10 Sekunden weiterfahren -> Stopp + Buzzer
5. Hindernis vorne kurzzeitig -> Stopp -> Hindernis entfernt -> weiterfahren
6. Hindernis vorne bleibt -> rechts frei -> `AVOID_RIGHT`
7. Hindernis vorne bleibt -> rechts blockiert, links frei -> `AVOID_LEFT`
8. Beide Seiten blockiert -> `AVOID_NOT_POSSIBLE`
9. Linie während Umfahrung früh erkannt -> jeweiliger `*_ALIGN_ON_LINE`-Unterzustand

