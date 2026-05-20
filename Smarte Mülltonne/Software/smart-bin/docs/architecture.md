# Smarte Mülltonne 2.0 — Architektur-Dokumentation

> **Projekt:** FH SWF Digitale Technologien, interdisziplinär
> **Software-Lead:** Jonas Wiesner (Backend, LLM-Agent, Dashboard)
> **Hardware-Lead:** Mech-Team (Antrieb, Sensorik, Tonne-Bau)
> **Stand:** Mai 2026
> **Scope:** Software-Komponenten unter `smart-bin/` — Backend, Frontend, Simulatoren, Agent, Pico-W-Touchpanel-Konzept

---

## 1. System-Überblick

Die Smarte Mülltonne 2.0 ist ein Hardware-/Software-Verbundsystem aus autonomen Mülltonnen, einem Sammelfahrzeug und einer zentralen Flottenmanagement-Plattform. Diese Doku beschreibt ausschließlich die **Software-Schicht**. Die Mechanik (Antrieb, Fahrwerk, Sensor-Integration) wird parallel vom Mech-Team gebaut und ist hier nur als API-Schnittstelle relevant.

### 1.1 Komponenten-Diagramm

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Smarte Mülltonne 2.0                            │
│                                                                          │
│  ┌─────────────────┐    HTTP / SSE    ┌──────────────────────────────┐  │
│  │   Frontend      │ ←─────────────→  │  Backend (FastAPI)           │  │
│  │   (Next.js 15)  │   WebSocket      │                              │  │
│  │                 │ ←─────────────→  │  ┌─────────┐  ┌──────────┐   │  │
│  │  • Dashboard    │                  │  │ SQLite  │  │ Routing  │   │  │
│  │  • Map (Leaflet)│                  │  │  (DB)   │  │ (OSRM)   │   │  │
│  │  • Chat (SSE)   │                  │  └─────────┘  └──────────┘   │  │
│  │  • Sim-Controls │                  │                              │  │
│  └─────────────────┘                  │  ┌──────────────────────┐    │  │
│                                       │  │ LangChain Agent      │    │  │
│                                       │  │  ↳ Groq Llama 3.3    │    │  │
│                                       │  └──────────────────────┘    │  │
│                                       └────────┬─────────────────────┘  │
│                                                │                        │
│                            HTTP polling (2s)   │                        │
│                  ┌─────────────────────────────┼──────────────────────┐ │
│                  ▼                             ▼                      ▼ │
│         ┌────────────────┐         ┌────────────────┐      ┌──────────┐ │
│         │  mock_truck    │         │  mock_bins     │      │ Pico W   │ │
│         │  (Python sim)  │         │  (Python sim)  │      │ Tonne(n) │ │
│         │                │         │                │      │ (geplant)│ │
│         └────────────────┘         └────────────────┘      └──────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Tech-Stack

| Schicht | Technologie | Begründung |
|---|---|---|
| Frontend | Next.js 15 (App Router) + React 19 + TypeScript + Tailwind v4 | SSR-fähig, moderne Hooks, kleines Setup für Single-Page-Dashboard |
| Karten | Leaflet + react-leaflet 5 + OpenStreetMap-Tiles | Kein API-Key, freie Karten |
| Backend | FastAPI + Pydantic + SQLAlchemy 2.0 | Async-first, OpenAPI auto-doc, gute DX |
| Datenbank | SQLite | Single-Node-Demo, kein Server, später durch Postgres tauschbar (URL-Tausch) |
| Routing | OSRM Public Demo + python-tsp | Echte Straßen-Routen, Open-Source-TSP-Heuristiken |
| Agent | LangChain 1.x + LangGraph + Groq (Llama 3.3 70B) | Tool-Calling, Free-Tier ausreichend für Demo |
| Realtime | FastAPI WebSocket (Live-Daten) + SSE (Chat-Stream) | Bidirektional für Telemetrie, unidirektional für Token-Streaming |
| Tonne-Hardware | Raspberry Pi Pico W + ILI9341 + XPT2046 | MicroPython, WLAN nativ, günstig, ausreichende Performance für UI |

---

## 2. Repo-Struktur

