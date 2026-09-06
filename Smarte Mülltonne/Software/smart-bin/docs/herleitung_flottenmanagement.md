# Herleitung: Flottenmanagement-App

> **Projekt:** Smarte Mülltonne 2.0
> **Zweck:** Herleitung für Präsentation und Modul-Dokumentation — *Wie kamen wir
> auf die Idee? Wie auf die Funktionen? Wie haben wir es umgesetzt?*
> **Methodischer Fokus:** agentisches, KI-gestütztes Coding (Multi-Agent).
> **Stand:** Juli 2026. Technische Aussagen sind aus Code/Docs des Repos belegt;
> mit ✅ markierte Punkte wurden gegen die Codebasis verifiziert.

---

## 1. Ausgangslage & Idee

Der Flottenmanagement-Gedanke entstand aus der **Modul-Aufgabenstellung**. Früh
stand eine grundlegende Richtungsentscheidung an:

> **Consumer-App** (Endnutzer/Haushalt) **oder App für den Entsorgungsbetrieb?**

Wir haben uns bewusst für die **App für den Entsorgungsbetrieb** entschieden.
Ausschlaggebend war der **Konnektivitäts-Gedanke**: Der eigentliche Mehrwert
vernetzter Tonnen entsteht nicht beim einzelnen Haushalt, sondern dort, wo viele
Tonnen als **Flotte** koordiniert werden.

### Warum der Entsorgungsbetrieb der sinnvollere Adressat ist

- **Füllstandsbasierte statt starrer Routen:** Der Betrieb ist von typischen,
  festen Abholzeiten **entkoppelt**. Statt „jeden Dienstag alles" kann er seine
  Routen **anhand der realen Füllstände** planen.
- **Vorteil für den Nutzer:** Eine volle Tonne kann eine **frühere Leerung**
  bekommen, statt bis zum starren Turnus zu warten.
- **Vorteil für den Betrieb:** deutlich **mehr Flexibilität** bei Routenplanung
  und Abholzeiten — nur anfahren, was sich lohnt.
- **Umwelt- & Service-Gedanke:** weniger Leerfahrten, kürzere Routen, bedarfs-
  gerechter Service. Die Vernetzung zahlt direkt auf Effizienz und Nachhaltigkeit
  ein.

### Leitidee (Vision): Prädiktive Füllstandsanalyse

Als weiterführender Gedanke steht die **prädiktive Füllstandsanalyse**: aus dem
Füllstandsverlauf vorhersagen, *wann* eine Tonne voll sein wird, und die Route
vorausschauend planen. Das ist die **konzeptionelle Leitidee** des Projekts.

> **Ehrliche Einordnung fürs Modul:** In der aktuellen Umsetzung ist die
> Routenauswahl **schwellenbasiert** (Tonnen ab einem Füllstand-Grenzwert werden
> eingesammelt) mit anschließender **Routenoptimierung (2-opt)**. Ein trainiertes
> Prognosemodell ist noch nicht implementiert — die Prädiktion ist der **Ausblick**,
> auf den die Architektur (kontinuierliche Füllstand-Telemetrie) hinarbeitet.

---

## 2. Funktionsherleitung — von der Idee zu den Features

Aus der Entscheidung „Werkzeug für den Entsorgungsbetrieb" ergaben sich die
Funktionen als **operativer Leitstand** (nicht als Endkunden-App):

| Bedürfnis (aus der Idee) | Abgeleitete Funktion | Im Code |
|---|---|---|
| Flotte auf einen Blick | Karten-Dashboard mit Tonnen-Pins, Flotten-Panel | `frontend/.../LeafletMap.tsx`, `FleetPanel.tsx` |
| Füllstände real kennen | Live-Füllstand-Telemetrie (Tonne → Leitstand) | `bridge/tcp_bridge.py`, `bins.py` (Telemetrie) |
| Bedarfsgerecht sammeln | Füllstand-Schwelle + Routenplanung/-optimierung | `routers/routes.py` (`/plan`, 2-opt) |
| Route abfahren & steuern | Müllwagen-Simulation, Dispatch (Start/Stop) | `services/truck_simulator.py`, `routes.py` (`/start`,`/stop`) |
| Energie im Blick | Akku-/Energie-Monitoring der Tonnen | `EnergyPanel.tsx`, Akku-Telemetrie |
| Sicherheit an der Straße | Geofence: Alarm bei unbefugter Deckelöffnung | `bins.py` (`arm-state`, 10 m) ✅ |
| Bedienung vor Ort | Touchpanel an der Tonne (Status, Diagnose) | `firmware/pico_touchpanel/` |
| Operator-Unterstützung | Chat/Agent-Interface im Leitstand | `ChatInterface.tsx`, `routers/agent.py` |

