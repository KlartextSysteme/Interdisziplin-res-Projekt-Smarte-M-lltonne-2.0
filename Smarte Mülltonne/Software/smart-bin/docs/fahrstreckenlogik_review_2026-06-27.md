# Fahrstreckenlogik — Dokumentation & Code-Review (2026-06-27)

Dieses Dokument beschreibt die aktuelle Logik, wie eine Sammelfahrt entsteht und
abgefahren wird, und erklärt die beobachtete Auffälligkeit: *volle Tonnen werden
übersprungen, obwohl der Wagen in der Straße steht, und erst „in der nächsten
Runde" geleert.*

Relevante Dateien:
- `backend/routers/routes.py` — Planung + Kapazitäts-Cutoff + Kandidaten
- `backend/services/truck_simulator.py` — Fahren, Sammeln, Entladen, Auto-Replan

## Update (umgesetzt) — Stand nach Review

Die im Review beschriebenen Schwächen wurden behoben:

1. **Opportunistisches Sammeln (positionsbasiert)** — der Wagen nimmt *jede*
   volle, freigegebene Tonne mit, an deren Abholposition er vorbeikommt und für
   die noch Kapazität frei ist (Route ODER nicht), unabhängig von der geplanten
   Reihenfolge. Behebt das „Vorbeifahren an vollen Tonnen" (Punkte (a)+(b) unten).
   Umsetzung über `_advance_with_arrival_check` mit Kapazitäts-Grenze; passt eine
   Tonne nicht mehr rein, bleibt sie für die nächste Runde (kein Überladen).
2. **Voll → direkt zum Depot** — sobald nicht mal die kleinste sammelbare Tonne
   (>= 60 %) noch reinpasst, bricht der Wagen die geplante Route ab und fährt auf
   direktem (OSRM-)Weg zum Depot, statt die restliche Route durch Seitenstraßen
   mit nicht mehr sammelbaren Tonnen abzuklappern. Rest → Auto-Replan.
