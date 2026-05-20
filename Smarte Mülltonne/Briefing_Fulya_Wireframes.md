# Briefing: Wireframes Web-App + Touchpanel

**An:** Fulya
**Von:** Jonas
**Stand:** Mai 2026
**Aufwand-Schätzung:** ca. 1–2 Tage

---

## Worum geht's

Wir haben die Flottenmanagement-Web-App und das Touchpanel-Konzept im Code-First-Modus gebaut — ohne vorher saubere Wireframes anzulegen. Für die Doku, die Verteidigung und die weitere UX-Arbeit brauchen wir das jetzt nachträglich. Du übernimmst quasi ein **Reverse-Engineering der UX**: Du schaust dir an, was wir gebaut haben, und übersetzt es in saubere, dokumentierbare Wireframes — als hätten wir den Schritt von Anfang an gemacht.

Das hat zwei Vorteile:
1. **Für die Doku/Präsentation**: Wir können die Wireframes als Grundlage zeigen und so methodisch korrekt argumentieren, dass User-Centered-Design die Basis war.
2. **Für die Weiterentwicklung**: Sobald die Wireframes existieren, können wir Schwachstellen erkennen und gezielt verbessern, bevor wir wieder Code anfassen.

---

## Aufgabe 1: Web-App-Wireframes (Bestand)

### Was du bekommst
- **Screenshot der aktuellen Web-App** (kommt von mir per WhatsApp)
- Optional: Live-Zugriff auf die App, wenn du sie selbst klicken willst (sag Bescheid, dann machen wir Meeting, ich starte ich sie auf meinem Rechner und teile den Bildschirm)

### Was du machst
Erstelle Wireframes (Low- bis Mid-Fidelity) der zentralen Web-App-Bildschirme. Das Tool ist dir freigestellt — **Figma**, **Excalidraw**, **Whimsical**, **Penpot** oder klassisch auf Papier-Scan, Hauptsache nachvollziehbar und exportierbar als PNG/SVG/PDF.

#### Mindestens diese Screens:
1. **Dashboard-Hauptansicht** (3-Spalten-Layout)
   - Linke Spalte: Fleet-Panel (Liste aller Tonnen sortiert nach Füllstand)
   - Mitte: Karte mit Tonnen-Markern, Truck-Marker, Route-Polyline, Depot-Marker
   - Rechte Spalte: Tab-Panel (Chat / Energie / Sicherheit)
   - Header: Logo, Sim-Speed-Controls (Play/Pause + 1×/5×/10×/20×), Route-Info, Live-Status-Badge, Individuelle Tonnenbadges (Auf dem Weg zum Abholpunkt / Auf dem Weg nach Hause) 
2. **Chat-Ansicht (rechte Spalte)**
   - Quick-Prompt-Chips, Tool-Call-Karten (klappbar), User- und Assistant-Bubbles, Eingabefeld
3. **Energie-Tab**
   - Liste mit Akku, Ladestatus pro Tonne
4. **Sicherheits-Tab + Alert-Banner**
   - Banner oben bei aktiven Events, Eventliste mit Sperren/Quittieren-Aktionen
5. **Tonne im "Gesperrt"-Zustand auf der Karte**
   - Wie sieht eine gesperrte Tonne aus, was ändert sich im Fleet-Panel?

#### Worauf du achten sollst
- **Layout-Logik dokumentieren**: Warum 3 Spalten? Warum Karte zentral? Wo sind die primären vs. sekundären Aktionen?
- **Persona im Hinterkopf**: Stefan Krüger (42, Fahrer + Disponent in Personalunion). Mobile Nutzung im Fahrerhaus, Handschuhe, Sonneneinstrahlung. → Große Bedienelemente, klare Kontraste, keine Hover-Abhängigkeiten.
- **Annotation**: Jeder Wireframe sollte beschriftet sein — was ist das Element? Was passiert beim Klick? Welche Daten zeigt es?

### Was wir am Ende brauchen
- Ein Figma-File (oder Equivalent), aus dem sich PNG/PDF exportieren lässt
- Idealerweise pro Screen ein kurzes Annotations-Layer (3–5 Sätze pro Screen)

---

## Aufgabe 2: Touchpanel-Wireframes (Konzept)

