# IoT-Kommunikation — Tonne ↔ Server ↔ Dashboard

> **Zweck:** Vollständige, zeichnungsreife Beschreibung aller Kommunikationswege. Strukturiert für Excalidraw — Boxen für Akteure, beschriftete Pfeile für Protokoll + Takt.
>
> **Stand:** Mai 2026, entspricht dem echten Firmware-Code unter `Software/Quellcode/Client/` und der Bridge `Flottenmanagement/bridge/tcp_bridge.py`

---

## 0. Das Wichtigste zuerst

**Es gibt genau EINEN Pico in der Tonne.** Er macht alles:

- **Antrieb:** 2 DC-Motoren, 5 Liniensensoren, PD-Regler, 50-Hz-Fahrschleife
- **Sensoren:** Ultraschall-Füllstand, Ultraschall-Hindernis
- **Bedienung:** 2 Buttons (rot/grün), Buzzer, Status-LEDs
- **Netzwerk:** TCP-Socket-Client zum Server
- **Touchpanel (Ziel):** Das Display-UI ist aktuell ein separater Prototyp (`Flottenmanagement/firmware/pico_touchpanel/`), soll aber in dieselbe Firmware integriert werden — **derselbe Pico**, nicht ein zweiter.

**Eine zentrale Besonderheit:** Der Pico ist **nicht durchgehend online**. Während der Fahrt trennt er das WLAN absichtlich (»Hard-Offline-Modus«), weil Netzwerk-Traffic die Echtzeit-Fahrschleife stören würde. Er ist nur an Haltepunkten (Standby, Wartepunkt) verbunden.

---

## 1. Akteure (deine Boxen im Excalidraw)

Vier Boxen reichen:

| Box | Was läuft drin | Wo | Sprache |
|---|---|---|---|
| **Pico** | Antrieb + Sensoren + Touchpanel-UI, TCP-Client | in der Tonne | MicroPython |
| **TCP-Bridge** | `tcp_bridge.py`, übersetzt TCP ↔ HTTP | Laptop, Port 50002 | Python (asyncio) |
| **Backend** | FastAPI + SQLite + Routing + Agent | Laptop, Port 8000 | Python |
| **Dashboard** | Next.js Web-App | Browser, Port 3000 | TypeScript/React |

**Anordnung-Vorschlag (lineare Kette, leicht zu lesen):**

```
   Pico  ←TCP→  TCP-Bridge  ←HTTP→  Backend  ←WS/HTTP→  Dashboard
 (Tonne)        (Übersetzer)        (Hub)              (Browser)
```

Das ist die ganze Grundstruktur. Alles andere sind Details *auf* diesen Pfeilen.

---

## 2. Warum eine Bridge? (die Kernidee)

Der Pico spricht **TCP** (rohe Text-Zeilen über einen Socket). Das Backend spricht **HTTP** (REST-Endpoints). Diese zwei Welten passen nicht direkt zusammen.

Die **TCP-Bridge** ist ein kleiner Übersetzer-Prozess auf dem Laptop:

- Nach **unten** (zum Pico): hält den TCP-Socket auf Port 50002 offen, schickt/empfängt Text-Zeilen
- Nach **oben** (zum Backend): macht normale HTTP-Calls gegen die FastAPI

Damit musste die **bestehende, funktionierende Pico-Firmware nicht angefasst werden**. Sie kennt nur ihre TCP-Welt, genau wie vorher. Die Bridge stülpt die moderne HTTP-Welt darüber.

> **Excalidraw-Tipp:** Die Bridge in einer eigenen Farbe (z.B. violett) zeichnen — sie lebt bewusst „zwischen den Welten". Links davon TCP-Welt, rechts HTTP-Welt.

---

## 3. Das TCP-Protokoll (Pico ↔ Bridge)

Zeilenbasiert, mit `\n` getrennt. Aus dem echten Firmware-Code (`global_controller.py`).

### 3.1 Pico → Bridge (was die Tonne meldet)

