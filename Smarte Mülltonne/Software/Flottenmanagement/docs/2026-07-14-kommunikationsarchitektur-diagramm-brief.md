# Design-Brief — Kommunikationsarchitektur (V1: Master-Datenfluss)

> **Zweck:** Vollständiger, code-verifizierter Brief für **Claude Design**, um EIN
> Master-Datenfluss-Diagramm der Kommunikationsarchitektur zu rendern.
> Anlass: Feedback „etwas wenig Pfeile". Kern-Einsicht: Die Architektur ist nicht
> sparsam — das alte Diagramm hat **realen, beidseitigen, getypten** Verkehr auf je
> einen Pfeil kollabiert. Dieser Brief faltet ihn ehrlich auf. Mehr Pfeile = korrekter.
>
> **Quelle:** Alle Kanäle, Nachrichten, Endpoints und Takte sind aus dem laufenden
> Code abgeleitet (`bridge/tcp_bridge.py`, `backend/routers/{commands,bins,ws,routes}.py`,
> `backend/services/truck_simulator.py`, `Quellcode/Client/*`). Stand 2026-07-14.

---

## 0. Harte Vorgaben (nicht verhandelbar)

- **Hintergrund MUSS transparent sein.** Kein Vollflächen-Background. Knoten-Boxen
  haben eigene, deckende Füllungen (Panel-Farben) und müssen sowohl auf hellem als
  auch dunklem Untergrund lesbar bleiben. Pfeilfarben und Label mit genügend Kontrast
  für beide Fälle wählen (nötigenfalls dünne Kontur/Halo hinter Label-Text).
- **Genau EINE Ansicht** (V1, Master-Datenfluss). Kein Sequenzdiagramm.
- **Design-System = unser CI** aus `docs/ci_farben_typografie.md` (Hexcodes unten).
  Typografie: IBM Plex (Web-App-CI).
- Querformat, eine zusammenhängende Fläche. Alle Pfeile beschriftet (Protokoll +
  Nutzlast; wo sinnvoll Takt-Badge).

---

## 1. Farbrollen (aus dem CI, semantisch belegt)

| Rolle | Farbe (Hex) | Verwendung |
|---|---|---|
| **Befehl / Steuerung** (stromabwärts) | `#f2c94c` (Akzent-Gelb) | Operator → … → Pico: Fahrbefehle |
| **Telemetrie / Status** (stromaufwärts) | `#10b981` (Grün) | Pico → … → Dashboard: Sensor-/Zustandsdaten |
| **Geofence / Sicherheit** | `#ef4444` (Rot) | ARM/DISARM (Truck-Nähe entschärft die Tonne) |
| **ACK / Handshake** | `#64748b` (Slate, gedämpft) | Befehlsbestätigungen (at-least-once) |
| **Lokal am Pico (kein Netz)** | `#64748b` gestrichelt, innerhalb der Pico-Box | Touch/Sensoren/Motoren on-device |

**Knoten-Füllungen (deckend, auf transparentem Grund):** Panel `#1a1c20`, stärker
`#202328`, Admin/dunkel `#111214`. **Text:** Primär `#f8fafc`, gedämpft `#cbd5e1` /
`#64748b`. **Marke/Highlights:** `#f2c94c`.

### Linienstil = Transportmuster (zweite, orthogonale Achse)
- **Durchgezogen** = Push / Event (TCP-Zeile, WebSocket-Push, POST bei Ereignis).
- **Gestrichelt** = **Poll** (die 1×/s-`GET`-Schleifen). Macht die Entkopplung sichtbar.
- **Badge** an der Kante = Protokoll + ggf. Takt, z. B. `HTTP GET · 1×/s`.

---

## 2. Knoten (Komponenten)

