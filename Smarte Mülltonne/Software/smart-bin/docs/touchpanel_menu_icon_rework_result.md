# Touchpanel Hauptmenue-Tonnenicons: Ergebnis Kontrastkorrektur

Stand: 2026-06-22

Umsetzung des Tasks aus `claude_touchpanel_menu_icon_prompt.md` unter Beachtung
von `touchpanel_tonnenicon_design_notes.md`.

## Befund (vor der Aenderung)

Die RLE-Assets sind palettenbasiert (`WF1`-Header: width, height, Palette,
danach pro Zeile `(run, palette_index)`-Paare). Analyse der aktiven
Rollback-Version `menu_1.rle` / `menu_2.rle`:

- Jeder Button ist ein zweifarbiges Rechteck: obere Bande hellgrau
  (`#7B7D7B`, ~123) und untere Bande etwas dunkler (`#6A6D6A`, ~106),
  Trennkante in Buttonmitte.
- Das Tonnen-Icon (Deckel, gelbes Funktionssymbol, helles Label, dunkle Fuesse)
  liegt darueber.
- **Es gibt gar keinen gefuellten Tonnenkoerper.** Der Bereich zwischen Deckel
  und Fuessen ist reiner Button-Hintergrund. Deshalb wirkte die Tonne
  ungefuellt — nicht weil der Koerper "fast dieselbe Farbe" wie der Button hat,
  sondern weil schlicht keine Koerperflaeche existiert.

## Loesungsansatz

Reine Paletten-/Pixel-Recolor-Loesung, kein Verschieben von Geometrie:

- Als geometrische Basis dient die aktive Rollback-Version (identisch mit
  `backups/2026-06-22_before_menu_contrast_fix/`).
- Aus dem fehlgeschlagenen Versuch
  (`backups/2026-06-22_failed_menu_contrast_attempt/`) wurde **ausschliesslich
  die saubere Koerper-Maske** (welche Pixel zur Tonnenkoerper-Trapezflaeche
  gehoeren) als Referenz uebernommen. Diese Maske beruehrt nur ehemalige
  Button-Hintergrundpixel — Deckel, Label, Gelb und Fuesse bleiben unberuehrt.
- Inhaltlich wurde **nicht** auf dem Failed-Attempt aufgebaut: dessen Fehler war
  der nahezu schwarze, plakative Fuellton. Es wurde nur die Koerperflaeche
  uebernommen und mit einem dezenten Ton neu gefuellt.

Der Koerper erhaelt eine 3-stufige Wireframe-Schattierung (statt eines flachen
Blocks):

| Layer            | RGB888        | RGB565   | Zweck                                  |
|------------------|---------------|----------|----------------------------------------|
| Koerper hell     | (96, 98, 96)  | 0x630C   | obere Koerperkante, leichtes Volumen   |
| Koerper Hauptton | (72, 74, 72)  | 0x4A49   | Hauptflaeche, eine klare Stufe < Button|
| Koerper Kante    | (54, 56, 54)  | 0x39C7*  | Seiten/Silhouette, etwas dunkler       |

\* `0x39C7` existierte bereits in beiden Paletten und wurde wiederverwendet.

Zum Vergleich: Button ~106/123. Der Hauptton 72 liegt eine klar erkennbare
Stufe darunter, bleibt aber deutlich heller als der nahezu schwarze
Failed-Ton (~49/56/57) und als Deckel/Fuesse (~24). Gelb, Label und Deckel sind
unveraendert.

## Geaenderte Dateien

- `firmware/pico_touchpanel/assets/menu_1.rle`
  (Palette 28 -> 30 Eintraege, 5219 Koerperpixel umgefaerbt)
- `firmware/pico_touchpanel/assets/menu_2.rle`
  (Palette 31 -> 32 Eintraege, 4958 Koerperpixel umgefaerbt)

`ui.py` wurde nicht geaendert. Layout, Buttonpositionen, Iconpositionen,
Proportionen, Pfeile, Statuspunkte und Touchboxen bleiben unangetastet.

## Backup

Vor der Aenderung angelegt:

```text
firmware/pico_touchpanel/backups/2026-06-22_before_claude_menu_icon_rework/
  menu_1.rle
  menu_2.rle
  ui.py
```

## Test auf dem Pico

- Pico verbunden an `/dev/cu.usbmodem21101`.
- `menu_1.rle` und `menu_2.rle` per `mpremote` nach `:/assets/` kopiert.
- `mpremote ... reset` ausgefuehrt — erfolgreich.

## Ergebnis am echten Display: ABGELEHNT, zurueckgerollt

Bewertung am echten Touchpanel (2026-06-22):

- Die gefuellten Trapez-Koerper (Kandidat B) wirkten auf dem Panel wie
  **"fette Boxen", die ueber die eigentliche Form gelagert sind**. Die feine
  Wireframe-Anmutung ging verloren — derselbe Grundfehler wie beim frueheren
  Failed-Attempt, nur weniger dunkel.
- Auf Wunsch wurde **vollstaendig auf die gute Rollback-Version zurueckgerollt**
  (lokal + Pico, `mpremote cp` + `reset`).
- Aktiver Stand wieder Hash `2070df…cfbd6` / `beae13…38235`
  (== `2026-06-22_before_menu_contrast_fix`).

## Wichtige Learnings fuer den naechsten Versuch

1. **Das Panel rendert stark blaustichig.** Neutrale Palette-Grautoene
   erscheinen als Blau. Klar lesbar bleiben nur sehr dunkle Toene
   (Deckel ~ schwarz), Gelb und das helle Label. Grau-auf-Grau-Kontrast ist
   praktisch wertlos — entscheidend ist der **Helligkeitsabstand (Value)**.
2. **Eine gefuellte Trapezflaeche ist der falsche Weg.** Sowohl der dunkle
   Failed-Versuch als auch der dezentere Kandidat B wurden abgelehnt, weil eine
   geschlossene Koerperflaeche ueber der filigranen Wireframe-Form als plumpe
   Box wahrgenommen wird. Die Akzeptanz haengt nicht an der Tonwahl, sondern an
   der **Idee "Flaeche fuellen" selbst**.
3. **Im Rollback existiert gar kein Koerper-Layer.** Die Tonne besteht nur aus
   Deckelbalken, hellem Label, gelbem Symbol und Fuessen; der Rumpf ist leerer
   Button-Hintergrund. "Koerper sichtbar fuellen" und "Wireframe-Form behalten"
   stehen damit in direktem Konflikt.
4. **Moeglicher naechster Ansatz statt Flaechenfuellung:** nur eine duenne,
   klar dunkle **Kontur/Silhouette** des Tonnenrumpfes ziehen (Linien, kein
   Fill) — analog zu Deckel und Fuessen, die auf dem Panel gut lesbar sind. So
   bekaeme die Tonne eine erkennbare Begrenzung, ohne als gefuellte Box zu
   wirken. Vor Umsetzung mit dem Nutzer abstimmen.

Render-/Simulationsvergleiche (inkl. Blaustich-Simulation) lagen unter
`/tmp/menu_dbg/` vor. Backup der gefuellten Variante existiert nicht separat;
sie ist aus Rollback + Maske jederzeit reproduzierbar.