| Nachricht | Bedeutung |
|---|---|
| `Pico ist bereit` | Boot abgeschlossen, bereit für Befehle |
| `STATUS:<state>` | Aktueller Zustand (siehe State-Liste unten) |
| `ARRIVED: STREET` | An der Straße / Abholpunkt angekommen |
| `ARRIVED: HOME` | Zurück am Depot/Zuhause |
| `ACK CMD_GOTO_STREET` | Befehl verstanden + akzeptiert |

### 3.2 Bridge → Pico (was der Server befiehlt)

| Nachricht | Bedeutung |
|---|---|
| `CMD_GOTO_STREET` | Fahr zum Abholpunkt los |
| `CMD_RETURN_HOME` | Fahr zurück zum Depot |
| `CMD_STOP` | Anhalten |
| `ACK_RECEIVED <cmd>` | Bestätigt, dass ein Pico-ACK angekommen ist |

### 3.3 Pico-Zustände (State Machine)

| State | Bedeutung |
|---|---|
| `STANDBY` | Wartet am Depot auf Befehl |
| `LINE_FOLLOWING` | Fährt gerade entlang der Linie |
| `WAIT_AT_STREET` | Wartet am Abholpunkt |
| `ARRIVED` | Kurzzeitig beim Erreichen eines Ziels |
| `FULL` | Tonne voll (Füllstand-Sensor) |
| `EMPTIED` | Tonne geleert |
| `OBSTACLE` | Hindernis erkannt, gestoppt |
| `USER_PAUSED` | Per Button pausiert |

---

## 4. Annahme für Demo & Doku: durchgehend WLAN

Für unser Szenario gilt: **Auf dem gesamten Gelände ist WLAN verfügbar.** Die Tonne ist also durchgehend mit dem Backend verbunden — auch während der Fahrt. Alle Diagramme in diesem Dokument gehen von dieser Annahme aus, weil sie den Ablauf einfacher und verständlicher macht.

### Randnotiz: der „Hard-Offline-Modus" der echten Firmware

Die aktuelle Pico-Firmware (`global_controller.py`) hat eine Besonderheit, die man kennen sollte: Sie trennt das WLAN **absichtlich während der Fahrt** — nicht wegen fehlender Abdeckung, sondern weil das Netzwerk die 50-Hz-Echtzeit-Fahrschleife stören würde. Die Tonne wäre dann beim Fahren kurz offline und meldet sich erst am Zielpunkt wieder.

Das ist ein **Firmware-Flag**, kein Naturgesetz:

- **Demo-Szenario (dieses Dokument):** WLAN überall, Flag deaktiviert gedacht → durchgehende Verbindung, Live-Telemetrie auch während der Fahrt.
- **Stromsparbetrieb / schwache CPU:** Flag aktiv → Tonne ist beim Fahren offline, meldet sich nur an Haltepunkten.

Für die Präsentation reicht die einfache Annahme „immer verbunden". Wer die Firmware anfasst, muss aber wissen, dass das Trennen aktuell standardmäßig drin ist.

---

## 5. Diagramm A: System-Übersicht (das große Bild)

Halte es als **lineare Kette** — keine kreuzenden Pfeile.

```
┌─────────────┐   TCP :50002    ┌──────────────┐   HTTP :8000    ┌─────────────┐
│             │  ───────────→   │              │  ───────────→   │             │
│    PICO     │   Text-Zeilen   │  TCP-BRIDGE  │   REST-Calls    │   BACKEND   │
│  (Tonne)    │  ←───────────   │ (Übersetzer) │  ←───────────   │  (FastAPI)  │
│             │                 │              │                 │   + SQLite  │
└─────────────┘                 └──────────────┘                 └──────┬──────┘
  Antrieb                                                                │
  Sensoren                                                          WS + REST + SSE
  Touchpanel                                                             │
  (1 Gerät)                                                        ┌─────▼──────┐
                                                                   │ DASHBOARD  │
                                                                   │ (Browser)  │
                                                                   └────────────┘
```