Kurz: Die Idee „der Betrieb plant nach Füllstand" zieht zwingend **Telemetrie
(rein)**, **Routenlogik (verarbeiten)** und **Dispatch/Visualisierung (raus)**
nach sich — genau der Funktionsumfang des Leitstands.

---

## 3. Methodik: Agentisches, KI-gestütztes Coding

Das Projekt wurde durchgängig mit **KI-Agenten** entwickelt — und zwar
**Multi-Agent über zwei Phasen**:

| Phase | Agent | Ergebnis |
|---|---|---|
| **1 — Flottenmanagement-App (V1)** | **Codex** | WebApp/Leitstand: FastAPI-Backend, Datenmodell, Next.js-Dashboard, Müllwagen-Simulation, Command-Queue |
| **2 — Hardware-Integration** | **Claude Code** | Anbindung der realen Tonne: TCP-Bridge, Telemetrie, Touchpanel, Sicherheits-/Fahrlogik |

### 3.1 Agentische Arbeitsweisen (eingesetzte Skills)

Die Umsetzung folgte nicht dem Muster „ein Prompt = fertige App", sondern einem
Set bewusster **Arbeitsweisen im Umgang mit den KI-Agenten**. Diese Skills sind
der eigentliche methodische Kern des Projekts:

**Brainstorming (Konzept vor Code).** Vor dem Bauen eines Features wurde das
Problem gemeinsam mit dem Agenten exploriert — Zielbild, Optionen, Trade-offs —
und erst daraus eine Spezifikation/ein Plan abgeleitet. Erst danach wurde Code
erzeugt. So entstanden abgestimmte Anforderungen statt vorschnellem Code.

**Multi-Agent-Prompting.** Aufgaben wurden auf **spezialisierte Agenten**
verteilt, je nach Stärke des Werkzeugs: **Codex** für die Flottenmanagement-WebApp
(Phase 1), **Claude Code** für die Hardware-Integration (Phase 2). Innerhalb einer
Phase wurden abgegrenzte Teilaufgaben zusätzlich an **Sub-Agenten** delegiert
(subagent-getriebene Umsetzung), um klar umrissene Arbeitspakete parallel/fokussiert
abzuarbeiten.

**Wireframes → initialer Prompt → UI.** Startpunkt der Web-App waren **Wireframes**
(liegen im Repo, u. a. `Briefing_Fulya_Wireframes.md` und die Excalidraw-Diagramme
unter `docs/`). Sie wurden als **initialer Prompt** an den Agenten gegeben, der
daraus die UI entwickelte. Die Designvorgaben (dunkler Leitstand, gelber Akzent,
Karte zentral, Flotte links, Status/Meldungen rechts) sind in
`docs/claude_prompt_webapp_pico_integration_scope.md` festgehalten.

**Vertical Slicing.** Gebaut wurde in **vertikalen Durchstichen**: statt Schicht
für Schicht wurde **eine Funktion komplett durch alle Ebenen** umgesetzt —
**Datenbank → Backend → Frontend** — als in sich lauffähiges Arbeitspaket. Nach
jedem Slice steht ein demonstrierbares, durchgängiges Feature — ideal für die
agentische Iteration und für Zwischenstände vor dem Prof. Der Ansatz ist im Repo
namentlich verankert: `docs/api_contract.md` beschreibt den **„ersten Vertical
Slice"** der Hardware-Anbindung.

**Iteration & Testing.** Kern der agentischen Arbeit war der **Zyklus aus Bauen →
Testen → Nachschärfen**. Features wurden am realen Aufbau geprüft (siehe
`docs/hardwaretestkatalog_2026-07-04.md`), gefundene Fehler flossen als nächster
Prompt zurück in den Agenten, der gezielt nachbesserte — teils über mehrere Runden
pro Feature (z. B. Motor-Pin-Korrektur, Kalibrierung und Stabilisierung des
Füllstandsensors). So näherte man sich iterativ dem funktionierenden Ergebnis, statt
auf einen „großen Wurf" zu setzen.

### 3.2 Bridge & Command-Queue als Adapter an die bestehende Logik ✅

Die zweite Phase durfte die in Phase 1 gebaute WebApp **nicht neu erfinden**.
Stattdessen wurde die Hardware **an die bestehende Backend-Logik angepasst** —
über eine **Adapterschicht**, nicht durch Umbau von Backend oder Firmware.

