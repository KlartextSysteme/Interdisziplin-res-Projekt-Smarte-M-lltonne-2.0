# Claude-Code-Prompt: Routenplanung kapazitätsbasiert, auswählbar + dynamischer Verlauf

Du arbeitest im Repo der smarten Mülltonne:

```text
Smarte Mülltonne/Software/Flottenmanagement
```

Bitte lies zuerst zur Einordnung:

```text
docs/webapp_edits_2026-06-19.md
docs/claude_prompt_webapp_pico_integration_scope.md
```

## Ziel / Vision

Der Müllplanungs-Leitstand soll **dynamischer und spielerischer** werden. Heute
plant „Route planen" eine einzige TSP-Tour über *alle* Tonnen über dem
Füllstand-Schwellwert und zeigt sie als eine statische gelbe Linie. Das wirkt
statisch, ignoriert die begrenzte Kapazität des Müllwagens und lässt dem Bediener
keine Wahl.

Drei Kernideen:

1. **Kapazitätsbasierte Planung.** Routen berücksichtigen die Kapazität des
   Müllwagens und enthalten nur so viele Tonnen, wie bis zur vollen Beladung
   passen. Danach Rückfahrt zum Depot. Eine Fahrt = Schleife Depot → Tonnen →
   Depot. Welche Tonnen relevant sind, hängt am **Füllstand**.

2. **Mehrere Vorschläge, der Bediener wählt (Google-Maps-Stil).** Nach Klick auf
   „Route planen" werden **mehrere mögliche Routen** vorgeschlagen. Die vom System
   bevorzugte ist gelb vorausgewählt, die Alternativen liegen **gedämpft/grau**
   daneben. Per **Klick** wählt der Bediener eine Alternative — diese wird dann
   gelb und damit zur aktiven Fahrt. Das ist **optional**: Wer nichts klickt,
   fährt die autonome Default-Wahl. Vorbild: Google Maps mit Routen-Alternativen.

3. **Sich aufbauender, abschnittsweiser Routenverlauf.** Beim Start baut sich die
   gewählte Route sichtbar entlang des Fahrwegs auf. Die Route ist durch die
   **Abholpositionen der Tonnen** in Abschnitte geteilt (jede Abholposition liegt
   exakt auf dem Fahrweg). Wenn der Wagen an einer Abholposition steht, soll der
   **nächste Streckenabschnitt** klar hervorgehoben werden, damit man versteht,
   wohin er als Nächstes fährt. Vorbild: Google Maps mit Zwischenstopps.

Wichtig: weiterhin ein operativer Leitstand, keine Marketing-Oberfläche. Dunkle
UI, gelber Akzent, Karte im Zentrum. Keine Architektur-Neuerfindung, kein echter
VRP-Solver.

## Aktueller Stand (Ausgangslage im Code)

Backend:

- `backend/routers/routes.py`
  - plant per Nearest-Neighbour-„Street-Sweep" + OSRM-Geometrie.
  - 2-opt-Optimierung ist bereits implementiert, wird aktuell nur als
    Vergleichswert (Badge) genutzt, **nicht** als Fahrreihenfolge → guter
    Ausgangspunkt für eine **Alternativ-Route**.
  - `FILL_THRESHOLD = 60` — nur Tonnen ab 60 % werden angefahren.
  - kennt **keine** Kapazitätsgrenze; alle Tonnen über Schwelle landen in *einer*
    Route.
- `backend/services/truck_simulator.py`
  - hat bereits `TRUCK_CAPACITY_UNITS = 5000.0`, trackt `load_units`, kennt
    Zustände `returning_full`, `unloading`.
  - `_project_point_to_route_m` projiziert die Truck-Position auf die Route →
    Basis für den Fahrt-Fortschritt.
- `backend/models/route.py` — Persistenz (waypoints, geometry, …).

Frontend:

- `frontend/app/dashboard/page.tsx` — Button „Route planen" ruft `planRoute()`,
  hält `activeRoute`, zeigt Distanz/Dauer + Optimierungs-Badge.
- `frontend/app/dashboard/components/LeafletMap.tsx`
  - zeichnet die Route als **eine** gelbe `Polyline` (`geometryLine`, ca. Z. 485).
  - Marker interpolieren weich; Truck-Fokus-Button existiert.
- `frontend/types/index.ts` — `interface Route { waypoints, geometry, distance_m, … }`.
- `frontend/lib/` — API-Aufrufe inkl. `planRoute`.

## Aufgabe 1: Kapazität als Planungsgrenze (Backend)

In `backend/routers/routes.py` die Planung kapazitätsbewusst machen.

- „Beladungseinheit" pro Tonne aus deren `fill_level` ableiten (konsistent zum
  Simulator: dort entspricht der eingesammelte Füllstand den `load_units`).