**Pfeil-Beschriftungen:**
- Pico ↔ Bridge: `TCP Port 50002 · Text-Zeilen · nur an Haltepunkten`
- Bridge ↔ Backend: `HTTP · Poll 1 s + Events`
- Backend ↔ Dashboard: `WebSocket Push 2 s · REST on-demand · SSE Chat`

---

## 6. Diagramm B: Was die Bridge eigentlich tut

Die Bridge ist eine **Übersetzerin**. Sie spricht zwei Sprachen und macht im Grunde nur drei Dinge:

| # | Aufgabe | In einfachen Worten |
|---|---|---|
| 1 | **Briefkasten prüfen** | Fragt das Backend einmal pro Sekunde: „Liegt ein Auftrag für die Tonne an?" |
| 2 | **Status weitergeben** | Wenn die Tonne meldet „ich fahre" oder „ich bin angekommen", reicht die Bridge das ans Backend weiter, damit das Dashboard es anzeigt |
| 3 | **Erledigung bestätigen** | Wenn die Tonne einen Auftrag angenommen hat, meldet die Bridge „erledigt" zurück ans Backend |

### Warum braucht es überhaupt eine Übersetzerin?

Die **Tonne** und das **Backend** sprechen technisch unterschiedliche „Sprachen":

- Die Tonne kennt nur kurze Funk-Kommandos wie *„fahr zur Straße"* oder *„fahr heim"*.
- Das Backend denkt in Aufträgen wie *„Auftrag Nr. 42: Abholfahrt starten"*.

Die Bridge übersetzt zwischen beiden. Sie nimmt einen Backend-Auftrag und macht daraus das passende Funk-Kommando für die Tonne — und umgekehrt.

### Die Übersetzungstabelle

| Backend sagt … | Bridge funkt an die Tonne … |
|---|---|
| „Abholfahrt starten" | „fahr zur Straße" |
| „zurück zum Depot" | „fahr heim" |
| „anhalten / sperren" | „stopp" |

> **Bild fürs Verständnis:** Die Bridge ist wie eine Dolmetscherin am Telefon. Das Backend ruft an und sagt auf Deutsch „starte die Abholfahrt". Die Dolmetscherin sagt es der Tonne in deren Sprache. Antwortet die Tonne, übersetzt sie zurück. Keiner der beiden muss die Sprache des anderen lernen.

<details>
<summary>Technische Details (nur für Entwickler)</summary>

Die Bridge nutzt diese HTTP-Endpoints des Backends:

| Aufgabe | HTTP-Call | Takt |
|---|---|---|
| Befehl abholen | `GET /bins/{id}/pending-command` | alle 1 s (Poll) |
| Status melden | `POST /bins/{id}/telemetry` | bei Status-Wechsel |
| Befehl quittieren | `POST /bins/{id}/ack` | nach Pico-ACK |

Befehls-Mapping im Code (`tcp_bridge.py`): `goto_street`/`start` → `CMD_GOTO_STREET`, `return_home` → `CMD_RETURN_HOME`, `stop`/`pause`/`lock` → `CMD_STOP`.
</details>

---

## 7. Diagramm C: Kompletter Ablauf — Dashboard schickt Tonne los

**Wichtig zum Verständnis:** Das ist **keine** durchgehende Kette von oben nach unten. Es sind **zwei getrennte Abläufe**, die sich an einem gemeinsamen Punkt treffen: der **Befehls-Queue** (= ein Briefkasten).

- Das **Backend** wirft einen Befehl in den Briefkasten und ist fertig.
- Die **Bridge** schaut *unabhängig davon* jede Sekunde in den Briefkasten und holt sich, was drin liegt.

Die beiden Seiten kennen sich nicht und laufen zeitlich entkoppelt. Genau deshalb „taucht die Bridge plötzlich auf" — sie pollt einfach dauernd im Hintergrund.

### Teil 1 — Befehl wird aufgegeben (gerade Kette von oben nach unten)