| # | Knoten | Rolle / Unterteile |
|---|---|---|
| N1 | **Operator** (Mensch) | Klickt/chattet im Leitstand |
| N2 | **Dashboard / Leitstand** | Next.js im Browser. **Mehrere Clients möglich** (Fan-out-Ziel des WebSockets) |
| N3 | **Backend** | FastAPI + SQLite. Enthält als Unterteile: **Befehls-Queue** (Command-Tabelle, „Briefkasten"), **Truck-Sync** (autonomer Auslöser), **Live-State** (bins/route/truck) |
| N4 | **TCP-Bridge** | „Übersetzerin", Port **50002**. Hält **genau eine** aktive Pico-Verbindung. Übersetzt Backend-Aktionen ⇄ Pico-Protokoll |
| N5 | **Pico (Tonne — 1 Gerät)** | Unterteile: **Antrieb/Motoren**, **Sensoren** (Füllstand/Hindernis/Linie), **Touch-Display/UI**, **Client-Stack/State-Machine**. Touch ist KEIN zweites Gerät |

**Layout-Idee:** Knoten als Kette **Operator — Dashboard — Backend(+Queue+Truck-Sync) — Bridge — Pico**.
Die **Queue** als eigenes Objekt zwischen Backend und Bridge zeichnen (Briefkasten).
Stromabwärts-Pfeile (Befehl, gelb) auf der einen Seite der Kette führen, Stromaufwärts-Pfeile
(Telemetrie, grün) auf der anderen zurück → ergibt einen sichtbaren **Kreislauf** statt einer
einzelnen Linie, ganz ohne künstliche Pfeile.

---

## 3. Pfeil-Inventar (vollständig, code-verifiziert)

Jede Zeile = ein Pfeil. Richtung wörtlich nehmen. „resp" = Antwort auf einen Poll
(als kurzer Rückpfeil oder gepaarte Kante darstellen).

### A · Befehlsweg — stromabwärts · **Gelb `#f2c94c`**
| ID | Von → Nach | Transport | Nutzlast / Nachricht | Takt | Stil |
|---|---|---|---|---|---|
| A1 | Operator → Dashboard | Interaktion | Klick / Chat | Ereignis | solid |
| A2 | Dashboard → Backend | HTTP REST **POST** | `goto_street` / `return_home` / `stop` / `lock` / `unlock` | Ereignis | solid |
| A3 | Backend → **Befehls-Queue** | in-process | *enqueue* (Command-Row) | Ereignis | solid (intern) |
| A4 | **Truck-Sync** → **Befehls-Queue** | in-process | *enqueue* `goto_street` — **AUTONOM**, ETA-Trigger wenn Truck nah | Ereignis | solid (intern), Badge „autonom" |
| A5 | Bridge → Backend | HTTP **GET** `/bins/{id}/pending-command` | holt nächsten Befehl ab | **1×/s** | **dashed** (poll) |
| A6 | Backend → Bridge | HTTP resp | `{ id, action }` oder `null` | auf Poll | dashed (resp zu A5) |
| A7 | Bridge → Pico | **TCP :50002** | `CMD_GOTO_STREET` / `CMD_RETURN_HOME` / `CMD_STOP` | Ereignis | solid |

### B · Geofence / Sicherheit — **Rot `#ef4444`**
| ID | Von → Nach | Transport | Nutzlast | Takt | Stil |
|---|---|---|---|---|---|
| B1 | Bridge → Backend | HTTP **GET** `/bins/{id}/arm-state` | Geofence-Abfrage | **1×/s** | **dashed** (poll) |
| B2 | Backend → Bridge | HTTP resp | `{ disarmed: bool }` (Truck ≤ 10 m → `true`) | auf Poll | dashed (resp zu B1) |
| B3 | Bridge → Pico | **TCP :50002** | `ARM` / `DISARM` (nur bei Änderung) | Ereignis | solid |

### C · Status- / Telemetrieweg — stromaufwärts · **Grün `#10b981`**
| ID | Von → Nach | Transport | Nutzlast / Nachricht | Takt | Stil |
|---|---|---|---|---|---|
| C1 | Pico → Bridge | **TCP :50002** | `Pico ist bereit` · `STATUS:<state>` · `BATTERY:<pct>` · `FILL:<pct>` · `ARRIVED:<STREET\|HOME>` | laufend | solid |
| C2 | Bridge → Backend | HTTP **POST** `/bins/{id}/telemetry` | `{ pico_state, battery, fill, target_destination }` (battery/fill gecacht, reiten auf nächstem STATUS mit) | Ereignis | solid |
| C3 | Backend → Dashboard(s) | **WebSocket** Broadcast | Live-State (bins · truck · route) — **Fan-out an alle Clients** | laufend | solid (WS, dick) |
| C4 | Dashboard → Backend | HTTP **GET** `/bins`, `/routes`, `/routes/latest`, `/routes/candidates` | Zustands-Poll | periodisch | **dashed** (poll) |

### D · ACK-Kette (at-least-once) — **Slate `#64748b`**
| ID | Von → Nach | Transport | Nutzlast | Takt | Stil |
|---|---|---|---|---|---|
| D1 | Pico → Bridge | **TCP :50002** | `ACK <cmd>` (Pico bestätigt Befehl) | Ereignis | solid |
| D2 | Bridge → Pico | **TCP :50002** | `ACK_RECEIVED <cmd>` (Handshake zurück) | Ereignis | solid |
| D3 | Bridge → Backend | HTTP **POST** `/bins/{id}/ack` | `{ command_id, success, pico_state }` → Befehl erledigt | Ereignis | solid |

### E · Lokal am Pico (KEIN Netz) — **Slate gestrichelt, innerhalb der Pico-Box**
| ID | Von → Nach | Nutzlast | Stil |
|---|---|---|---|
| E1 | Touch-Display → Client-Logik | Deckel öffnen / PIN / Menü | dashed (intern) |
| E2 | Sensoren → Client-Logik | Linien-/Hindernis-/Füllstand-Werte | dashed (intern) |
| E3 | Client-Logik → Antrieb/Motoren | Fahr-/Regelbefehle | dashed (intern) |

---

## 4. Erklär-Callouts (kurze Textmarken im Diagramm)

Diese drei Aussagen sind der „ehrliche Architektur"-Kern und sollen als kleine
Callouts nahe der jeweiligen Kanten stehen:

1. **Entkopplung / Briefkasten:** „Kein direkter Draht — **Backend legt ab, Bridge holt ab**
   (Poll 1×/s). Beide Seiten laufen unabhängig weiter." (nahe Queue / A3–A5)
2. **At-least-once:** „Jeder Befehl wird bestätigt (ACK-Kette D1–D3). Verbindungsabriss
   ⇒ erneute Zustellung, kein stiller Verlust." (nahe D)
3. **Ein Pico macht alles:** „Touch, Sensoren und Motoren im **selben Gerät**; lokale
   Aktionen laufen ohne Netz." (in/an der Pico-Box, E1–E3)
4. *(optional)* **Geofence:** „`DISARM`, wenn der Truck ≤ 10 m ist — die Tonne wird zum
   Leeren entschärft." (nahe B3)

---

## 5. Legende (im Diagramm platzieren)

- **Farbe = Absicht:** Gelb = Befehl · Grün = Telemetrie · Rot = Geofence/Sicherheit ·
  Slate = ACK · gedämpft/gestrichelt (intern) = lokal am Pico.
- **Linie = Transportmuster:** durchgezogen = Push/Event · **gestrichelt = Poll (1×/s)**.
- **Transporte:** `TCP :50002` (zeilenbasiert) · `HTTP/REST` · `WebSocket` · `in-process` (Queue).
- **Badges:** Takt (`1×/s`), `autonom` (A4), `Fan-out` (C3).

---

## 6. Was das Diagramm bewusst leistet (für die Erklärung)

- Es zeigt **beide Richtungen** getrennt (Befehl abwärts, Telemetrie aufwärts) → der
  „Kreislauf" ist sichtbar, nicht eine einzelne Kette.
- Es macht die **Entkopplung** (Poll-Queue) und die **at-least-once-ACK-Kette**
  explizit — das sind echte, benennbare Architektur-Eigenschaften, keine Deko.
- Es trennt **Netz-Kommunikation** (A–D) sauber von **lokaler On-Device-Logik** (E)
  und untermauert damit „ein Pico macht alles".
- Ergebnis: deutlich mehr — und **korrekte** — Pfeile, ohne die Aussage zu verfälschen.
