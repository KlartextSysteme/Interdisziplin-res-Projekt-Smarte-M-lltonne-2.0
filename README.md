# Intelligente Entsorgungssysteme: Smarte Mülltonne 2.0

Software-Repository zum Interdisziplinären Projekt (Prüfungsnummer 2220) im Masterstudiengang Digitale Technologien der Fachhochschule Südwestfalen, Sommersemester 2026.

Team: Alaeddine Baghyour, Jan-Lukas Bellenhaus, S. Fulya Bulut, Theresa Pelz, Jonas Wiesner. Hinweis zur Commit-Historie: Die Commits unter dem Konto Klartext-Systeme stammen von Jonas Wiesner und Jan-Lukas Bellenhaus, die über dasselbe Konto gearbeitet haben. Eine Aufteilung der Beiträge nach Personen ist aus der Historie deshalb nicht ablesbar.

## Was das System tut

Die Smarte Mülltonne fährt selbstständig entlang einer Bodenlinie von ihrem Stellplatz zur Straße und zurück. Ein Raspberry Pi Pico W steuert dabei zwei Schrittmotoren, liest fünf Liniensensoren und mehrere Ultraschallsensoren über einen Multiplexer und misst Füllstand und Akkuspannung. Ein Touchdisplay an der Tonne zeigt Zustand und Diagnosewerte und nimmt lokale Befehle entgegen. Über WLAN meldet sich der Pico bei einer TCP-Bridge auf einem Laptop, die seine Telemetrie an das Backend weiterreicht und Fahrbefehle aus der Kommando-Warteschlange an den Pico zurückgibt. Das Backend (FastAPI, SQLite) verwaltet Tonnen, Füllstände, Sicherheitsereignisse und Routen und bindet einen LLM-Agenten für die Routenplanung an. Die Web-App (Next.js) ist der Leitstand: Flottenliste, Live-Karte, Chat mit dem Agenten, Energie- und Sicherheitspanel sowie Sperren und Steuern einzelner Tonnen.

## Ordnerstruktur

Der gesamte Projektinhalt liegt unter `Smarte Mülltonne/`. Alle Pfade unten sind relativ dazu. Für die Abgabe wurden zwei Ordner umbenannt, `smart-bin` heißt jetzt `Flottenmanagement` und `Test_2` heißt `Hardwaretests`; die Dokumentation verwendet die neuen Namen, siehe Abschnitt „Codeverweise in der Dokumentation". Die Semesterdokumentation und die Abschlusspräsentation sind nicht Teil dieses Repos; sie liegen im Abgabeordner. Der Vorgängerstand (Smarte Mülltonne 1.0, Ordner `Alt/`) und ein früherer Doku-Arbeitsstand wurden für die Abgabe entfernt und sind in der Git-Historie bis Commit `dae74ec9` erhalten.

| Pfad | Inhalt |
|---|---|
| `Software/Quellcode/Client/` | MicroPython-Firmware des Pico W in der Tonne: Fahrlogik, Sensorik, Touchpanel-Oberfläche, TCP-Client zur Bridge. `main.py` startet den Controller. |
| `Software/Quellcode/Client/assets/` | Vorgerenderte Bild-Assets für das Touchdisplay (WF1/RLE-Format). |
| `Software/Quellcode/Server/` | Früher TCP-Server für die Missionssteuerung auf dem Laptop; im Zielsystem übernimmt die Bridge unter `Flottenmanagement/bridge/` diese Rolle. |
| `Software/Flottenmanagement/backend/` | FastAPI-Backend mit Datenmodell, Routern, Agent und Truck-Simulator. |
| `Software/Flottenmanagement/frontend/` | Next.js-Web-App (Leitstand und Admin-Seite). |
| `Software/Flottenmanagement/bridge/` | TCP-Bridge zwischen Pico und Backend sowie ein Pico-Simulator. |
| `Software/Flottenmanagement/simulator/` | Skripte, die Füllstände, Energie, Sicherheitsereignisse und LKW-Fahrt simulieren. |
| `Software/Flottenmanagement/firmware/pico_touchpanel/` | Eigenständige Touchpanel-Firmware mit Kalibrierung, Asset-Werkzeugen und datierten Backups der Display-Stände. |
| `Software/Flottenmanagement/docs/` | Architektur, API-Vertrag, CI-Vorgaben, Handoffs, Design-Specs und Pläne aus der Entwicklung. |
| `Software/Hardwaretests/` | Einzelne Hardware-Testskripte (Motoren, Sensoren, Multiplexer, Display) aus der Inbetriebnahme. |
| `Software/Visualisierungen/` | Architektur- und Zustandsdiagramme, Pinout, Schaltpläne. |
| `Software/Übergabedokument_Smarte_Muelltonne.pdf` | Technisches Übergabedokument zum Client-Server-Quellcode des Pico (Stand April 2026). |

An der Wurzel liegen außerdem `render.yaml` (Deployment-Blueprint für Backend und Web-App auf Render) und `.gitignore`.

## Stand der Dokumentation

Die Semesterdokumentation bezieht sich auf den Branch `route-start-live-akku` im Stand des Commits `c10b40b` vom 11.07.2026. Dieser Commit ist in `main` enthalten. In diesem Stand heißen die Ordner noch `smart-bin` und `Test_2`, und die Ordner `Alt/` sowie `Dokumentation & Präsentation Neu/` sind noch vorhanden. Um genau diesen Stand zu sehen:

```
git checkout c10b40b
```

Zurück zum aktuellen Stand mit `git checkout main`.

## Codeverweise in der Dokumentation