```
   ┌────────────┐
   │  Operator  │
   └─────┬──────┘
         │  "Starte Abholfahrt" (Klick/Chat)
         ▼
   ┌────────────┐
   │  Dashboard │
   └─────┬──────┘
         │  HTTP  POST /agent/chat
         ▼
   ┌────────────┐
   │  Backend   │   Agent ruft Tool, erzeugt Befehl
   └─────┬──────┘
         │  legt Befehl ab
         ▼
   ┌────────────────────────┐
   │  📬 BEFEHLS-QUEUE       │   ← Briefkasten. Hier endet Teil 1.
   │  {action: goto_street}  │
   └────────────────────────┘
```

### Teil 2 — Tonne holt den Befehl ab (eigener Ablauf, läuft dauernd)

```
   ┌────────────────────────┐
   │  📬 BEFEHLS-QUEUE       │   ← derselbe Briefkasten
   └─────┬──────────────────┘
         ▲  "Liegt was an?"  (Bridge fragt JEDE SEKUNDE per HTTP GET)
         │
   ┌─────┴──────┐
   │ TCP-Bridge │   holt den Befehl ab
   └─────┬──────┘
         │  TCP  CMD_GOTO_STREET
         ▼
   ┌────────────┐
   │    Pico    │   nimmt Auftrag an, fährt los
   └─────┬──────┘
         │  fährt (bleibt per WLAN verbunden) →
         │  meldet Status laufend
         ▼
   ┌────────────┐
   │    Pico    │   TCP  ARRIVED: STREET (angekommen)
   └─────┬──────┘
         │
         ▼
   ┌────────────┐
   │ TCP-Bridge │   HTTP  POST /telemetry
   └─────┬──────┘
         ▼
   ┌────────────┐
   │  Backend   │   WebSocket-Push
   └─────┬──────┘
         ▼
   ┌────────────┐
   │  Dashboard │   Karte aktualisiert sich
   └────────────┘
```

### So zeichnest du es in Excalidraw

- **Zwei Spalten** nebeneinander: links Teil 1, rechts Teil 2
- In der Mitte **eine** Briefkasten-Box (`📬 BEFEHLS-QUEUE`), auf die beide Teile zeigen — das ist der verbindende Punkt
- Teil 1: Pfeile zeigen **in** den Briefkasten (Befehl wird abgelegt)
- Teil 2: Bridge-Pfeil zeigt mit Beschriftung „pollt jede Sekunde" **auf** den Briefkasten, dann geht es weiter runter zum Pico

> **Merksatz:** Backend *legt ab*, Bridge *holt ab*. Sie reden nie direkt miteinander — der Briefkasten entkoppelt beide. Das ist das ganze Geheimnis (Fachbegriff: Pull-basierte Command-Queue).
>
> *(Hinweis: In unserem Demo-Szenario ist überall WLAN, die Tonne bleibt durchgehend verbunden. Die echte Firmware kann beim Fahren trennen — siehe §4.)*

---

## 8. Diagramm D: Wo das Touchpanel hingehört

Das Touchpanel ist **Teil desselben Pico**, kein eigenes Gerät. Es ist die lokale Bedien- und Anzeigeoberfläche an der Tonne.

```
            ┌──────────────────────────────────────┐
            │              PICO (1 Gerät)           │
            │                                       │
            │   ┌─────────┐  ┌─────────┐  ┌──────┐  │
            │   │ Antrieb │  │Sensoren │  │ Touch│  │
            │   │ Motoren │  │ Füllst. │  │Display│ │
            │   │ Linien  │  │ Hindern.│  │  UI  │  │
            │   └─────────┘  └─────────┘  └──────┘  │
            │         └──────────┬──────────┘       │
            │              ┌──────────┐             │
            │              │TCP-Client│             │
            │              └─────┬────┘             │
            └────────────────────┼──────────────────┘
                                 │ TCP :50002
                                 ▼
                          ┌──────────────┐
                          │  TCP-Bridge  │
                          └──────────────┘
```

### Wer bedient das Touchpanel?

