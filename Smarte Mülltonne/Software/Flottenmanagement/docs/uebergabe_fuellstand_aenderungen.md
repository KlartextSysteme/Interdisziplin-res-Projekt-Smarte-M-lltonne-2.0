# Übergabe: Füllstand-Test mit vorderem Ultraschallsensor

Stand: 27.06.2026

## Ziel der Änderung

Der vordere Ultraschallsensor soll kurzfristig zusätzlich als Füllstandsensor genutzt werden, damit der Füllstand der Mülltonne getestet werden kann, ohne einen separaten Füllstandsensor anzuschließen.

Wichtig: Der vordere Ultraschallsensor wird weiterhin für die Hinderniserkennung benötigt. Deshalb wird die Füllstandmessung aktuell nur in stehenden Zuständen verwendet.

## Geänderte Dateien

- `main.py`
- `global_controller_test.py`
- vorhandene Klasse in `ultraschallsensor.py`: `FuellstandSensor`

## Umsetzung in `main.py`

In der `main.py` wird der vorhandene vordere Ultraschallsensor aus `HindernisSensoren` zusätzlich an einen `FuellstandSensor` übergeben.

Dadurch wird kein neuer Ultraschallsensor benötigt. Für den Test wird dieser Sensor wiederverwendet:

```python
fuellstand_sensor = FuellstandSensor(
    ultrasonic=obstacle_sensors.front,
    leer_abstand_cm=FUELLSTAND_LEER_CM,
    voll_abstand_cm=FUELLSTAND_VOLL_CM,
)
```

Die aktuellen Testwerte sind:

```python
FUELLSTAND_LEER_CM = 40
FUELLSTAND_VOLL_CM = 5
```

Bedeutung:

- Abstand kleiner/gleich 5 cm: Mülltonne voll, also 100 Prozent.
- Abstand um 40 cm oder größer: Mülltonne leer, also 0 Prozent.
- Dazwischen wird linear in Prozent umgerechnet.

## Umsetzung im `GlobalController`

Der `GlobalController` bekommt den Füllstandsensor zusätzlich übergeben:

```python
fuellstand_sensor=fuellstand_sensor
```

Im Controller wurde dazu ein neues Attribut ergänzt:

```python
self.fuellstand_sensor = fuellstand_sensor
```

Die Füllstandmessung wird aktuell nur in diesen Zuständen aufgerufen:

- `AT_HOME`
- `WAIT_AT_STREET`

Damit stört die Füllstandmessung nicht die Hinderniserkennung während der Fahrt.

## Debug-Ausgabe für den Test

Zur Kontrolle am PC wurde eine Debug-Ausgabe ergänzt. Diese gibt Abstand, berechneten Füllstand und Deckelstatus aus.

Beispielausgabe:

```text
Fuellstand-Test | Abstand cm: 23.4 | Fuellstand: 47 | Deckel offen: False
```

Die Ausgabe läuft über die vorhandene Debug-Logik des Controllers und erscheint daher nicht in jedem Schleifendurchlauf, sondern zeitlich begrenzt.

## Wichtige Erkenntnisse

Der vordere Ultraschallsensor kann für den Füllstandstest verwendet werden, solange die Mülltonne steht. Während der Fahrt sollte er vorrangig für die Hinderniserkennung verwendet werden.

Die Füllstandmessung sollte nicht parallel zur Hinderniserkennung im Fahrbetrieb laufen, weil beide Funktionen denselben Sensor nutzen. Sonst kann es zu unklaren Messergebnissen oder verzögerter Hinderniserkennung kommen.

Für den aktuellen Test ist wichtig: Ein Abstand größer als 40 cm soll als leer gelten. Das darf nicht automatisch als offener Deckel interpretiert werden.

Falls in `FuellstandSensor.update_from_distance()` noch eine Logik steht, die Abstände größer als `leer_abstand_cm + deckel_offen_margin_cm` als `deckel_offen = True` wertet, muss diese für den aktuellen Test angepasst werden. Für den Test soll gelten:

```python
if distance >= self.leer_abstand_cm:
    self.deckel_offen = False
    self.fuellstand_prozent = 0
    self._no_echo_count = 0
    return
```

## Noch zu prüfen

- Ob die Werte `40 cm` für leer und `5 cm` für voll zur realen Mülltonnenhöhe passen.
- Ob die Messrichtung des vorderen Ultraschallsensors für den Füllstand mechanisch sinnvoll ist.
- Ob der Sensor bei leerer Tonne zuverlässig Werte über 40 cm liefert oder Timeouts auftreten.
- Ob `None` weiterhin als offener Deckel oder Messfehler behandelt werden soll.
- Ob später ein eigener Füllstandsensor verwendet wird, damit Hinderniserkennung und Füllstandmessung getrennt sind.

## Aktueller Testablauf

1. Pico starten.
2. Mülltonne im Zustand `AT_HOME` oder `WAIT_AT_STREET` stehen lassen.
3. PC-Ausgabe beobachten.
4. Auf Zeilen mit `Fuellstand-Test` achten.
5. Abstand und Prozentwert mit realem Füllstand vergleichen.
6. Danach `FUELLSTAND_LEER_CM` und `FUELLSTAND_VOLL_CM` bei Bedarf anpassen.