- Kapazität aus **einer** gemeinsamen Konstante/Config (heute `TRUCK_CAPACITY_UNITS`),
  von Planung und Simulator gemeinsam genutzt (kein doppelter Wahrheitswert).
- Sammelreihenfolge so abschneiden, dass die kumulierte Beladung die Kapazität
  nicht überschreitet; sobald die nächste Tonne nicht mehr passt, endet die Fahrt.
- Route als Schleife **Depot → Tonnen → Depot** inkl. Rückfahrt-Geometrie.

Resttonnen (passen nicht in diese Fahrt) bleiben für die nächste Planung übrig.
Mehrere *aufeinanderfolgende* Trips sind hier **nicht** das Ziel — die „mehreren
Routen" meinen Alternativen zur Auswahl (Aufgabe 2), nicht mehrere Fahrten.

## Aufgabe 2: Mehrere Routen-Vorschläge erzeugen + auswählbar machen

Kern der „spielerischen" Interaktion.

### Backend: 2–3 Kandidaten statt einer Route

- `planRoute` soll eine **Liste von Kandidaten-Routen** zurückgeben (nicht eine).
- Jede Kandidatin ist kapazitätsbegrenzt (Aufgabe 1) und hat eigene Geometrie.
- Echte VRP-Diversität ist nicht nötig. Kandidaten aus **billigen Variationen**
  derselben Heuristik ableiten, damit sie sichtbar verschieden sind, z. B.:
  - Kandidat A: Nearest-Neighbour-Street-Sweep (heutiges Verhalten).
  - Kandidat B: 2-opt-optimierte Reihenfolge (im Code schon vorhanden).
  - Kandidat C: anderer Startpunkt/Cluster oder anderes Kapazitäts-Füllziel
    (z. B. „nur fast volle Tonnen zuerst").
- Pro Kandidatin Kennzahlen mitliefern: Tonnenanzahl, geschätzte Beladung
  (Einheiten + % Auslastung), Distanz, Dauer, und welche als System-Default
  empfohlen ist.
- Duplikate (identische Reihenfolge) zusammenfassen, damit nicht 3× dieselbe Linie
  erscheint.

### Frontend: Auswahl per Klick (Google-Maps-Muster)

- `frontend/types/index.ts`: additiv ein `RoutePlan`/`RouteCandidate`-Konzept
  ergänzen (Liste), bestehende `Route`-Felder nicht brechen.
- `frontend/app/dashboard/page.tsx`: Zustand für `candidates` + `selectedRouteId`
  halten (kein State-Lib). System-Default vorauswählen.
- `frontend/app/dashboard/components/LeafletMap.tsx`:
  - **nicht gewählte** Kandidaten gedämpft/grau und dünner zeichnen.
  - **gewählte** Kandidatin in Gelb, kräftiger, im Vordergrund.
  - Klick auf eine graue Linie (oder auf einen Listeneintrag) wählt sie aus →
    wird gelb. Hover hebt sie leicht an.
- Erst die **gewählte** Route wird beim Start tatsächlich gefahren (an die
  bestehende Start-/Aktivierungslogik übergeben).

Bitte sauber trennen: „geplant/vorgeschlagen" (mehrere, auswählbar) vs.
„aktiv/wird gefahren" (genau eine). Die Auswahl ist **optional** — ohne Klick
fährt der Default.

## Aufgabe 3: Abschnittsweiser, sich aufbauender Routenverlauf (Frontend)

In `frontend/app/dashboard/components/LeafletMap.tsx`, sobald eine Route aktiv ist
und der Wagen fährt.

- Die Route in **Abschnitte** teilen, **getrennt an den Abholpositionen** der
  Tonnen (jede Abholposition liegt exakt auf der Geometrie). Abschnitt = Stück
  zwischen zwei aufeinanderfolgenden Abholpunkten (bzw. Depot ↔ erste/letzte
  Tonne).
- **Aufbau beim Start:** die Linie nicht komplett statisch zeigen, sondern sich
  entlang des Fahrwegs aufbauen lassen (Fortschritt aus der Truck-Position auf der
  Route, vgl. `_project_point_to_route_m` im Simulator).
- **Gefahren vs. kommend** visuell trennen (gefahren gedämpft, kommend gelb).
- **Nächster Abschnitt:** wenn der Wagen an einer Abholposition steht, den
  Abschnitt zur *nächsten* Tonne klar betonen (kräftiger / Pfeilrichtung / Pulse),
  analog zu Google Maps beim Anfahren des nächsten Zwischenstopps. Nach jeder
  geleerten Tonne (`fill_level → 0` / Truck-Event `emptying`) rückt die
  Hervorhebung auf den folgenden Abschnitt weiter.
- Weiche Marker-Interpolation und Truck-Fokus-Button erhalten und sinnvoll
  zusammenspielen lassen.

Rein clientseitig aus dem vorhandenen WebSocket-/Positionsstrom ableiten, keine
zusätzliche Polling-Schleife.

## Aufgabe 4: „Route planen"-Panel spielerischer (UI)

Im Bereich um den „Route planen"-Button / das Route-Badge in `page.tsx`:

- Nach dem Planen eine kompakte Vorschlagsliste zeigen: pro Kandidatin Tonnenzahl,
  Auslastung (z. B. „4.200 / 5.000 Einheiten · 84 %"), Distanz, Dauer; die
  Default-Empfehlung markiert.
- Hover/Klick auf einen Listeneintrag synchron mit der Karten-Hervorhebung
  (Liste ↔ Linie verknüpft).
- Deutlich machen: gezeigt wird die Fahrt bis zur Depot-Rückkehr (kapazitäts-
  begrenzt). Falls Tonnen übrig bleiben, Hinweis „X volle Tonnen erst in der
  nächsten Fahrt".
- Stil an die bestehende Leitstand-UI, nicht überladen.

## Empfohlene Umsetzungsreihenfolge

Inkrementell, jeder Schritt für sich lauffähig und buildbar:

1. **Aufgabe 1 — Kapazitätsgrenze (Backend).** Kleinste, fundamentalste Änderung;
   verändert nur, *welche* Tonnen in der Route landen. Sofort als kürzere Linie
   sichtbar, ohne UI-Umbau.
2. **Aufgabe 3 — abschnittsweiser, sich aufbauender Verlauf (Frontend).** Größter
   „dynamischer"-Effekt, braucht keine neue Auswahl-UI. Baut nur auf der einen
   aktiven Route auf.
3. **Aufgabe 2 — mehrere Vorschläge + Klick-Auswahl.** Erst Backend-Kandidatenliste,
   dann Frontend-Auswahl (grau → gelb). Optionaler Layer obendrauf; bricht die
   bisherigen Schritte nicht.
4. **Aufgabe 4 — Vorschlags-Panel-Feinschliff (UI).** Kennzahlen, Liste ↔ Linie
   verknüpfen, Auslastungsanzeige.

So bleibt nach jedem Schritt ein vorzeigbarer Zustand, und die interaktive
Auswahl (der optionale Teil) kommt zuletzt.

## Nicht im Scope

- Komplettes Redesign, neue State-Management-Library.
- Echter VRP-/CVRP-Solver (billige Heuristik-Varianten genügen für die
  Alternativen).
- Mehrere *aufeinanderfolgende* Trips in einer Planung (bewusst später).
- Auth/Login, Consumer-Onboarding, große DB-Migrationen, Render-/Deployment-Umbau.
- Echte Pico-Firmware.

## Qualitätsanforderungen

- TypeScript und Python sauber halten, bestehende Struktur respektieren.
- Kleine, fokussierte Änderungen, keine unrelated Refactors.
- Kapazitätskonstante an einer Stelle, von Planung und Simulator gemeinsam genutzt.
- Klare Trennung: vorgeschlagen (mehrere) vs. aktiv (eine).
- UI darf auf Desktop und kleineren Viewports nicht überlaufen.
- Build muss laufen:

```bash
cd "Smarte Mülltonne/Software/Flottenmanagement/frontend"
npm run build
```

- Falls Backend geändert:

```bash
cd "Smarte Mülltonne/Software/Flottenmanagement/backend"
./.venv/bin/python -m compileall main.py routers services models
```

> Hinweis Build-Umgebung: Das Repo liegt unter `~/Documents` (iCloud). Wenn
> `next build` ohne CPU-Last hängt, sind `node_modules`-Dateien iCloud-ausgelagert
> (`dataless`). Fix: `rm -rf node_modules && npm ci`.

## Erwartetes Ergebnis

Am Ende bitte kurz dokumentieren:

- Wie die Kapazitätsgrenze in die Planung einfließt und wo sie definiert ist.
- Wie die mehreren Kandidaten erzeugt werden (welche Variationen) und wie die
  Auswahl per Klick funktioniert (grau → gelb, optional, Default autonom).
- Wie der abschnittsweise, sich aufbauende Verlauf technisch funktioniert
  (Abschnittsgrenzen = Abholpositionen, Fortschritt aus Truck-Position,
  Hervorhebung des nächsten Abschnitts).
- Welche neuen Felder/`types` hinzukamen.
- Welche Folgeideen offen bleiben (mehrere aufeinanderfolgende Trips, echte
  diverse Alternativen, Echtzeit-Pico-Beladung).