| Nutzer | Aktion am Display | Was technisch passiert |
|---|---|---|
| Anwohner | „Deckel öffnen" | **lokal** (GPIO/Servo), kein Netz nötig |
| Anwohner | „Problem melden" | später: Meldung über TCP/Bridge an Backend |
| Wartung | PIN + Diagnose | **lokal** am Display |

> **Wichtig fürs Verständnis:** Die meisten Touchpanel-Aktionen sind **lokal** — sie brauchen kein Backend. Das passt perfekt zum Hard-Offline-Modus: Auch wenn die Tonne gerade fährt und offline ist, funktioniert das Display weiter.

### Offene Design-Frage

Das aktuelle Touchpanel-Prototyp-Stub (`Flottenmanagement/firmware/pico_touchpanel/`) ist als HTTP-Direkt-Client gedacht. Der echte Pico nutzt aber TCP + Hard-Offline. Bei der Integration muss entschieden werden:

- Entweder das Touchpanel nutzt **denselben TCP-Kanal** wie der Antrieb (konsistent, aber nur online an Haltepunkten)
- Oder Display-Reports werden **lokal gepuffert** und beim nächsten Online-Fenster gesendet

---

## 9. Endpoint-Referenz (Hardware-relevant)

Alles, was die Bridge im Namen des Pico aufruft:

| Endpoint | Methode | Zweck |
|---|---|---|
| `/bins/{id}/pending-command` | GET | Befehl abholen (oder `null`) |
| `/bins/{id}/telemetry` | POST | Pico-Status melden (mit Mapping auf Bin-Status) |
| `/bins/{id}/ack` | POST | Befehl quittieren |
| `/bins/{id}/command` | POST | (Backend-intern) Befehl in Queue legen |

Status-Mapping im Backend (`bins.py`): `pico_state` → Dashboard-Bin-Status. Z.B. `FULL` → `fill_level ≥ 95`, `EMPTIED` → `fill_level = 0`.

---

## 10. Excalidraw-Cheat-Sheet

### Farben (Hex)
- **Pico / Hardware:** `#F59E0B` (amber)
- **TCP-Bridge:** `#A855F7` (violett — lebt zwischen den Welten)
- **Backend:** `#2563EB` (blau)
- **Dashboard:** `#10B981` (grün)

### Pfeil-Stile
- **Durchgezogen** = TCP oder HTTP-Request
- **Gestrichelt** = WebSocket-Push / SSE-Stream
- **Doppelpfeil** = bidirektionale Session (TCP-Socket, WebSocket)

### Pfeil-Label-Format
```
Protokoll · Pfad/Befehl · Takt
```
Beispiel: `HTTP · GET /pending-command · alle 1 s`

### Welche Diagramme als separate Files
1. `iot_uebersicht.excalidraw` — Diagramm A (lineare Kette, das Hauptbild)
2. `iot_hard_offline.excalidraw` — der Online/Offline-Balken aus §4
3. `iot_ablauf_losfahren.excalidraw` — Diagramm C (Sequenz)
4. `iot_pico_innen.excalidraw` — Diagramm D (was im einen Pico steckt)

> Tipp: Fang mit Diagramm A + dem Hard-Offline-Balken an. Die beiden zusammen erklären 80 % des Systems.

---

## 11. Was noch offen ist

| Punkt | Status |
|---|---|
| Touchpanel in Haupt-Firmware integrieren | Stub existiert separat, noch nicht vereint |
| Touch-Hardware (XPT2046) anschließen | Pin-Mapping + Kalibrierung offen |
| Touchpanel-Reports über TCP vs. lokal puffern | Design-Entscheidung offen (siehe §8) |
| TCP-Bridge Auto-Start | aktuell manuell `python bridge/tcp_bridge.py` |
| Telemetrie-Auth | aktuell ohne Auth |

---

*Grundlage für die Excalidraw-Zeichnungen. Bei Architektur-Änderungen bitte hier aktualisieren, damit Diagramm und Realität synchron bleiben.*
