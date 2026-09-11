# Claude-Code-Prompt: WebApp glätten und Pico-Integration vorbereiten

Du arbeitest im Repo der smarten Mülltonne:

```text
Smarte Mülltonne/Software/Flottenmanagement
```

Bitte lies zuerst diese beiden aktuellen Übergabedokumente:

```text
docs/webapp_edits_2026-06-19.md
docs/connection_notes_2026-06-19.md
```

## Ziel

Die WebApp soll als Leitstand für die smarte Mülltonne sauberer, bedienbarer und
integrationsbereit für den Pico/Touchpanel-Flow werden. Bitte keine große
Design-Neuerfindung und keine Marketing-Oberfläche bauen. Es ist eine operative
Dashboard-WebApp für Operatoren, nicht für Endverbraucher.

Die App soll weiterhin wie ein kompakter Leitstand wirken:

- dunkle UI als Basis,
- gelber Akzent passend zum Touchpanel,
- Karte im Zentrum,
- links die Flotte,
- rechts Chat/Status/Meldungen,
- keine Landingpage,
- keine dekorativen Karten-Layouts ohne Funktion.

## Relevante Dateien

Frontend:

```text
frontend/app/dashboard/page.tsx
frontend/app/dashboard/components/FleetPanel.tsx
frontend/app/dashboard/components/LeafletMap.tsx
frontend/app/dashboard/components/SecurityPanel.tsx
frontend/app/dashboard/components/ChatInterface.tsx
frontend/app/globals.css
frontend/types/index.ts
frontend/lib/labels.ts
```

Backend/Integration, falls nötig:

```text
backend/routers/commands.py
backend/routers/bins.py
backend/models/bin.py
backend/services/truck_simulator.py
backend/routers/ws.py
```

## Aufgabe 1: Detail-Popups/Karten für Mülltonnen-Pins verbessern

Aktuell sind die Popups beim Klick auf Mülltonnen-Pins sehr basic und schlecht
lesbar. Bitte überarbeite sie zu kompakten, gut lesbaren Detailkarten.

Inhalt pro Mülltonne:

- Name und Adresse
- Füllstand mit Prozent und visuellem Balken
- Akku mit Prozent
- Position/Zustand:
  - Zuhause
  - fährt zur Abholposition
  - an Abholposition
  - fährt nach Hause
  - unbekannt
- Sperrstatus
- aktuelle offene Meldung, falls vorhanden
- Home-/Pickup-Kontext, wenn vorhanden

Bitte beachten:

- Popup muss auf dunkler Karte gut lesbar sein.
- Kein übergroßes Modal.
- Kein Textüberlauf.
- Gute Touch-/Klickflächen.
- Stil an bestehende Leitstand-UI anpassen.

Falls Leaflet-Popups typografisch schwer zu stylen sind, nutze entweder sauber
gestyltes HTML im Popup oder eine eigene ausgewählte Detailkarte neben/über der
Karte. Wichtig ist: Klick auf Pin muss deutlich bessere Detailinformation zeigen.

## Aufgabe 2: FleetPanel interaktiv machen

Wenn im linken FleetPanel eine Tonne angeklickt wird, soll die Karte auf den
entsprechenden Pin zoomen bzw. panen.

Erwartetes Verhalten:

- Klick auf eine Tonne im FleetPanel selektiert diese Tonne.
- Karte zoomt/pannt auf die aktuelle Position der Tonne.
- Der Pin bzw. die Tonne wird visuell hervorgehoben.
- Optional: Popup/Detailkarte der Tonne automatisch öffnen.
- Die Selektion soll auch sichtbar im FleetPanel markiert sein.

Technischer Vorschlag:

- Selection-State in `dashboard/page.tsx` halten, z.B. `selectedBinId`.
- `FleetPanel` bekommt `selectedBinId` und `onSelectBin`.
- `LeafletMap` bekommt `selectedBinId` und steuert Pan/Zoom via `useMap`.
- Keine globale State-Library einführen.

Bitte auch berücksichtigen:

- Wenn Truck-Focus aktiv ist und eine Tonne gewählt wird, sollte Tonnen-Selektion
  priorisieren oder Truck-Focus deaktivieren. Bitte konsistentes UX-Verhalten
  wählen und kurz im Code/Commit-Kontext begründen.