### Kontext
An jeder Tonne soll ein **2,8-Zoll-Touchscreen (320×240 Pixel, resistiv)** verbaut werden, gesteuert von einem Raspberry Pi Pico W. Das ist die Schnittstelle für **Anwohner** (Klappe öffnen, Problem melden) und gelegentlich für **Wartungspersonal** (Wartungsmodus mit PIN). Sehr enge Hardware-Beschränkungen:

- Nur 320×240 Pixel — entspricht ~6,5 cm Bildschirmdiagonale
- Resistiv → Buttons müssen **mindestens 60×60 Pixel** sein
- Keine Tastatur, kein Drag, kein Pinch-Zoom
- Ablesbarkeit bei Tageslicht (hoher Kontrast erforderlich)

### Was du machst
Wireframes für die folgenden 5 Screens. Jeder Screen muss in 320×240 funktionieren. Du kannst in Figma einen Frame mit genau diesen Dimensionen anlegen.

1. **IDLE / Startbildschirm**
   - Zeigt: Tonne-Name, Füllstand-Balken, Status („Verfügbar"), 1 Hauptbutton
2. **Hauptmenü**
   - 3 Buttons: Klappe öffnen / Problem melden / Wartung (PIN)
3. **Problem melden**
   - 2-3 Optionen:  Beschädigt / Geruch & Hygiene + Zurück-Button / etc.
4. **Gesperrt-Zustand**
   - Vollbild-Hinweis: „GESPERRT — Diese Tonne ist außer Betrieb"
   - Kein interaktives Element (außer evtl. „Hinweis" für nächste Tonne)
5. **Wartungsmodus (PIN-Eingabe)**
   - 3×4 Zahlenpad, PIN-Anzeige (verdeckt), Bestätigen + Löschen

### Bonus (optional)
- **Wartungs-Untermenü** nach erfolgreicher PIN-Eingabe (Geleert manuell / Diagnose / Zurück)
- **State-Diagramm** als kleine Übersicht: Welcher Screen führt wohin? Beim Code-Skeleton existiert die State-Machine schon, aber visuell wäre das toll.

### Was wir am Ende brauchen
- Wireframes als 320×240-Frames in Figma (oder als 320×240-Bilder einzeln)
- Eine **State-Diagramm-Skizze** (was-führt-wohin) — kann auch handschriftlich/Excalidraw sein
- Kurze Notiz pro Screen: Welche Schriftgröße? Welche Tap-Targets sind kritisch?

---

## Was wir bewusst NICHT von dir wollen (Scope)

- **Keine Hi-Fi-Designs / Pixel-Perfect** — Wireframes reichen, gerne in Graustufen oder mit minimaler Farbcodierung (rot = voll, grün = ok, grau = gesperrt)
- **Keine Animations- oder Mikrointeraktions-Designs** — wir reden über Layout und Flows, nicht über Hover-Zustände oder Übergänge
- **Kein Klick-Prototyp** — wenn du Lust hast und schnell bist, gerne, aber nicht erforderlich
- **Keine Anwender-Interviews / User Research** — das machen wir gemeinsam später

---

## Deliverables — Zusammenfassung

| # | Was | Format |
|---|---|---|
| 1 | Web-App-Wireframes (5 Screens, annotiert) | Figma + PNG/PDF-Export |
| 2 | Touchpanel-Wireframes (5 Screens, je 320×240) | Figma + PNG-Export |
| 3 | State-Diagramm Touchpanel | Figma/Excalidraw/Skizze |
| 4 | Kurze Begleitnotizen | 1–2 Seiten Markdown oder direkt als Annotations-Layer |

---

## Fragen?

Bei allem, was unklar ist: schreib mir kurz an. Ich kann dir auch jederzeit die App live zeigen oder einzelne Komponenten erklären. Wenn du am Layout was nicht verstehst, frag lieber kurz, bevor du loslegst — wir wollen vermeiden, dass du Wireframes für Funktionen baust, die wir gar nicht haben.

**Persona-Beschreibung Stefan Krüger** findest du in der aktuellen Doku unter:
`Dokumentation & Präsentation Neu/Dokumentation.pdf`, Kapitel **„Zielgruppe und User Persona"** — als Grundlage für deine Designentscheidungen.

Viel Spaß damit! 🚀
