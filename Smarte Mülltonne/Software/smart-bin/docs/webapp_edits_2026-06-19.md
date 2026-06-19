# Web-App-Edits 2026-06-19

Dieses Dokument haelt die letzten Web-App- und Simulationsaenderungen fest.
Es ist als schneller Wiedereinstieg fuer die naechste Session gedacht.

## Ziel der letzten Runde

Die Web-App sollte die reale Idee der smarten Tonne besser abbilden:

- Tonnen stehen normalerweise am Haus.
- Wenn eine Abholung geplant wird, fahren relevante Tonnen zur Abholposition an der Strasse.
- Der Muellwagen faehrt eine Strassenroute, haelt an passenden Tonnen, leert sie und faehrt danach weiter.
- Leere oder nicht sammelrelevante Tonnen duerfen nicht extra zur Strasse fahren und den Truck blockieren.
- Die Karte soll bei hoher Simulationsgeschwindigkeit nicht mehr sprunghaft wirken.

## Frontend

### Statussymbole in der Flottenliste

In `frontend/app/dashboard/components/FleetPanel.tsx` werden die Statusicons fuer
Standort/Zielzustand eingebunden:

- `frontend/public/icons/status-home.svg`
- `frontend/public/icons/status-truck.svg`

Die Anzeige entscheidet anhand `location_state`:

- `truck` oder `moving_to_pickup` => Abholposition/Muellwagen-Icon
- alle anderen Werte => Zuhause-Icon

Zusaetzlich werden Meldungen wie Schadens- und Hygienemeldung mit eigenen kleinen
Icons und Farben in der Flottenliste hervorgehoben.

### Security-/Meldungspanel

In `frontend/app/dashboard/components/SecurityPanel.tsx` werden offene Meldungen
sichtbar fuer Operatoren dargestellt:

- `damage_report` => Werkzeug/Wrench-Icon, roter Ton, optional Sperren
- `hygiene_report` => Sparkles-Icon, gelber Ton
- andere Events => Warnsymbol

Die Meldungen koennen quittiert werden. Kritischere Meldungen bieten zusaetzlich
eine Sperraktion.

### Karte und Bewegungsdarstellung

In `frontend/app/dashboard/components/LeafletMap.tsx` wurden mehrere Punkte
verbessert:

- Tonne nutzt aktuelle Koordinaten ueber `current_lat/current_lng`, wenn vorhanden.
- Hausposition und Abholposition werden ueber `home_lat/home_lng` und
  `pickup_lat/pickup_lng` unterschieden.
- Bewegungswege von Haus zu Abholposition werden als gestrichelte Linien gezeigt,
  wenn die Tonne zur aktiven Route gehoert oder sich gerade bewegt.
- Abholpunkte werden mit kleinen Kreis-Markern sichtbar gemacht.
- Die aktive Truck-Route nutzt bevorzugt OSRM-Geometrie und folgt damit echten
  Strassen.
- Nur wenn keine OSRM-Geometrie vorhanden ist, faellt die UI auf gestrichelte
  Luftlinien zurueck.

### Sanftere Bewegung

Truck- und Tonnenmarker interpolieren ihre Positionen zwischen WebSocket-Updates
per `requestAnimationFrame`.

Grund:

- Bei 10x/20x Simulation wirkten Truck und Tonnen vorher sprunghaft.
- Kurven konnten so aussehen, als fliege der Truck kurz ueber die Karte.

Aktuelle Loesung:

- Kleine Positionsupdates werden animiert.
- Sehr grosse Spruenge werden bewusst direkt gesetzt, damit alte/weit entfernte
  Positionen nicht ueber die Karte interpoliert werden.

### Truck-Fokus

In der Karte gibt es einen Truck-Fokus-Button:

- Icon `Crosshair`, wenn Fokus aus ist.
- Icon `Truck`, wenn Fokus aktiv ist.
- Bei aktivem Fokus wird die Karte laufend auf den Truck zentriert.

Das hilft beim Beobachten der Route, besonders bei hoeherer Simulationsgeschwindigkeit.

## Backend und Simulation

### Home- und Pickup-Positionen

In `backend/database.py` wurden zusaetzliche Bewegungsfelder modelliert bzw.
migriert:

- `home_lat`, `home_lng`
- `pickup_lat`, `pickup_lng`
- `current_lat`, `current_lng`
- `movement_state`

Die initiale Logik:

- Bestehende Koordinaten gelten als Abhol-/Strassennaehe.
- Hauspositionen werden deterministisch versetzt, damit Bewegung sichtbar ist.
- Abholpositionen werden, soweit moeglich, zur naechstgelegenen Strasse gelegt.

Damit wirkt die Simulation weniger zufaellig als vorher.

### Route nur fuer sammelbare Tonnen

In `backend/services/truck_simulator.py` gibt es eine Sammelbarkeitslogik:

- Tonne muss existieren.
- Tonne darf nicht gesperrt sein.
- Fuellstand muss ueber dem Sammel-Schwellwert liegen.

Leere oder nicht sammelbare Tonnen sollen:

- nicht zur Abholposition geschickt werden,
- nicht vom Truck als echter Stopp behandelt werden,
- nicht dazu fuehren, dass der Truck unnoetig wartet.

Diese Constraint war wichtig, weil leere Tonnen zeitweise trotzdem zur Strasse
gefahren sind und der Truck auf sie wartete.

### Timing: Tonne faehrt passend los

Beim Start einer Route wird fuer jede sammelbare Tonne berechnet:

- wann der Truck ungefaehr am Abholpunkt ankommt,
- wie lange die Tonne von Zuhause bis zur Abholposition braucht,
- wann sie losfahren muss, damit sie rechtzeitig bereitsteht.

Die Tonne soll also nicht sofort blind losfahren, sondern passend zur Route.

### Truck-Stopp und Entleerung

Der Truck haelt an Abholpunkten und wartet kurz, damit die Entleerung in der UI
realistischer wirkt. Erst danach wird die Tonne geleert und die Rueckfahrt der
Tonne nach Hause geplant.

### Depot-Rueckfahrt

Die Rueckfahrt zum Depot wird als eigene OSRM-Strassenroute berechnet. Sie soll
nicht die alte Abholroute oder eine Luftlinie wiederverwenden.

## Lokaler Demo-Zustand

Vor dem Netzwerk-/Pico-Debugging wurde die lokale Simulation auf einen vollen,
aber dynamischen Zustand gesetzt:

- alle 35 Tonnen stehen wieder zuhause,
- alle sind idle,
- Fuellstaende liegen dynamisch im vollen Bereich,
- nicht alle Tonnen sind exakt 100 Prozent.

Verifizierter Zustand:

```text
count: 35
min_fill: 73
max_fill: 100
home: 35
idle: 35
```

## Relevante Dateien

- `frontend/app/dashboard/components/FleetPanel.tsx`
- `frontend/app/dashboard/components/SecurityPanel.tsx`
- `frontend/app/dashboard/components/LeafletMap.tsx`
- `frontend/public/icons/status-home.svg`
- `frontend/public/icons/status-truck.svg`
- `backend/database.py`
- `backend/models/bin.py`
- `backend/services/truck_simulator.py`
- `backend/services/routing.py`

## Offene Punkte

- Noch einmal live pruefen, ob leere Tonnen wirklich nie mehr als Stopp
  behandelt werden.
- Bei 20x Simulation die Kurvenbewegung weiter beobachten.
- Die spaetere echte Pico-Telemetrie muss dieselben Felder fuellen:
  `location_state`, `movement_state`, `current_lat/current_lng`, `fill_level`,
  `battery` und Meldungs-Events.
