# Intelligente Entsorgungssysteme: Smarte Mülltonne 2.0

Software-Repository zum Interdisziplinären Projekt (Prüfungsnummer 2220) im Masterstudiengang Digitale Technologien der Fachhochschule Südwestfalen, Sommersemester 2026.

Team: Alaeddine Baghyour, Jan-Lukas Bellenhaus, S. Fulya Bulut, Theresa Pelz, Jonas Wiesner.

## Was das System tut

Die Smarte Mülltonne fährt selbstständig entlang einer Bodenlinie von ihrem Stellplatz zur Straße und zurück. Ein Raspberry Pi Pico W steuert dabei zwei Schrittmotoren, liest fünf Liniensensoren und mehrere Ultraschallsensoren über einen Multiplexer und misst Füllstand und Akkuspannung. Ein Touchdisplay an der Tonne zeigt Zustand und Diagnosewerte und nimmt lokale Befehle entgegen. Über WLAN meldet sich der Pico bei einer TCP-Bridge auf einem Laptop, die seine Telemetrie an das Backend weiterreicht und Fahrbefehle aus der Kommando-Warteschlange an den Pico zurückgibt. Das Backend (FastAPI, SQLite) verwaltet Tonnen, Füllstände, Sicherheitsereignisse und Routen und bindet einen LLM-Agenten für die Routenplanung an. Die Web-App (Next.js) ist der Leitstand: Flottenliste, Live-Karte, Chat mit dem Agenten, Energie- und Sicherheitspanel sowie Sperren und Steuern einzelner Tonnen.

## Ordnerstruktur

Der gesamte Projektinhalt liegt unter `Smarte Mülltonne/`. Alle Pfade unten sind relativ dazu.

| Pfad | Inhalt |
|---|---|
| `Software/Quellcode/Client/` | MicroPython-Firmware des Pico W in der Tonne: Fahrlogik, Sensorik, Touchpanel-Oberfläche, TCP-Client zur Bridge. `main.py` startet den Controller. |
| `Software/Quellcode/Client/assets/` | Vorgerenderte Bild-Assets für das Touchdisplay (WF1/RLE-Format). |
| `Software/Quellcode/Server/` | Früher TCP-Server für die Missionssteuerung auf dem Laptop; im Zielsystem übernimmt die Bridge unter `smart-bin/bridge/` diese Rolle. |
| `Software/smart-bin/backend/` | FastAPI-Backend mit Datenmodell, Routern, Agent und Truck-Simulator. |
| `Software/smart-bin/frontend/` | Next.js-Web-App (Leitstand und Admin-Seite). |
| `Software/smart-bin/bridge/` | TCP-Bridge zwischen Pico und Backend sowie ein Pico-Simulator. |
| `Software/smart-bin/simulator/` | Skripte, die Füllstände, Energie, Sicherheitsereignisse und LKW-Fahrt simulieren. |
| `Software/smart-bin/firmware/pico_touchpanel/` | Eigenständige Touchpanel-Firmware mit Kalibrierung, Asset-Werkzeugen und datierten Backups der Display-Stände. |
| `Software/smart-bin/docs/` | Architektur, API-Vertrag, CI-Vorgaben, Handoffs, Design-Specs und Pläne aus der Entwicklung. |
| `Software/Test_2/` | Einzelne Hardware-Testskripte (Motoren, Sensoren, Multiplexer, Display) aus der Inbetriebnahme. |
| `Software/Visualisierungen/` | Architektur- und Zustandsdiagramme, Pinout, Schaltpläne. |
| `Software/Übergabedokument_Smarte_Muelltonne.pdf` | Technisches Übergabedokument zum Client-Server-Quellcode des Pico (Stand April 2026). |
| `Dokumentation & Präsentation Neu/` | Arbeitsstand von Projektantrag, Dokumentation und Bildmaterial im Repo. Die Abgabefassung der Dokumentation liegt im Abgabeordner, nicht hier. |
| `Alt/` | Vorgängerstand (Smarte Mülltonne 1.0): STL-Dateien, Teileliste, Schaltplan, alter Client- und Servercode, alte Dokumentation. |
| `Briefing_Fulya_Wireframes.md` | Briefing für die Wireframes von Web-App und Touchpanel. |

