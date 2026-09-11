# Corporate Identity — Farben & Typografie

> **Projekt:** Smarte Mülltonne 2.0 — Flottenmanagement-Leitstand + Touchpanel
> **Zweck:** Verbindliche Referenz der verwendeten Farben (inkl. Hexcodes) und
> Typografie für Präsentation und Modul-Dokumentation.
> **Stand:** Juli 2026 — abgeleitet direkt aus dem Code (`frontend/app/globals.css`,
> Dashboard-Komponenten, `firmware/pico_touchpanel/`).

Das Projekt hat **zwei Oberflächen** mit bewusst gemeinsamer Designsprache:

1. **Web-App / Leitstand** (Next.js Dashboard, Operator-Ansicht im Browser)
2. **Touchpanel** (Display direkt an der Tonne, gerendert auf dem Pico)

Beide teilen die **Ampel-Logik** (Gelb = Akzent/mittel, Grün = ok, Rot = kritisch)
auf dunklem/neutralem Grund. Die Gelbtöne unterscheiden sich leicht, weil das
Touchpanel über ein RGB565-Display läuft (sattes LED-Gelb) und die Web-App ein
wärmeres Signalgelb nutzt.

---

## 1. Farben — Web-App (Leitstand)

### 1.1 Basis / Neutral

| Rolle | Hex | Einsatz |
|---|---|---|
| Haupt-Hintergrund | `#151619` | App-Grund, dunkle Fläche |
| Panel | `#1a1c20` | Karten/Panels |
| Panel (stärker) | `#202328` | Eingabefelder, hervorgehobene Panels |
| Panel (Admin) | `#111214` | Sekundäre Flächen im Admin |
| Vordergrund / Text | `#f8fafc` | Primärtext (nahezu weiß) |
| Text auf Gelb | `#171717` | Schrift/Icon auf gelbem Grund |
| Text gedämpft | `#cbd5e1` / `#64748b` | Sekundärtext (`slate-300` / `slate-500`) |

### 1.2 Akzent (Marke)

| Rolle | Hex | Einsatz |
|---|---|---|
| Akzent-Gelb | `#f2c94c` | Marke, primäre Buttons, aktive Zustände, Highlights |
| Akzent-Gelb Hover | `#ffd866` | Hover auf gelben Buttons |

Der gelbe Akzent ist die tragende Markenfarbe und stellt die Verbindung zum
Touchpanel her.

### 1.3 Status-Ampel

**Füllstand** (Karten-Pins & Balken, `LeafletMap.tsx`):

| Bedingung | Farbe | Hex |
|---|---|---|
| ≥ 80 % (voll/dringend) | Rot | `#ef4444` |
| ≥ 50 % (mittel) | Gelb | `#f2c94c` |
| < 50 % (ok) | Grün | `#10b981` |

**Akku / Energie** (`EnergyPanel.tsx`):

| Bedingung | Farbe | Hex |
|---|---|---|
| < 20 % (kritisch) | Rot | `#f87171` (`red-400`) |
| < 50 % (niedrig) | Gelb | `#f2c94c` |
| sonst (gut) | Grün | `#6ee7b7` (`emerald-300`) |

**Truck-Auslastung:** ≥ 90 % `#dc2626` · ≥ 70 % `#f2c94c` · sonst `#10b981`

**Weitere Semantik:**

| Rolle | Hex |
|---|---|
| Erfolg / OK | `#10b981` / `#6ee7b7` (emerald) |
| Fehler / kritisch | `#ef4444` / `#dc2626` (red) |
| Warnung (Amber-Alert-Text) | `#f8dda0` |

---

## 2. Farben — Touchpanel (Pico-Display)

Werte im Code als RGB (`color565(r, g, b)`), hier zusätzlich als Hex.

### 2.1 Akku-Anzeige