```
smart-bin/
├── backend/
│   ├── main.py                  # FastAPI-Entry, Router-Registrierung, CORS
│   ├── config.py                # Pydantic-Settings (.env-Loader)
│   ├── database.py              # SQLAlchemy-Engine + Seed-Daten (35 Tonnen)
│   ├── models/
│   │   ├── bin.py               # Bin-ORM
│   │   ├── route.py             # Route-ORM (waypoints, geometry, distances)
│   │   ├── event.py             # SecurityEvent-ORM
│   │   └── command.py           # Command-Queue für Hardware
│   ├── routers/
│   │   ├── bins.py              # GET /bins, POST /bins/{id}/update
│   │   ├── routes.py            # POST /routes/plan (NN + 2-opt + Held-Karp)
│   │   ├── security.py          # Events, lock/unlock
│   │   ├── energy.py            # Akku- und Solar-Status
│   │   ├── truck.py             # Truck-Position + -Command-Endpoints
│   │   ├── commands.py          # Pull-Queue für Hardware (Pico W)
│   │   ├── agent.py             # POST /agent/chat (SSE)
│   │   ├── sim.py               # GET/PUT /sim/speed (Speed + Pause)
│   │   └── ws.py                # WebSocket /ws/live
│   ├── services/
│   │   └── routing.py           # OSRM-Client (echte Straßen-Geometrie)
│   ├── agent/
│   │   ├── planner.py           # ChatGroq + create_agent (LangGraph)
│   │   ├── prompts.py           # System-Prompt für den Disponenten-Agent
│   │   └── tools.py             # Tool-Definitionen (9 Tools)
│   └── scripts/
│       ├── geocode_bins.py      # Nominatim-Batch-Geocoder
│       └── tsp_benchmark.py     # NN vs 2-opt vs Held-Karp
│
├── frontend/
│   ├── app/dashboard/
│   │   ├── page.tsx             # Hauptseite: Header + 3-Spalten-Layout
│   │   └── components/
│   │       ├── LeafletMap.tsx   # Karte mit AnimatedTruckMarker
│   │       ├── FleetPanel.tsx   # Linke Spalte: Tonnen-Liste
│   │       ├── ChatInterface.tsx# Rechte Spalte: SSE-Stream + Tool-Cards
│   │       ├── EnergyPanel.tsx
│   │       ├── SecurityPanel.tsx
│   │       └── AlertBanner.tsx
│   ├── lib/
│   │   ├── api.ts               # REST-Wrapper + streamChat (SSE)
│   │   └── useWebSocket.ts      # Live-Data-Hook
│   └── types/index.ts           # Bin, Route, ChatMessage, ToolCall, ...
│
├── simulator/
│   ├── mock_truck.py            # Fahrt entlang OSRM-Geometrie
│   ├── mock_bins.py             # Füllstand-Drift
│   ├── mock_energy.py           # Solar/Akku-Simulation
│   └── mock_security.py         # Sicherheitsereignisse
│
└── docs/
    ├── architecture.md          # ← dieses Dokument
    └── api_contract.md          # API-Vertrag für Pico-W-Firmware
```

---

## 3. Datenmodell

### 3.1 Bin (Mülltonne)