An der Wurzel liegen außerdem `render.yaml` (Deployment-Blueprint für Backend und Web-App auf Render) und `.gitignore`.

## Stand der Dokumentation

Die Semesterdokumentation bezieht sich auf den Branch `route-start-live-akku` im Stand des Commits `c10b40b` vom 11.07.2026. Dieser Commit ist in `main` enthalten. Um genau diesen Stand zu sehen:

```
git checkout c10b40b
```

Zurück zum aktuellen Stand mit `git checkout main`.

## Codeverweise in der Dokumentation

Die Dokumentation zitiert die folgenden Pfade, alle relativ zu `Smarte Mülltonne/Software/`. Sie existieren bei `c10b40b` und unverändert auf `main`.

Firmware und Client:

```
Quellcode/Client/main.py
Quellcode/Client/ui.py
Quellcode/Client/ultraschallsensor.py
Quellcode/Client/global_controller_test.py
Quellcode/Client/multiplexer.py
Quellcode/Client/display.py
Quellcode/Client/touchpanel.py
Quellcode/Client/wireframe.py
Quellcode/Client/assets/
```

Backend, Frontend und Touchpanel-Firmware:

```
smart-bin/backend/config.py
smart-bin/backend/agent/planner.py
smart-bin/backend/agent/tools.py
smart-bin/backend/routers/admin_demo.py
smart-bin/backend/routers/bins.py
smart-bin/backend/routers/commands.py
smart-bin/backend/routers/routes.py
smart-bin/backend/routers/ws.py
smart-bin/frontend/app/admin/page.tsx
smart-bin/frontend/app/dashboard/components/OperatorTour.tsx
smart-bin/firmware/pico_touchpanel/touch_calibrate.py
smart-bin/firmware/pico_touchpanel/tools/png_to_wf1.py
smart-bin/firmware/pico_touchpanel/backups/2026-06-11_light_mode_before_icon_shape_fix/
```

Dokumente:

```
smart-bin/docs/api_contract.md
smart-bin/docs/ci_farben_typografie.md
smart-bin/docs/handoff_fahrlogik_2026-06-27.md
smart-bin/docs/touchpanel_tonnenicon_design_notes.md
smart-bin/docs/superpowers/plans/2026-07-04-hardware-test-followup.md
smart-bin/docs/superpowers/specs/2026-07-04-hardware-test-followup-design.md
```

Die gestalterischen Vorgaben für die Web-App (Farben, Ampelfarben, Schrift, Layout) stehen in `smart-bin/docs/ci_farben_typografie.md`. Die Design-Spezifikationen der Agenten-Aufträge folgen dem Namensschema `<thema>-design.md` in `smart-bin/docs/`.

## Starten

Backend (Python 3.12, aus `Smarte Mülltonne/Software/smart-bin/backend/`):

```
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8000
```

In `.env` werden Admin-Token, `GROQ_API_KEY` für den Agenten, erlaubte CORS-Origins und die Depot-Koordinaten gesetzt. Die Datenbank `smart_bin.db` wird beim ersten Start angelegt.

Web-App (Node 22, aus `Smarte Mülltonne/Software/smart-bin/frontend/`):

```
npm ci
npm run dev
```

Die App läuft dann auf Port 3000 und erwartet das Backend unter `NEXT_PUBLIC_API_URL` (Standard im Deployment: `http://localhost:8000`) und den Live-Kanal unter `NEXT_PUBLIC_WS_URL` (`ws://localhost:8000/ws/live`). `npm run build` erzeugt den statischen Export nach `out/`.

Bridge zur Tonne (aus `Smarte Mülltonne/Software/smart-bin/`):

```
python bridge/tcp_bridge.py --bin-id 1 --backend http://localhost:8000
```

Der Pico verbindet sich mit `BRIDGE_HOST` und `BRIDGE_PORT` (50002) aus `Quellcode/Client/config.py`. Ohne Hardware lässt sich der Pico mit `bridge/pico_tcp_simulator.py` nachstellen; die Skripte in `simulator/` erzeugen Füllstands-, Energie- und Sicherheitsdaten gegen das laufende Backend.

Pico-Firmware: Die Dateien aus `Quellcode/Client/` einschließlich `assets/` auf den Pico W kopieren; `main.py` startet beim Booten den Controller. WLAN-Zugang und Bridge-Adresse stehen in `config.py`.