| Rolle | RGB | Hex | Einsatz |
|---|---|---|---|
| Akku normal | `(255, 198, 32)` | `#FFC620` | gefüllter Akku, Normalzustand |
| Akku leer / schwach | `(224, 72, 56)` | `#E04838` | niedriger Ladestand |
| Akku lädt | `(120, 200, 90)` | `#78C85A` | Ladevorgang (Blitz/Stecker) |

### 2.2 Flächen & Elemente

| Rolle | RGB | Hex |
|---|---|---|
| Tonnenkörper | `(104, 106, 102)` | `#686A66` |
| Label / Beschriftung | `(204, 204, 200)` | `#CCCCC8` |
| Panel-Hintergrund (Top-Bar / Diagnose) | `(66, 65, 66)` | `#424142` |
| Werte-Text (Diagnose) | `(255, 255, 255)` | `#FFFFFF` |
| Asset-Transparenz-Key (nur intern) | `(255, 0, 255)` | `#FF00FF` |

> Hinweis: Der Magenta-Key `#FF00FF` ist keine sichtbare Farbe, sondern markiert
> in den RLE-Assets transparente Pixel.

---

## 3. Typografie — Web-App (Leitstand)

### 3.1 Schriftfamilie

Bewusst **kein Webfont**, sondern der native System-UI-Stack (schnell, kein
Ladeflackern, plattformkonsistent):

```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
```

Für technische Werte (IDs, Koordinaten, Eingaben) wird zusätzlich **Monospace**
(`font-mono`, System-Mono-Stack) eingesetzt.

### 3.2 Typo-Skala (verwendete Größen)

| Klasse | Größe | Einsatz |
|---|---|---|
| `text-lg` | 18 px | Überschriften/Titel |
| `text-base` | 16 px | Fließtext (selten) |
| `text-sm` | 14 px | Standard-UI-Text |
| `text-xs` | 12 px | Labels, Meta, Panels (häufigste Größe) |
| `text-[11px]` / `text-[10px]` | 11 / 10 px | Kleine Labels, Chips |

### 3.3 Schriftschnitte & Label-Stil

- **Gewichte:** `font-semibold` (dominant), `font-medium`, `font-bold`
- **Signatur-Label-Stil:** `UPPERCASE` + weites Tracking
  (`tracking-[0.18em]`, `tracking-[0.22em]`, `tracking-[0.28em]`) — der typische
  „Leitstand"-Look für Sektions-Labels (z. B. „LEITSTAND", „ADMIN").

---

## 4. Typografie — Touchpanel (Pico-Display)

Da das Display keine echte Font-Engine hat, werden Texte **vorab als Bild
gerendert** und als RLE-Assets (`.rle`) auf den Pico gelegt.

- **Schriftart:** **Arial Bold**
  (Fallback: Helvetica Neue → Helvetica)
- **Rendering-Tool:** `firmware/pico_touchpanel/tools/render_*.py` (PIL/Pillow)

| Element | Font-Größe | Anmerkung |
|---|---|---|
| Diagnose-Werte (Füllstand %, Hindernis cm) | 14 px | Cap-Height ~9 px |
| Datum (Top-Bar) | 13 px | Arial Bold |
| Adresse | 15 px | Arial Bold |

> **Wichtig:** Die eingebaute `display.text()`-Bitmap-Schrift (8×8) wird **nicht**
> für lesbaren Text genutzt — sie rendert transponiert/gespiegelt. Alle
> lesbaren Panel-Texte laufen über vorab gerenderte Arial-Bold-Assets.

---

## 5. Quick-Reference

| | Web-App | Touchpanel |
|---|---|---|
| 🟡 Gelb | `#f2c94c` | `#FFC620` |
| 🟢 Grün | `#10b981` | `#78C85A` |
| 🔴 Rot | `#ef4444` | `#E04838` |
| ⬛ Neutral/Grund | `#151619` / `#202328` | `#424142` / `#686A66` |
| ⬜ Text | `#f8fafc` | `#FFFFFF` / `#CCCCC8` |
| 🔤 Schrift | System-UI-Stack (+ Mono) | Arial Bold (gerendert) |
