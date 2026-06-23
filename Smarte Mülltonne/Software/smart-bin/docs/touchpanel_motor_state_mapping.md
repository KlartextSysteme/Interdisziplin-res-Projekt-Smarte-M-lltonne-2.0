# Touchpanel-Screens und Mapping zur Motor-State-Machine

Stand: 2026-06-22

Dieses Dokument ist fuer die Motorsteuerungsabteilung gedacht. Es beschreibt,
welche Screen-Namen es im Touchpanel-Code gibt, welche Statusscreens aus den
Wireframes damit gemeint sind und wie die State Machine (`GlobalController`) die
Anzeige spaeter ansteuern sollte.

## 1. Grundprinzip im Touchpanel-Code

Im Touchpanel gibt es zwei Ebenen von Screen-Namen:

1. **Technische Screen-Container**  
   Das sind die Namen, mit denen der Code zwischen Hauptansicht, PIN, Menues,
   Diagnose und Bestaetigung umschaltet.

2. **Statusscreen-Varianten innerhalb von `SCREEN_STATUS`**  
   Die eigentlichen Figma-Statusscreens links im Wireframe sind keine eigenen
   Top-Level-Screens, sondern Varianten des technischen Screens `status`. Sie
   werden ueber `status_kind`, `location`, `fill_level`, `line_ok`,
   `connected`, `locked` usw. gesteuert.

Relevante Datei:

```text
firmware/pico_touchpanel/ui.py
```

## 2. Technische Screen-Namen im Code

Diese Konstanten existieren aktuell in `ui.py`:

| Code-Name | Bedeutung | Anzeige-Dauer |
|---|---|---|
| `SCREEN_STATUS = "status"` | Haupt-/Statusansicht der Tonne | persistent, solange kein Menue/PIN geoeffnet wird |
| `SCREEN_PIN = "pin"` | PIN-Eingabe | persistent bis Zurueck oder korrekter PIN |
| `SCREEN_MENU_1 = "menu_1"` | Hauptmenue Seite 1 | persistent bis Navigation |
| `SCREEN_MENU_2 = "menu_2"` | Hauptmenue Seite 2 | persistent bis Navigation |
| `SCREEN_SUBMENU = "submenu"` | Untermenue, z.B. Deckel/Fahren/Problem | persistent bis Aktion oder Zurueck |
| `SCREEN_DIAGNOSE = "diagnose"` | Diagnosepanel | persistent bis Zurueck |
| `SCREEN_CONFIRM = "confirm"` | Bestaetigungsscreen | automatisch ca. 1,5 s, Touch springt sofort zurueck |

Aktuell ist im Code definiert:

```python
CONFIRM_MS = 1_500
```

Das betrifft nur die gelben Haken-/Bestaetigungsscreens, nicht die
Statusscreens.

## 3. Statusscreen-Varianten aus dem Wireframe

Alle folgenden Screens laufen technisch ueber:

```python
ui.set_status(status_kind="...")
```

oder ueber `location`, wenn nur zwischen Zuhause und Abholposition gewechselt
wird.

| Figma-/UI-Screen | Aktueller Code-Wert | Asset-Name | Wann anzeigen? | Anzeige-Dauer |
|---|---|---|---|---|
| Standard Zuhause, z.B. `Westfalenweg 8` mit Fuellstand | `status_kind="full_home"` und `location="home"` | `status_full_home_clean` | Tonne steht zuhause / im normalen Standby | persistent |
| Standard Abholposition / Muellwagen, z.B. `Westfalenweg 8` mit Fuellstand | `location="truck"` | `status_full_truck_clean` | Tonne steht an der Abholposition / wartet auf Leerung | persistent |
| Hindernis erkannt | `status_kind="obstacle"` | `status_obstacle` | Hindernissensor meldet Blockade | persistent, bis Hindernis frei bzw. State verlassen |
| Hilfe benoetigt | `status_kind="help"` | `status_help` | manueller/technischer Fehler, Eingriff noetig | persistent, bis Fehler quittiert/behoben |
| Linie erkannt | `status_kind="line_ok"` | `status_line_ok` | Linie wurde gefunden/erkannt | nur kurz oder Diagnose-nahe Anzeige, empfohlen 1,5-2 s |
| Linie verloren | `status_kind="line_lost"` | `status_line_lost` | Linienfolger findet Linie nicht mehr | persistent waehrend Such-/Lost-Zustand |
| Tonne faehrt | **noch zu ergaenzen:** `status_kind="driving"` | **neu:** `status_driving` | Tonne bewegt sich aktiv auf der Linie | persistent waehrend Fahrt |

Wichtig: Der neue Screen **"Tonne faehrt"** existiert laut Stand dieses Dokuments
noch nicht als eigener Asset-/Code-Zweig. Empfohlene technische Ergaenzung:

```python
elif self.status_kind == "driving":
    asset = "status_driving"
```

## 4. Mapping GlobalController-State -> Touchpanel-Status

Die Motorsteuerung arbeitet mit States aus:

```text
Software/Quellcode/Client/global_controller.py
```

Empfohlenes Mapping:

| GlobalController-State | Touchpanel-Aufruf | Gemeinter Screen |
|---|---|---|
| `STANDBY` | `ui.set_status(status_kind="full_home", location="home")` | Standard Zuhause |
| `LINE_FOLLOWING` | `ui.set_status(status_kind="driving")` | Tonne faehrt |
| `OBSTACLE` | `ui.set_status(status_kind="obstacle", obstacle_cm=...)` | Hindernis erkannt |
| `LINE_LOST` | `ui.set_status(status_kind="line_lost", line_ok=False)` | Linie verloren |
| Linie wiedergefunden / Suchphase erfolgreich | `ui.set_status(status_kind="line_ok", line_ok=True)` | Linie erkannt |
| `WAIT_AT_STREET` | `ui.set_status(status_kind="full_home", location="truck")` | an Abholposition / wartet |
| `ARRIVED` | je nach Ziel kurz `line_ok` oder direkt Zielscreen | Ankunft / Uebergang |
| `FULL` | `ui.set_status(fill_level=100, status_kind="full_home")` | Standardscreen mit vollem Fuellstand |
| `EMPTIED` | `ui.set_status(fill_level=0, location="truck")` | geleert an Abholposition |
| `USER_PAUSED` | aktuell am ehesten `status_kind="help"` | Hilfe benoetigt / pausiert |
| `AVOID_*` | aktuell am ehesten `status_kind="obstacle"` oder spaeter eigener Screen | Ausweich-/Blockadezustand |
| `AVOID_NOT_POSSIBLE` | `ui.set_status(status_kind="help")` | Hilfe benoetigt |
| `OFFLINE` / kein Serverkontakt | `ui.set_status(connected=False)` | Statusleiste zeigt Verbindung getrennt |
| `CONNECTED` | `ui.set_status(connected=True)` | Statusleiste zeigt verbunden |

## 5. Anzeige-Dauer und Prioritaeten

### Dauerhafte Statusscreens

Diese Screens bleiben sichtbar, solange der jeweilige Zustand aktiv ist:

- Zuhause / normaler Status
- Abholposition / wartet
- Tonne faehrt
- Hindernis erkannt
- Linie verloren
- Hilfe benoetigt

Die State Machine sollte sie also nicht per Timer ausblenden, sondern erst durch
einen neuen Zustand ersetzen.

### Kurzzeitige Statusscreens

`Linie erkannt` sollte nicht dauerhaft den normalen Fahr- oder Standby-Screen
ueberschreiben. Empfehlung:

- 1,5-2 Sekunden anzeigen,
- danach automatisch zurueck auf `status_kind="driving"` oder den vorherigen
  Hauptzustand.

Wenn die Motorsteuerung diesen Timer nicht selbst bauen will, kann das spaeter
im Touchpanel als eigener transienter Status implementiert werden.

### Confirm-Screens

Die Bestaetigungsscreens sind bereits im Touchpanel-Code geloest:

- Anzeigezeit: `CONFIRM_MS = 1_500`
- bei Touch: sofort zurueck

Diese Screens sind fuer Menueaktionen gedacht, z.B. Sperren, Verbindung,
Problemmeldung, nicht fuer Motor-State-Feedback.

## 6. Empfohlene Integrationsstelle

Die Motorsteuerung sollte nicht direkt Assets zeichnen. Stattdessen sollte sie
eine kleine Adapterfunktion aufrufen, z.B.:

```python
def update_touchpanel_from_state(controller, ui):
    state = controller.state

    if state == controller.STATE_LINE_FOLLOWING:
        ui.set_status(status_kind="driving")
    elif state == controller.STATE_OBSTACLE:
        ui.set_status(status_kind="obstacle", obstacle_cm=None)
    elif state == controller.STATE_LINE_LOST:
        ui.set_status(status_kind="line_lost", line_ok=False)
    elif state == controller.STATE_WAIT_AT_STREET:
        ui.set_status(status_kind="full_home", location="truck")
    elif state == controller.STATE_STANDBY:
        ui.set_status(status_kind="full_home", location="home")
```

Die Funktion sollte immer dann laufen, wenn sich der State aendert, nicht
unnoetig in jedem Loop mit voller Frequenz. Wenn Fuellstand/Akku/Sensorwerte
aktualisiert werden, kann `ui.set_status(fill_level=..., connected=..., ...)`
zusaetzlich in einem langsameren Takt laufen.

## 7. Touchpanel-Menueaktionen fuer Motorsteuerung

Das Touchpanel erzeugt bei Menue-Aktionen aktuell stabile Action-Namen. Die
Motorsteuerung bzw. der Global Controller kann diese spaeter im `action_handler`
entgegennehmen.

Relevante Action-Namen:

| Touchpanel-Aktion | Bedeutung fuer Motorsteuerung |
|---|---|
| `goto_street` | Fahre zur Abholposition / Strasse |
| `goto_home` | Fahre zurueck nach Hause |
| `lid_open` | Deckel oeffnen |
| `lid_close` | Deckel schliessen |
| `report_damage` | Schadensmeldung ausloesen |
| `report_hygiene` | Hygienemeldung ausloesen |
| `lock` | Tonne sperren |
| `unlock` | Tonne entsperren |
| `shutdown` | Ausschalten |
| `factory_reset` | Werkeinstellungen / Reset |
| `eco` | Eco-Modus / Display abdunkeln |
| `goto_dock` | zur Dockingstation fahren |
| `connect` | Verbindung herstellen |
| `disconnect` | Verbindung trennen |

Für die Fahrbefehle bietet sich ein Mapping auf die vorhandenen Commands an:

```text
goto_street -> CMD_GOTO_STREET
goto_home   -> CMD_RETURN_HOME
```

## 8. Was noch fehlt

Für die Motorsteuerungsintegration fehlen aus Touchpanel-Sicht noch:

1. Neuer Asset-/Code-Zweig fuer `status_kind="driving"` / Screen "Tonne faehrt".
2. Optional ein transienter Mechanismus fuer `line_ok`, damit "Linie erkannt"
   nach 1,5-2 Sekunden automatisch wieder zum Fahrzustand zurueckspringt.
3. Ein sauberer Adapter zwischen `GlobalController.state` und `TouchUi.set_status`.
4. Entscheidung, ob `AVOID_*` Zustaende alle als `obstacle` laufen oder spaeter
   eigene Screens bekommen.