Die Dokumentation zitiert Pfade relativ zu `Smarte Mülltonne/Software/` im Stand `c10b40b`. Nach der Umbenennung für die Abgabe gilt auf `main` die rechte Spalte. Dateien ohne Eintrag in der rechten Spalte haben sich nicht bewegt.

| Pfad in der Dokumentation (Stand `c10b40b`) | Pfad auf `main` |
|---|---|
| `Quellcode/Client/main.py` | unverändert |
| `Quellcode/Client/ui.py` | unverändert |
| `Quellcode/Client/ultraschallsensor.py` | unverändert |
| `Quellcode/Client/global_controller_test.py` | unverändert |
| `Quellcode/Client/multiplexer.py` | unverändert |
| `Quellcode/Client/display.py` | unverändert |
| `Quellcode/Client/touchpanel.py` | unverändert |
| `Quellcode/Client/wireframe.py` | unverändert |
| `Quellcode/Client/assets/` | unverändert |
| `smart-bin/backend/config.py` | `Flottenmanagement/backend/config.py` |
| `smart-bin/backend/agent/planner.py` | `Flottenmanagement/backend/agent/planner.py` |
| `smart-bin/backend/agent/tools.py` | `Flottenmanagement/backend/agent/tools.py` |
| `smart-bin/backend/routers/admin_demo.py` | `Flottenmanagement/backend/routers/admin_demo.py` |
| `smart-bin/backend/routers/bins.py` | `Flottenmanagement/backend/routers/bins.py` |
| `smart-bin/backend/routers/commands.py` | `Flottenmanagement/backend/routers/commands.py` |
| `smart-bin/backend/routers/routes.py` | `Flottenmanagement/backend/routers/routes.py` |
| `smart-bin/backend/routers/ws.py` | `Flottenmanagement/backend/routers/ws.py` |
| `smart-bin/frontend/app/admin/page.tsx` | `Flottenmanagement/frontend/app/admin/page.tsx` |
| `smart-bin/frontend/app/dashboard/components/OperatorTour.tsx` | `Flottenmanagement/frontend/app/dashboard/components/OperatorTour.tsx` |
| `smart-bin/firmware/pico_touchpanel/touch_calibrate.py` | `Flottenmanagement/firmware/pico_touchpanel/touch_calibrate.py` |
| `smart-bin/firmware/pico_touchpanel/tools/png_to_wf1.py` | `Flottenmanagement/firmware/pico_touchpanel/tools/png_to_wf1.py` |
| `smart-bin/firmware/pico_touchpanel/backups/2026-06-11_light_mode_before_icon_shape_fix/` | `Flottenmanagement/firmware/pico_touchpanel/backups/2026-06-11_light_mode_before_icon_shape_fix/` |
| `smart-bin/docs/api_contract.md` | `Flottenmanagement/docs/api_contract.md` |
| `smart-bin/docs/ci_farben_typografie.md` | `Flottenmanagement/docs/ci_farben_typografie.md` |
| `smart-bin/docs/handoff_fahrlogik_2026-06-27.md` | `Flottenmanagement/docs/handoff_fahrlogik_2026-06-27.md` |
| `smart-bin/docs/touchpanel_tonnenicon_design_notes.md` | `Flottenmanagement/docs/touchpanel_tonnenicon_design_notes.md` |
| `smart-bin/docs/superpowers/plans/2026-07-04-hardware-test-followup.md` | `Flottenmanagement/docs/superpowers/plans/2026-07-04-hardware-test-followup.md` |
| `smart-bin/docs/superpowers/specs/2026-07-04-hardware-test-followup-design.md` | `Flottenmanagement/docs/superpowers/specs/2026-07-04-hardware-test-followup-design.md` |

Die gestalterischen Vorgaben für die Web-App (Farben, Ampelfarben, Schrift, Layout) stehen in `Flottenmanagement/docs/ci_farben_typografie.md`. Die Design-Spezifikationen der Agenten-Aufträge folgen dem Namensschema `<thema>-design.md` in `Flottenmanagement/docs/`.

## Starten

Backend (Python 3.12, aus `Smarte Mülltonne/Software/Flottenmanagement/backend/`):

```
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8000
```

In `.env` werden Admin-Token, `GROQ_API_KEY` für den Agenten, erlaubte CORS-Origins und die Depot-Koordinaten gesetzt. Die Datenbank `smart_bin.db` wird beim ersten Start angelegt.

Web-App (Node 22, aus `Smarte Mülltonne/Software/Flottenmanagement/frontend/`):

```
npm ci
npm run dev
```

Die App läuft dann auf Port 3000 und erwartet das Backend unter `NEXT_PUBLIC_API_URL` (Standard im Deployment: `http://localhost:8000`) und den Live-Kanal unter `NEXT_PUBLIC_WS_URL` (`ws://localhost:8000/ws/live`). `npm run build` erzeugt den statischen Export nach `out/`.

Bridge zur Tonne (aus `Smarte Mülltonne/Software/Flottenmanagement/`):

```
python bridge/tcp_bridge.py --bin-id 1 --backend http://localhost:8000
```

Der Pico verbindet sich mit `BRIDGE_HOST` und `BRIDGE_PORT` (50002) aus `Quellcode/Client/config.py`. Ohne Hardware lässt sich der Pico mit `bridge/pico_tcp_simulator.py` nachstellen; die Skripte in `simulator/` erzeugen Füllstands-, Energie- und Sicherheitsdaten gegen das laufende Backend.

Pico-Firmware: Die Dateien aus `Quellcode/Client/` einschließlich `assets/` auf den Pico W kopieren; `main.py` startet beim Booten den Controller. WLAN-Zugang und Bridge-Adresse stehen in `config.py`.