3. **Exakter Fahrt-Fortschritt** — das Backend meldet `route_progress` (0..1) im
   Truck-Status. Das Frontend teilt damit eindeutig in gefahren (grau) / kommend
   (gelb), ohne Projektion → robust gegen die Depot-Doppeldeutigkeit und
   selbstkreuzende Routen (kein „gelb hinter dem Wagen").
4. **Robustere Rückfahrt-Erkennung** — Status „returning", sobald nichts mehr zu
   sammeln ist (statt „alle Waypoints besucht"), da mit Kapazitäts-Grenze geplante
   Tonnen übrig bleiben können.

Hinweis: Das „Sammeln nach Listenreihenfolge" und die strikte Stopp-Planung
(`_advance_with_planned_stop`, `_next_unvisited_waypoint`,
`_position_at_route_progress`) wurden durch das positionsbasierte Sammeln ersetzt
und als toter Code entfernt.

Die folgenden Abschnitte beschreiben den Stand *vor* diesen Änderungen (zur
Nachvollziehbarkeit der ursprünglichen Logik).

## 1. Pipeline im Überblick

```
Route planen ─▶ Tonnen ≥ 60% ─▶ 3 Kandidaten (Ziel-Reihenfolge) ─▶ Kapazitäts-Cutoff
        ─▶ Default aktiv ─▶ Simulator fährt aktive Route ─▶ sammelt in Reihenfolge
        ─▶ Depot-Entladung ─▶ Auto-Replan für Resttonnen (nächster Trip)
```

## 2. Planung (`routes.py: generate_route_candidates`)

1. Kandidaten-Tonnen: `locked == False` und `fill_level >= FILL_THRESHOLD` (60).
2. Drei Reihenfolgen (= die drei Buttons):
   - **Kürzeste Strecke** → 2-opt-Reihenfolge (geografisch kürzeste Tour).
   - **Dringendste zuerst** → Tonnen nach Füllstand *absteigend*.
   - **Meiste Tonnen** → Tonnen nach Füllstand *aufsteigend* (mehr passen rein).
3. **Kapazitäts-Cutoff** (`_capacity_cutoff`): geht die Tonnen *in dieser
   Reihenfolge* durch und nimmt sie auf, solange die kumulierte Beladung
   (Σ `fill_level`, 1 % ≈ 1 Einheit) die Kapazität (`truck_capacity_units`, aktuell
   **1500**) nicht überschreitet. Sobald die nächste Tonne nicht mehr passt, **endet
   die Auswahl** — der Rest landet **nicht** in `waypoints`.
4. OSRM-Geometrie wird **nur über die aufgenommenen Tonnen** berechnet
   (Depot → aufgenommene Pickups → Depot).

> Folge: Bei 35 vollen Tonnen passen mit 1500 Einheiten ≈ **17** in eine Fahrt.
> Die übrigen ≈18 sind in dieser Route gar nicht enthalten.

## 3. Fahren & Sammeln (`truck_simulator.py: _drive_route`)

- `waypoints` = die Tonnen der aktiven Route, **in Planungsreihenfolge**.
- `_coords_for_waypoint_legs` baut die Geometrie, indem es die Pickups **in
  Reihenfolge** abfährt, und liefert `stop_progress_by_bin` = kumulierte
  Streckenposition je Tonne (monoton steigend).
- Tonnen fahren parallel von Haus → Abholposition (`_schedule_route_bins_to_pickup`),
  zeitlich so geplant, dass sie etwa zum Truck-Eintreffen bereitstehen.
- Haupt-Loop pro Tick:
  1. `next_bin = _next_unvisited_waypoint(...)` → die **nächste Tonne in
     Listenreihenfolge** (nicht „die, an der der Truck gerade ist").
  2. `_advance_with_planned_stop(...)` fährt bis zur `stop_progress_m` **genau
     dieser** Tonne und hält.
  3. `_wait_for_bin_at_pickup` wartet bis `BIN_MAX_WAIT_S` (18 s), bis die Tonne
     an der Abholposition ist; ist sie noch voll/sammelbar, wird sie geleert.
  4. `_empty_bin` setzt `fill_level = 0`, Tonne fährt zurück nach Hause.
- Kapazitäts-Sicherung im Loop (`load + waste > capacity → Zwischenentladung`)
  greift im Normalfall **nicht**, weil bereits beim Planen gecuttet wurde.

## 4. Nach der Route

- `route.completed = True`, `route.active = False`, Entladung am Depot.
- `_maybe_plan_next_trip`: sind noch volle Tonnen da → **neue Route** (nächster
  Trip). So entsteht die Mehr-Trip-Kette, bis nichts mehr übrig ist.

## 5. Warum volle Tonnen „übersprungen" werden — die zwei Entscheidungen

Beide maßgeblichen Entscheidungen sind **reihenfolge-/kapazitätsbasiert** und
berücksichtigen **nicht**, wo der Wagen gerade physisch steht:

### (a) Kapazitäts-Cutoff → „nächste Runde" (häufigster Fall)
Tonnen jenseits der Kapazitätsgrenze sind **gar nicht in der Route**. Der Wagen
fährt aber die Straßen-Geometrie der *aufgenommenen* Tonnen — und diese führt
physisch an ausgeschlossenen vollen Tonnen vorbei. Aus Bedienersicht: „Der Wagen
steht direkt daneben, sammelt die volle Tonne aber nicht." Sie kommt erst im
Auto-Replan-Trip dran.

### (b) Strikte Reihenfolge-Sammlung → Vorbeifahren innerhalb eines Trips
Der Wagen sammelt **nur die jeweils nächste Tonne in der Listenreihenfolge**
(`_next_unvisited_waypoint`), nicht „die Tonne, an der ich gerade vorbeikomme".
Wenn die Heuristik-Reihenfolge nicht der geografischen Fahrtreihenfolge
entspricht, fährt der Wagen an einer Route-Tonne vorbei und sammelt sie erst
später, wenn sie „dran" ist. Besonders stark bei **Dringendste zuerst** und
**Meiste Tonnen**, weil die Sortierung nach Füllstand die Geografie komplett
ignoriert → die Fahrt zickzackt und passiert volle Tonnen mehrfach.

**Kernaussage:** Der Cutoff und das Sammeln sind *reihenfolge-basiert, nicht
geografie-bewusst*. Das ist die „unklare Entscheidung" hinter dem Verhalten.

## 6. Review-Befunde

- **Kein harter Bug:** Das Verhalten folgt der implementierten Logik. Aber es gibt
  eine **konzeptionelle Schwäche** (Sammeln/Cutoff ignorieren die Truck-Position).
- **Dormanter Code:** `_advance_with_arrival_check` *kann* „jede Tonne, an der man
  vorbeikommt, einsammeln" (prüft *alle* unbesuchten waypoints auf Nähe). Sie wird
  aber nur in `_drive_geometry` mit **leeren** `waypoints` aufgerufen (Z. 569) —
  also nie für echtes Sammeln. Genau diese Funktion wäre die Lösung für (b).
- **Kapazität 1500** ist bewusst niedrig (Grenze soll sichtbar greifen), erzeugt
  aber viele „nächste Runde"-Fälle.

## 7. Verbesserungsoptionen (priorisiert)

1. **Opportunistisches Sammeln** *(klein, großer Effekt — behebt (b))*: Im
   `_drive_route`-Loop zusätzlich prüfen, ob der Wagen an **irgendeiner** noch
   nicht besuchten Route-Tonne vorbeikommt (`ARRIVAL_THRESHOLD_M`) und sie dann
   sofort mitnehmen, statt strikt der Listenreihenfolge zu folgen. Die nötige
   Logik (`_advance_with_arrival_check`) existiert bereits.
2. **Geografie-bewusster Kapazitäts-Cluster** *(behebt (a))*: Statt „erste N der
   Heuristik-Reihenfolge" eine räumlich zusammenhängende Tonnen-Gruppe wählen, die
   den Wagen füllt (Greedy nach Nähe + Füllstand, Mini-CVRP). Dann liegen
   ausgeschlossene Tonnen weit weg → der Wagen fährt nicht an ihnen vorbei.
3. **„Dringendste/Meiste" geografisch glätten:** nach der Füllstand-Auswahl die
   Reihenfolge per 2-opt geografisch optimieren, damit die Fahrt nicht zickzackt.
4. **Kapazität erhöhen**, falls weniger „nächste Runde" gewünscht ist (Trade-off:
   die Kapazitätsgrenze wird weniger sichtbar).

Empfehlung: **Option 1 zuerst** (kleinster Eingriff, behebt das sichtbarste
Vorbeifahren innerhalb eines Trips), danach Option 2, falls das „Wagen passiert
ausgeschlossene volle Tonnen"-Verhalten weiter stören soll.