> **Verifikation gegen den Code:**
> - `docs/api_contract.md`: *„Die alte Pico-Firmware bleibt der autonome Echtzeit-
>   Kern… Eine kleine Bridge verbindet beide Welten… Bridge kann durch direkte
>   HTTP-Polling-Firmware ersetzt werden, **ohne Dashboard und Backend umzubauen**."*
> - `docs/iot_kommunikation.md`: *„Damit musste die **bestehende, funktionierende
>   Pico-Firmware nicht angefasst werden**… Die Bridge stülpt die moderne HTTP-Welt
>   darüber."*
>
> Der Pico spricht ein zeilenbasiertes **TCP-Protokoll**, das Backend spricht
> **HTTP/REST**. Die **TCP-Bridge** übersetzt zwischen beiden. Befehle laufen über
> eine **Command-Queue**: das Backend legt Kommandos ab (`enqueue`), die
> Bridge **pollt** sie (`/pending-command`) und reicht sie an den Pico weiter.
> Dieses Polling-Modell fügt sich in die vorhandene HTTP-Backend-Logik ein — die
> Adaption erfolgte also **nachträglich an die bestehende Logik**, wie beabsichtigt.

---

## 4. Umsetzung & Architektur

Die Systemarchitektur ist eine **lineare Vier-Boxen-Kette** (aus
`docs/iot_kommunikation.md`):

```
   Pico  ←TCP→  TCP-Bridge  ←HTTP→  Backend  ←WS/HTTP→  Dashboard
 (Tonne)        (Übersetzer)        (Hub)              (Browser)
 MicroPython    Python/asyncio      FastAPI+SQLite     Next.js
```

Kernentscheidungen:

- **Warum eine Bridge?** TCP-Welt (Pico) und HTTP-Welt (Backend) passen nicht
  direkt zusammen. Die Bridge übersetzt und hält die bestehende Firmware
  unangetastet.
- **Command-Queue statt Push:** Der Pico ist **nicht durchgehend online** — während
  der Fahrt trennt er bewusst das WLAN (»Hard-Offline-Modus«), damit Netzwerk-
  Traffic die Echtzeit-Fahrschleife nicht stört. Ein **Poll-Modell** passt zu
  diesem Verhalten besser als ein permanenter Push-Kanal.
- **Geofence-Sicherheit:** An der Straße ist die Tonne „scharf"; kommt der
  Müllwagen näher als **10 m**, wird sie automatisch entschärft (legitime
  Leerung). Unbefugtes Öffnen davor → Buzzer am Gerät + Meldung im Leitstand. ✅

---

## 5. Ergebnis & Ausblick

**Erreicht:**

- Durchgängiger Leitstand: Flotten-Karte, Live-Füllstand-/Akku-Telemetrie,
  schwellenbasierte Routenplanung mit Optimierung, Müllwagen-Dispatch,
  Sicherheits-Geofence, Touchpanel an der realen Tonne.
- Reale Tonne fährt vom (simulierten) Müllwagen getriggert zur Straße und nach
  der Leerung selbsttätig heim — die Hardware-Integration schließt den Kreis.

**Ausblick:**

- **Prädiktive Füllstandsanalyse** als nächster Schritt auf Basis der bereits
  laufenden kontinuierlichen Telemetrie.
- **Direkte HTTP-Polling-Firmware** könnte die Bridge langfristig ersetzen — ohne
  Backend/Dashboard anzufassen (die Adapter-Architektur hält diesen Weg offen).

---

## Anhang: Kernaussagen für die Slides

- **Idee:** aus der Aufgabenstellung → bewusste Wahl **Entsorgungsbetrieb statt
  Consumer** (Konnektivität, Effizienz, Umwelt/Service).
- **Funktionen:** folgen zwingend aus „Routenplanung nach Füllstand" →
  Telemetrie · Routenlogik · Dispatch/Visualisierung.
- **Methode:** **agentisches KI-Coding** mit bewussten Skills — **Brainstorming**,
  **Multi-Agent-Prompting** (Codex → Claude Code, + Sub-Agenten),
  **Wireframes → Prompt → UI**, **Vertical Slicing**, **Iteration & Testing**;
  Ergebnis u. a. **Bridge/Command-Queue als Adapter** an die bestehende Logik.
- **Architektur:** Pico ↔ Bridge ↔ Backend ↔ Dashboard.