| Feld | Typ | Beschreibung |
|---|---|---|
| `id` | int (PK) | Eindeutige ID |
| `name` | str | Anzeigename („Westfalenweg 3") |
| `address` | str | Vollständige Adresse |
| `lat` / `lng` | float | Koordinaten (Nominatim geocodiert) |
| `fill_level` | int (0–100) | Aktueller Füllstand in Prozent |
| `battery` | int (0–100) | Akkustand |
| `solar_output_w` | float | Solar-Leistung in Watt |
| `is_charging` | bool | Lädt aktuell? |
| `status` | str | `idle` / `in_use` / `emptied` |
| `locked` | bool | Aus Sicherheits-/Wartungsgründen gesperrt |
| `last_seen` | datetime | Letzter Status-Update |

### 3.2 Route

| Feld | Typ | Beschreibung |
|---|---|---|
| `id` | int (PK) | Eindeutige ID |
| `created_at` | datetime | Plan-Zeitpunkt |
| `waypoints` | list[int] | Bin-IDs in der finalen 2-opt-Reihenfolge |
| `distance_m` | int | OSRM-Strecke (echte Straßen) |
| `duration_s` | int? | OSRM-Fahrzeit |
| `geometry` | dict | GeoJSON LineString der Tour |
| `nn_distance_m` | int? | NN-Baseline (planar, für A/B) |
| `optimized_distance_m` | int? | 2-opt-Distanz (planar) |
| `exact_distance_m` | int? | Held-Karp-Optimum (planar, nur n ≤ 15) |
| `completed` | bool | Tour abgeschlossen? |
| `llm_reasoning` | str? | Optional: Agent-Begründung |

### 3.3 SecurityEvent

| Feld | Typ | Beschreibung |
|---|---|---|
| `id`, `bin_id`, `created_at` | – | Standard |
| `event_type` | str | `tamper`, `vandalism`, `user_report`, `fire`, ... |
| `reason` | str? | Freitext-Beschreibung |
| `resolved` | bool | Quittiert? |

### 3.4 Command (Hardware-Queue)

| Feld | Typ | Beschreibung |
|---|---|---|
| `id`, `bin_id`, `created_at` | – | Standard |
| `action` | str | `lock`, `unlock`, `open_lid`, `beep` |
| `payload` | dict? | Optionale Parameter |
| `acked` | bool | Von der Hardware bestätigt? |

**Sync-Pattern:** Hardware pollt `GET /bins/{id}/pending-command` alle 2 s, führt aus, sendet `POST /bins/{id}/ack`.

---

## 4. API-Endpoints

| Methode | Pfad | Zweck |
|---|---|---|
| GET | `/health` | Healthcheck |
| GET | `/config/public` | Depot-Koordinaten, App-Konstanten |
| GET | `/bins` | Alle Tonnen |
| POST | `/bins/{id}/update` | Sensor-Update (fill, battery, status) |
| POST | `/bins/{id}/command` | Befehl in Hardware-Queue legen |
| GET | `/bins/{id}/pending-command` | Pull-Endpoint für Pico |
| POST | `/bins/{id}/ack` | Command-Ack vom Pico |
| POST | `/routes/plan` | Route planen (NN + 2-opt + Held-Karp ≤ 15) |
| GET | `/routes/latest` | Neueste Route |
| POST | `/routes/{id}/complete` | Tour abschließen |
| GET | `/truck/status` | Truck-Position + Action |
| POST | `/truck/position` | Position vom Simulator |
| POST | `/truck/command` | Truck steuern (`start`/`pause`/`stop`) |
| GET | `/security/events` | Offene Sicherheitsmeldungen |
| POST | `/security/events` | Neues Event anlegen |
| POST | `/security/{id}/lock` | Tonne sperren (Admin-Token) |
| POST | `/security/{id}/unlock` | Tonne entsperren |
| GET | `/energy` | Akku- und Solar-Status aller Tonnen |
| GET | `/sim/speed` | Sim-Speed + Pause-State |
| PUT | `/sim/speed` | Sim-Speed setzen / Pause toggeln |
| POST | `/agent/chat` | SSE-Chat-Stream |
| WS | `/ws/live` | Bins + Truck + Alerts alle 2 s |

---

## 5. Architektur-Entscheidungen (ADRs)

Die wichtigsten Entscheidungen im Entwicklungsprozess — mit Begründung für künftige Maintainer.

### ADR-1 — SQLite statt Supabase/PostgreSQL

**Kontext:** Demo mit 35 Tonnen, Single-Node, kein Multi-User.
**Entscheidung:** SQLite via SQLAlchemy.
**Begründung:** Setup-Zeit ~ 0 s, keine externen Dependencies, file-based. Migration zu PostgreSQL ist später ein URL-Tausch. Supabase wäre nur sinnvoll bei Multi-User-Auth, Production-Deployment oder Echtzeit-Replikation — nichts davon im Scope.

### ADR-2 — Statische Bin-Adressen statt GPS

**Kontext:** Mülltonnen sind ortsfest.
**Entscheidung:** Koordinaten einmalig via Nominatim geocodiert, in DB gespeichert.
**Begründung:** Spart GPS-Modul auf der Hardware, vereinfacht Pico-Firmware, Standorte sind bekannt. Konsequenz: Hardware sendet nur Status (Füllstand, Akku, Sicherheit), keine Position.

### ADR-3 — Pull-basierte Command-Queue für Hardware

**Kontext:** Pico W ist Microcontroller — kann nicht als Server angesprochen werden.
**Entscheidung:** Pico pollt alle 2 s `GET /bins/{id}/pending-command`. Backend ist nie der Initiator.
**Begründung:**
- Funktioniert ohne öffentliche IP/Port-Forwarding auf der Tonne
- Einfach zu debuggen
- Tolerant gegenüber kurzen Netzausfällen
- Latenz ≤ 2 s ist für Sperren völlig ausreichend

### ADR-4 — OSRM Public Demo statt Self-Hosting

**Kontext:** Brauchen Straßen-Routing.
**Entscheidung:** `https://router.project-osrm.org` als Free-Service.
**Begründung:** Keine Auth, kein Hosting-Aufwand. Fallback auf Haversine ist eingebaut, falls OSRM nicht erreichbar. Für Production müsste eigenes OSRM aufgesetzt werden.

### ADR-5 — LLM als Dispatch-Interface, NICHT als Entscheider

**Kontext:** Hellweg-Feedback (April 2026): „Akku-Reaktionen und Routenplanung lassen sich ohne LLM lösen — wozu der Aufwand?"

**Entscheidung:** Das LLM trifft **keine algorithmischen Entscheidungen**. Routing, Schwellwerte, Lock-Regeln sind deterministischer Python-Code. Das LLM übersetzt nur Natursprache in Tool-Calls.

```
User: "Sperre Tonne 3 wegen Vandalismus"
  → LLM ruft: lock_bin(bin_id=3, reason="Vandalismus")
  → Python-Code in routers/security.py legt Command in Queue
  → Pico W pollt, führt Motor-Befehl aus
```

**Vorteile:**
- Volle Kontrolle über Entscheidungslogik (auditierbar)
- Keine Halluzinationen bei Zahlen (Tools liefern reale DB-Daten)
- LLM-Ausfall macht Dashboard nicht unbenutzbar (Frontend hat eigene Buttons)
- Chat ist additiv — kein kritischer Pfad

### ADR-6 — Groq + Llama 3.3 70B statt Anthropic Claude

**Kontext:** Anthropic-Account ohne Guthaben.
**Entscheidung:** Groq Free-Tier mit Llama 3.3 70B (Tool-Calling-fähig).
**Begründung:** 0 € Kosten, schnelle Inferenz (Groq LPU ~ 500 tok/s), `langchain-groq` als Drop-in, Tool-Calling-Qualität ausreichend. Wechsel zu Anthropic später ist 3 Code-Zeilen.

### ADR-7 — 2-opt seeded mit Nearest-Neighbour

**Kontext:** Initial nur NN-Sortierung nach Füllstand → 32 km Route bei 13 Tonnen.
**Trigger:** Hellweg-Feedback: „k-opt findet bessere Lösungen, NN hat pathologische Fälle."

**Entscheidung:** `python-tsp` als Dependency, 2-opt local search seeded mit NN-Lösung. Für n ≤ 15 zusätzlich Held-Karp-DP als Optimum-Referenz.

**Begründung:** 2-opt garantiert ≤ NN-Distanz, läuft in < 1 s bei n=18. Held-Karp dient nur als Verifikation und ist bei n > 15 zu langsam für interaktive Nutzung.

**Messung (35-Tonnen-Demo):**
- NN-Baseline: 9,11 km (planar)
- 2-opt: 8,19 km (planar, −10,1 %)
- OSRM real-street: 16,8 km → 15,2 km nach Optimierung

### ADR-8 — Füllstand-Threshold (60 %)

**Kontext:** Bei 35 Tonnen wäre eine „alle abfahren"-Route unsinnig lang.
**Entscheidung:** Nur Tonnen mit `fill_level >= 60 %` und `locked == False` werden in der Tour geplant.
**Begründung:** Entspricht der Agent-Regel „Tonnen < 30 % lohnen sich selten", spart Strecke, Schwelle ist Konstante in `routes.py`.

### ADR-9 — SSE für Chat-Streaming statt WebSocket

**Kontext:** Token-by-Token-Streaming vom Agent.
**Entscheidung:** Server-Sent Events.
**Begründung:** Chat ist unidirektional, SSE läuft über normales HTTP ohne Upgrade-Handshake, LangChain liefert via `astream_events()`. WebSocket bleibt für bidirektionalen Live-Feed (Bins + Truck + Alerts).

### ADR-10 — Frontend-Marker-Smoothing via requestAnimationFrame

**Kontext:** Truck-Position kommt alle 1–2 s vom WebSocket — Marker „springt".
**Entscheidung:** `AnimatedTruckMarker` interpoliert per RAF zwischen alter und neuer Position über 1,5 s.
**Begründung:** Vermeidet Teleport-Effekt. Logik bleibt im Frontend, keine Server-Last.

### ADR-11 — Sim-Speed-Cap auf 20×

**Kontext:** Initial wollten wir 50×. Bei 20× brachen Bin-Refill und Truck-Pickup zusammen.
**Entscheidung:** Maximum 20×, Bin-Refill-Increment sublinear gedeckelt (`min(speed, 5)`).
**Begründung:**
- 50× hätte Tonnen so schnell befüllt, wie der Truck sie leeren konnte
- Truck-Proximity-Check musste **innerhalb** der `advance()`-Schleife passieren, sonst überspringt der Truck Tonnen
- Sublineare Skalierung hält das System auch unter Last leerbar

### ADR-12 — Tonnen-Display ist separate Anwender-Schnittstelle

**Kontext:** Frage: „soll das Display dasselbe sein wie das Dashboard?"
**Entscheidung:** Nein. Display am Pico W ist für **Anwohner und Wartung**, nicht für den Fleet-Operator.
**Begründung:** Drei verschiedene Zielgruppen, drei verschiedene UX-Paradigmen:
- Dashboard → Stefan Krüger (Fahrer/Disponent), 3-Spalten-Layout, viele Daten
- Touch-Display → Anwohner, 5 Screens, 320 × 240, Handschuh-tauglich
- Touch-Display (Wartung) → Service-Techniker, PIN-geschützt, Diagnose-Daten

Backend-API ist für beide identisch — Endpoints werden geteilt.

### ADR-13 — Pico W (RP2040) statt Raspberry Pi 4

**Kontext:** Mech-Team setzt auf Pico W.
**Entscheidung:** Firmware in MicroPython, kein Linux-Stack.
**Begründung:**
- Pico W ~ 7 €, Pi 4 ~ 50 € — bei vielen Tonnen relevant
- Keine OS-Updates, keine Boot-Zeiten, sofort betriebsbereit
- 264 KB RAM reicht für UI + HTTP-Polling
- WLAN nativ über CYW43439
- Konsequenz: Firmware ist **eine MicroPython-Mainloop** (Sensoren, Commands, UI in einem Prozess), nicht mehrere systemd-Services

---

## 6. Schlüssel-Algorithmen

### 6.1 Tour-Planung (`backend/routers/routes.py`)

```
Input:  Tonnen mit fill_level ≥ 60 %, nicht gesperrt
Output: Geordnete Bin-IDs + OSRM-Geometrie + Distanz-Metriken

  1. Filtere Tonnen nach Threshold und lock-Status
  2. Baue (n+1)×(n+1) planare Distanzmatrix (Depot = Knoten 0)
  3. Nearest-Neighbour als Baseline       → nn_distance (Persistenz für A/B)
  4. 2-opt local search seeded mit NN     → opt_distance, opt_perm
  5. Wenn n ≤ 15: Held-Karp-DP            → exact_distance (Optimum-Referenz)
  6. OSRM-Call mit opt_perm               → reale Straßen-Geometrie
  7. Persistiere Route mit allen drei Distanz-Metriken
```

**Performance bei n=18:** ~ 230 ms gesamt (davon OSRM ~ 150 ms, 2-opt < 100 ms).

### 6.2 Truck-Simulation (`simulator/mock_truck.py`)

Walking-Algorithmus entlang OSRM-Geometrie mit Speed-Multiplikator,
integrierter Proximity-Prüfung und realistisch begrenzter Ladekapazität:

```python
load_units = 0

while seg_index < len(coords) - 1:
    speed, paused = await get_sim_state()
    if paused:
        await sleep(0.5); continue

    budget_m = SPEED_MPS * TICK_S * speed   # Meter pro Tick

    # Walk along geometry, checking proximity at EACH segment endpoint
    pos, seg_index, hit_bin = advance_with_arrival_check(...)

    if hit_bin:
        waste_units = get_bin_fill(hit_bin)
        if load_units + waste_units > TRUCK_CAPACITY_UNITS:
            drive_to_depot(); unload(); load_units = 0

        collected = empty_bin(hit_bin)
        load_units += collected
        visited.add(hit_bin)
    await sleep(TICK_S)
```

**Key-Insight (ADR-11):** Proximity-Check muss **innerhalb** der `advance`-Loop laufen, sonst überspringt der Truck Tonnen bei hoher Speed.

**Kapazitätsmodell:** Eine 100%-Tonne entspricht 100 Ladeeinheiten. Der
Demo-Truck fasst 600 Einheiten, also grob sechs volle Tonnen. Wenn ein weiterer
Pickup die Kapazität überschreiten würde, fährt der Truck zum Depot, setzt
`action="returning_full"`, entlädt mit `action="unloading"` und nimmt die Route
danach wieder auf. Das ist der erste Schritt Richtung Mehrfahrzeug-Logik:
Später kann ein Dispatcher verbleibende Waypoints auf weitere Trucks verteilen,
statt denselben Truck Zwischenfahrten machen zu lassen.

### 6.3 Bin-Refill-Simulation (`simulator/mock_bins.py`)

```python
increment = random.uniform(0, 2) * min(speed, 5)   # sublinear gedeckelt
sleep    = max(0.5, 10.0 / speed)                  # Floor 0,5 s
```

**Warum sublinear:** Lineare Skalierung würde bei 20× zu 80 %/s führen — Truck-Pickup käme nicht hinterher.

---

## 7. Frontend-Architektur

### 7.1 Layout-Prinzip: 3-Spalten-Dashboard

```
┌──────────────────────────────────────────────────────────────┐
│  Header: Logo | Sim-Controls | Route-Info | Live-Badge       │
├─────────────┬──────────────────────────────┬─────────────────┤
│             │                              │  Tab-Switcher   │
│  Fleet      │                              │  (Chat/Energie/ │
│  Panel      │         Leaflet-Karte        │   Security)     │
│  (Liste)    │  (Bins + Truck + Route +     │                 │
│             │   Depot)                     │  Active Tab     │
│  35 Tonnen  │                              │  Content        │
│  sortiert   │                              │                 │
│  nach Fill  │                              │                 │
└─────────────┴──────────────────────────────┴─────────────────┘
```

Begründet durch User-Persona **Stefan Krüger** (Fahrer und Disponent in Personalunion): Statusübersicht + Räumlichkeit + Aktion gleichzeitig sichtbar, keine Tab-Wechsel für die häufigsten Aufgaben. Detail siehe Doku-Kapitel „Zielgruppe und User Persona".

### 7.2 Datenfluss

```
WebSocket /ws/live (2s)
  ↓
useLiveData() hook
  ↓
DashboardPage state: { bins, alerts, truck }
  ↓
Pass-through props an FleetPanel + LeafletMap + AlertBanner

REST polling /routes/latest (10s)
  ↓
activeRoute state → LeafletMap (Polyline) + Header (Route-Info)

SSE /agent/chat
  ↓
ChatInterface streamChat() callback
  ↓
messages state (lokal, nicht persistiert)
```

### 7.3 Sim-Controls

Header-Element zur Live-Steuerung der Simulation:

- **Play/Pause-Toggle:** Friert alle Simulatoren ein (`sim.paused=True`). Truck postet `action="paused"`, Bins drift en stoppt.
- **Speed-Buttons:** `1× / 5× / 10× / 20×`. Truck-Bewegung und Bin-Refill skalieren entsprechend.
- Bei Pause sind Speed-Buttons disabled (ausgegraut).

### 7.4 Chat-Tool-Transparenz

Der Agent macht Tool-Calls (z.B. `get_bins`, `plan_route`) sichtbar als klappbare Karten im Chat. Bewusst:
- User sieht **was** der Agent tut, nicht nur das Ergebnis
- Hilft Vertrauen aufbauen („kein magischer Output, sondern reproduzierbare Schritte")
- Beim Debuggen: Input/Output jedes Tools sichtbar

---

## 8. Touchpanel-Konzept (Pico W)

### 8.1 Hardware

- **MCU:** Raspberry Pi Pico W (RP2040 + CYW43439 WLAN)
- **Display:** 2,8" ILI9341 SPI, 320 × 240 px
- **Touch:** XPT2046 resistiv (4-Wire)
- **Verbindung:** Shared SPI0-Bus mit separaten CS-Pins

### 8.2 Firmware-Architektur

**Eine** MicroPython-Mainloop mit drei async-Tasks (`uasyncio`):

```python
async def main():
    await uasyncio.gather(
        sensor_loop(),    # Füllstand/Akku alle 8 s posten
        command_loop(),   # Command-Queue pollen, lock/unlock anwenden
        ui_loop(),        # Touch-Events verarbeiten, Display rendern
    )
```

State teilt sich über das `UI`-Objekt — keine IPC nötig (single-threaded cooperative async).

### 8.3 Sync-Pattern

| Richtung | Wer initiiert? | Latenz | Beispiel |
|---|---|---|---|
| Sensor → Backend | Pico (~ 8 s) | – | `POST /bins/{id}/update` mit fill_level |
| Backend → Pico | Pico pollt (~ 2 s) | ≤ 2 s | Dashboard sperrt → `lock`-Command in Queue → Pico holt |
| User → Backend | Pico (sofort bei Tap) | – | „Problem melden" → `POST /security/events` |

**Lokale Aktionen bleiben lokal:** „Klappe öffnen" geht direkt an Servo-GPIO, nicht übers Backend. Backend wird nur informiert (`status=in_use`).

### 8.4 UX

5 Pflicht-Screens:
1. **IDLE** — Füllstand + Hauptbutton
2. **Hauptmenü** — Klappe öffnen / Problem melden / Wartung
3. **Problem melden** — Beschädigt / Geruch / Zurück
4. **Gesperrt** — Vollbild-Hinweis
5. **Wartung mit PIN** — 3×4 Zahlenpad

Designprinzipien:
- **≥ 60 × 60 px Touch-Targets** (resistiv + Handschuhe)
- Keine Swipe-Gesten (resistiv unzuverlässig)
- Hoher Kontrast (Sonneneinstrahlung)
- Bitmap-Fonts statt TTF (RAM/Performance)

---

## 9. Demo-Setup

### 9.1 Vorab

`.env` im `backend/`:

```bash
DATABASE_URL=sqlite:///./smart_bin.db
ADMIN_TOKEN=changeme
GROQ_API_KEY=gsk_...
CORS_ORIGINS=["http://localhost:3000"]
```

### 9.2 Hochfahren

```bash
# Backend (Port 8000)
cd backend
.venv/bin/uvicorn main:app --port 8000

# Simulatoren (in zwei Terminals oder nohup)
cd simulator
python mock_truck.py
python mock_bins.py

# Frontend (Port 3000)
cd frontend
npm run dev
```

→ Dashboard: <http://localhost:3000>
→ Swagger: <http://localhost:8000/docs>

### 9.3 Demo-Daten

- **35 Tonnen** in 4 Clustern um die FH Soest (Westfalenweg, Kasernenweg, Elsa-Brandström, Siegener Str.) + FH Campus
- **Cluster-Größe:** 700 × 600 m
- **Depot:** Doyenweg 21
- **Fill-Verteilung deterministisch** (`random.seed(42)`): 6 kritisch / 10 hoch / 12 mittel / 7 niedrig

### 9.4 Demo-Flow (3-Minuten-Pitch)

1. Dashboard zeigt 35 smarte Tonnen, color-coded nach Füllstand
2. „Route planen" → 2-opt-Optimierung läuft, Badge zeigt Ersparnis
3. Sim-Speed 5× — Truck fährt los, leert die kritischen Tonnen
4. Im Chat: „Sperre Tonne X" → Agent ruft Tool, Dashboard reagiert sofort
5. WebSocket-Banner für Sicherheitsereignisse

---

## 10. Lessons Learned

Erfahrungen aus der Entwicklung, relevant für Maintainer und Folge-Teams.

### 10.1 Nominatim-Geocoding ist unzuverlässig

15 von 50 versuchten Adressen waren in OSM nicht erfasst (Christian-Rohlfs-Straße, Im Tabaksgang, Dammweg in 59494 Soest existieren nicht in OpenStreetMap, obwohl real). Konsequenzen:
- Adressen **vorher** prüfen, nicht erst nach dem Geocoding
- Strukturierte Queries (`street=...&city=...`) liefern bessere Treffer als Freitext
- Bei Duplikaten (mehrere Hausnummern auf der gleichen Straßenmitte): deterministischer Jitter pro Hausnummer-Hash für visuelle Trennung auf der Karte

### 10.2 Pydantic-Settings respektiert Shell-Env

Eine leere `ANTHROPIC_API_KEY=""` Shell-Variable überschrieb den Wert aus `.env`. Schwer zu debuggen, weil das Env-File äußerlich korrekt aussieht. Fix: vor Start `unset ANTHROPIC_API_KEY` oder bewusst `model_config = SettingsConfigDict(env_file=".env", ...)` in Pydantic V2.

### 10.3 LangChain 1.x bricht die 0.x-API

`AgentExecutor` und `create_tool_calling_agent` sind in LangChain 1.x entfernt. Ersatz: `create_agent` aus `langchain.agents` (LangGraph-basiert). Auch das Input-Format wechselt von `{"input": ..., "chat_history": [...]}` zu `{"messages": [...]}`. Bei Migration **beides** anpassen, nicht nur den Import.

### 10.4 Groq lehnt leere Tool-Returns ab

Ein Tool, das `[]` zurückgibt, wird von LangChain als ToolMessage mit Content `[]` weitergereicht. Groq lehnt das mit HTTP 400 ab (`content : value must be a string OR minimum number of items is 1`). Fix: Alle Tools liefern garantiert einen **nicht-leeren String** (JSON-encoded oder Klartext-Fallback bei leerem Ergebnis).

### 10.5 Sim-Speed ist ein verstecktes Race-Condition-Problem

Bei 20× füllen Bins schneller, als der Truck leeren kann. Bei großen Tick-Sprüngen (160 m/Tick) verpasst der Truck Tonnen, deren Stop-Zone (35 m) innerhalb eines Ticks komplett überfahren wird. Beide Bugs nur unter Last sichtbar. Lehre: **Skalierungs-Effekte immer im integrierten System testen**, nicht in der Komponente isoliert.

### 10.6 Dashboard ohne Marker-Interpolation wirkt billig

Roher WebSocket-Stream → Marker springt alle 2 s um 10–20 px. Wirkt amateurhaft im Demo. RAF-Interpolation für 1,5 s zwischen Updates rettet das visuelle Erlebnis ohne Server-Änderung.

### 10.7 Reverse-Engineering der UX wegen Code-First-Ansatz

Dashboard und Touchpanel-Konzept wurden **vor** den Wireframes implementiert. Konsequenz: jetzt müssen nachträglich Wireframes erstellt werden (Fulya-Briefing), damit die Doku methodisch sauber bleibt. Lehre: bei Folgeprojekten Wireframes **vor** Code, auch bei „nur" einem Prototyp.

### 10.8 Hellweg-Feedback war ein Architektur-Geschenk

Sein Einwand „warum LLM für deterministische Aufgaben?" hat die LLM-Rolle scharf gemacht — nicht als Entscheider, sondern als natürlichsprachliche Übersetzung in Tool-Calls. Das ist fachlich der einzig vertretbare LLM-Einsatz in einem solchen System.

---

## 11. Bekannte Limitierungen und Future Work

| Thema | Status | Nächste Schritte |
|---|---|---|
| Hardware-Integration (Pico W) | Konzept fertig, Firmware-Skelett vorhanden | Mech-Team integriert Sensorik + Motor; Firmware flashen |
| Held-Karp bei n > 15 | Hart gegated | Optional Branch-and-Bound oder Christofides als Mittelweg |
| Multi-Truck-Flotte | Nicht implementiert | Aktuell genau 1 Fahrzeug — VRP-Erweiterung wäre nötig |
| Auth / Multi-User | Nicht implementiert | Out of Scope für Demo |
| Historisches KPI-Dashboard | Nicht implementiert | Route-Daten persistiert, aber nicht aggregiert |
| Eigenes OSRM-Hosting | Nutzt Public Demo | Bei Production-Deployment in eigene Infrastruktur |
| Predictive Fill-Level (ML) | Nicht implementiert | Zu wenig Daten; in größerem Pilot sinnvoll |
| Vollständige Wireframes | In Arbeit (Fulya) | Web-App + Touchpanel-Screens |
| Touchpanel-State-Diagramm | Ausstehend | Lieferung mit Wireframes |

---

## 12. Verweise

- **Projekt-Dokumentation:** `Dokumentation & Präsentation Neu/Dokumentation.typ` — vollständige Doku inkl. Hardware, Mechanik, Sprintplan, Persona
- **Briefing Wireframes:** `Briefing_Fulya_Wireframes.md` — Aufgabenstellung für UX-Arbeit
- **TSP-Benchmark:** `backend/scripts/tsp_benchmark.py` — empirischer NN-vs-2-opt-vs-Exact-Vergleich
- **Geocoder:** `backend/scripts/geocode_bins.py` — Nominatim-Batch zur Adress-Verortung
- **API-Vertrag** (für Pico-Firmware): `docs/api_contract.md`

---

*Diese Doku ist die kanonische Architektur-Referenz. Bei Code-Änderungen, die hier dokumentierte Entscheidungen verändern, bitte dieses File mit aktualisieren.*