## Aufgabe 3: Clickdummy "Neue Tonne hinzufügen" mit realistischem Pairing-Flow

Es soll eine Clickdummy-Funktion geben, um neue Tonnen hinzuzufügen. Wichtig:
Die WebApp ist kein Consumer-Onboarding, sondern ein Operator-Leitstand. Deshalb
soll der Flow technisch/operativ wirken, nicht wie eine Endkunden-App.

Bitte einen Button integrieren:

```text
Neue Tonne verbinden
```

Geeigneter Ort:

- im FleetPanel-Kopfbereich oder als kompakte Aktion in der Dashboard-Toolbar.

Der Button öffnet ein Menü/Modal/Panel mit einem realistischen Verbindungsprozess.

Vorgeschlagener Operator-Flow:

1. Gerät in Pairing-Modus setzen
   - Hinweistext: Pico/Touchpanel einschalten oder Setup-Modus starten.
   - Kein langer Consumer-Erklärungstext.
2. Gerät suchen
   - simulierte Suche mit Ladezustand.
   - beispielhaft gefundenes Gerät: `SmartBin Pico W`
   - Werte anzeigen: Signal, temporäre Geräte-ID, letzter Kontakt.
3. Gerät zuordnen
   - Name/Standort vergeben, z.B. `Westfalenweg 36`
   - optional Home-/Abholposition später auf Karte setzen.
4. Verbindung bestätigen
   - Zusammenfassung
   - Status: "bereit für Backend-Command-Queue"

Da dies erstmal Clickdummy ist:

- Noch keine echte Persistenz nötig, falls dadurch Scope klein bleibt.
- Optional kann lokal im UI ein temporärer Eintrag simuliert werden.
- Der Flow soll aber so gestaltet sein, dass später echte API-Endpunkte ergänzt
  werden können.

Bitte im Code klar trennen:

- UI-Step-State
- simulierte Device-Daten
- spätere API-Anschlussstellen

Keine komplizierte Wizard-Bibliothek hinzufügen.

## Aufgabe 4: Pico-Integration mitdenken

Bitte keine echte Pico-Firmware schreiben. Aber die WebApp soll so vorbereitet
sein, dass folgende echte Integration sauber möglich ist:

- Pico sendet Touchpanel-Events ans Backend:
  - `damage_report`
  - `hygiene_report`
  - `lock`
  - `unlock`
  - `lid_open`
  - `lid_close`
  - `goto_pickup`
  - `return_home`
  - `eco_mode`
  - `power_off`
- WebApp/Backend sendet Befehle über bestehende Command-Queue:
  - `POST /bins/{bin_id}/command`
  - `GET /bins/{bin_id}/pending-command`
  - `POST /bins/{bin_id}/ack`

Bitte prüfe, ob die UI-Begriffe und Statuslabels dazu passen. Falls Labels
fehlen, ergänze sie in `frontend/lib/labels.ts`.

## Nicht im Scope

Bitte nicht:

- komplettes Redesign der App,
- neue State-Management-Library,
- neue Backend-Architektur,
- echte WLAN-/Pico-Firmware,
- Login/Auth,
- Consumer-Onboarding,
- große Datenbankmigrationen ohne Not,
- Render-/Deployment-Umbau.

## Qualitätsanforderungen

- TypeScript sauber halten.
- Bestehende Komponentenstruktur respektieren.
- Kleine, fokussierte Änderungen.
- Keine unrelated Refactors.
- UI muss auf Desktop und kleineren Viewports nicht überlaufen.
- Popups/Buttons müssen gut lesbar sein.
- Build muss laufen.

Bitte am Ende ausführen:

```bash
cd "Smarte Mülltonne/Software/Flottenmanagement/frontend"
npm run build
```

Falls Backend geändert wird:

```bash
cd "Smarte Mülltonne/Software/Flottenmanagement/backend"
./.venv/bin/python -m compileall main.py routers services models
```

## Erwartetes Ergebnis

Am Ende bitte kurz dokumentieren:

- Welche Dateien geändert wurden.
- Wie die Pin-Detailansicht funktioniert.
- Wie FleetPanel -> Kartenfokus funktioniert.
- Wie der "Neue Tonne verbinden"-Clickdummy aufgebaut ist.
- Welche offenen echten Pico/API-Anschlussstellen bleiben.
