# Touchpanel Tonnen-Icons: Design- und Umsetzungsnotizen

Stand: 2026-06-22

Dieses Dokument beschreibt, wie die Tonnen-Icons im Touchpanel umgesetzt sind,
welche Designentscheidungen bisher gut funktioniert haben und wo die aktuellen
Probleme liegen. Es ist als Briefing fuer einen weiteren Coding-Agenten gedacht.

## Kontext

Die Touchpanel-Firmware liegt hier:

```text
Smarte Mülltonne/Software/smart-bin/firmware/pico_touchpanel/
```

Die sichtbaren Screens werden nicht live aus SVGs gerendert, sondern als
vorgefertigte RLE-Bitmap-Assets geladen:

```text
firmware/pico_touchpanel/assets/*.rle
```

Der Renderer sitzt in:

```text
firmware/pico_touchpanel/wireframe.py
```

Die Screen-Logik sitzt in:

```text
firmware/pico_touchpanel/ui.py
```

Wichtig: Die beiden Hauptmenues mit den 4 Funktionsbuttons links/rechts werden
als komplette Screens geladen:

```text
assets/menu_1.rle
assets/menu_2.rle
```

Die Touchboxen liegen zwar in `ui.py`, aber die sichtbaren Button- und
Iconformen stecken in den RLE-Assets.

## Aktueller guter Stand / Rollback

Der letzte akzeptierte Stand vor dem fehlgeschlagenen Kontrastversuch wurde
gesichert unter:

```text
firmware/pico_touchpanel/backups/2026-06-22_before_menu_contrast_fix/
```

Darin liegen:

```text
assets/menu_1.rle
assets/menu_2.rle
ui.py
```

Dieser Stand ist aktuell wieder aktiv. Die Formen der Tonnen-Icons sind dort
grundsaetzlich richtig:

- Position der Tonnen innerhalb der Buttons passt.
- Skalierung der Icons passt.
- Button-Groessen und Button-Positionen passen.
- Pfeile, Statuspunkte und Zurueck-Pfeil passen.
- Gesamtkomposition des doppelseitigen Hauptmenues passt.

Bitte diesen Stand als geometrische Basis verwenden.

## Fehlgeschlagener Versuch

Ein Kontrastversuch wurde gesichert unter:

```text
firmware/pico_touchpanel/backups/2026-06-22_failed_menu_contrast_attempt/
```

Der Versuch hat die Tonnenkoerper in `menu_1.rle` und `menu_2.rle`
nachtraeglich per geometrischem Recoloring dunkler gemacht. Das war in der
Desktop-Vorschau besser, auf dem echten Display aber optisch ein Fail.

Bitte nicht auf diesem Versuch aufbauen.

Warum der Ansatz nicht funktioniert hat:

- Die Tonnen wurden zu plakativ und wirkten nicht mehr wie der vorherige
  Wireframe-Stil.
- Die feinen Proportionen und Layer der Icons wurden durch das grobe Uebermalen
  gestoert.
- Das Problem ist nicht nur "Tonne dunkler machen", sondern gezielter
  Material-/Layer-Kontrast innerhalb des bestehenden Designs.

## Aktuelles Problem

Auf dem echten Display wirken die Tonnen-Icons im Hauptmenue teilweise so, als
waeren sie nicht gefuellt.

Beobachtung:

- Der Tonnenkoerper hat fast dieselbe Farbe wie der Button-Hintergrund.
- Dadurch bleiben vor allem Deckel, Label, gelbe Symbole und schwarze Kanten
  sichtbar.
- Die eigentliche Tonnenflaeche verschmilzt mit dem Button.
- Bei Lichteinstrahlung wird das Problem deutlich staerker.

Kurz: Die Formen sind gut, aber der lokale Kontrast zwischen Button und
Tonnenkoerper ist zu schwach.

## Display-Learning

Das verwendete Touchdisplay zeigt feine Grauabstufungen schlecht:

- Grauverlaeufe wirken stufig.
- Grau auf Grau verliert bei Umgebungslicht schnell Kontrast.
- Dunkler Dark Mode wirkt auf dem Desktop gut, ist auf dem Panel aber schlechter
  lesbar.
- Gelb bleibt wichtig als Akzent, darf aber auf hellerem Grau nicht ausbleichen.

Deshalb:

- Keine subtilen Verlaeufe als Hauptkontrast verwenden.
- Nicht zu viele nah beieinanderliegende Grautoene nutzen.
- Wichtige Formen brauchen harte, aber stilistisch saubere Tonwerttrennung.
- Gelb moeglichst stabil lassen oder nur sehr vorsichtig anheben.

## Designentscheidungen fuer das Tonnen-Icon

Die Tonne soll weiterhin wie im Wireframe aussehen:

- schwarzer/dunkler Deckel mit gelbem Griff/Deckelakzent,
- kleines helles Rechteck/Touchpanel vorne oben,
- trapezfoermiger Tonnenkoerper,
- schwarze/dunkle Raeder und Standfuesse,
- dezente Vorderstruktur, aber nicht zu viel Detail,
- Funktionssymbol in Gelb vor/auf der Tonne,
- kein 8-Bit-/Pixelart-Stil,
- keine rein flache Silhouette ohne Wireframe-Anmutung.

Wichtige Erkenntnis aus den Statusscreen-Arbeiten:

- Formen muessen sauber bleiben.
- Nachtraegliches Uebermalen kompletter Koerperbereiche kann die Wirkung
  zerstoeren.
- Besser ist ein gezieltes Re-Exportieren oder Recoloring aus der Quelle mit
  klar definierten Layerfarben.

## Empfohlener Loesungsansatz

Nicht grob in den RLEs uebermalen. Besser:

1. Die aktuelle gute Version von `menu_1.rle` und `menu_2.rle` als Basis nehmen.
2. Falls moeglich aus der urspruenglichen SVG-/Designquelle neu exportieren.
3. Nur die Tonnenkoerper-Farbe in den Menue-Icons leicht vom Button absetzen.
4. Button-Hintergruende nicht stark veraendern, weil deren Position/Form bereits
   gut ist.
5. Deckel, gelbe Symbole, Pfeile und helle Label-Flaechen nicht veraendern.

Kontrastidee:

- Buttonflaeche: aktueller mittlerer Grauton darf bleiben oder minimal heller.
- Tonnenkoerper: etwas dunkler und neutraler als Button, aber nicht schwarz.
- Tonnen-Seiten/Kanten: minimal dunkler als Koerper.
- Label oben: hell lassen.
- Gelb: moeglichst unveraendert, weil es auf dem Panel gut sichtbar ist.

Wichtig: Tonnenkoerper soll sichtbar gefuellt sein, aber nicht wie ein grober
schwarzer Block wirken.

## Was nicht wiederholen

Bitte vermeiden:

- komplette Tonnenkoerper mit einem grossen Polygon hart zu uebermalen,
- den Tonnenkoerper zu dunkel zu machen,
- die Proportion der Tonne zu veraendern,
- Iconpositionen erneut zu verschieben,
- Buttonpositionen erneut zu verschieben,
- Gelb zu entsaettigen,
- Hintergrund/Button und Tonne mit denselben Grau-/Blauwerten zu belassen.

## Konkrete Dateien

Zu bearbeiten:

```text
firmware/pico_touchpanel/assets/menu_1.rle
firmware/pico_touchpanel/assets/menu_2.rle
```

Nur bei Bedarf:

```text
firmware/pico_touchpanel/ui.py
```

`ui.py` sollte fuer diese Aufgabe normalerweise nicht geaendert werden, weil die
Touchboxen und Screen-Navigation bereits passen.

## Testworkflow

Vor jedem Versuch:

1. Backup anlegen, z.B.

```text
firmware/pico_touchpanel/backups/YYYY-MM-DD_before_menu_recolor_attempt/
```

2. Mindestens sichern:

```text
assets/menu_1.rle
assets/menu_2.rle
ui.py
```

3. Assets aendern.
4. Nur `menu_1.rle` und `menu_2.rle` auf den Pico kopieren.
5. Pico resetten.
6. Direkt auf dem echten Display bei Raumlicht und Lichteinstrahlung bewerten.

Upload-Beispiel:

```bash
fw="/ABSOLUTER/PFAD/ZU/firmware/pico_touchpanel"
python3 -m mpremote connect /dev/cu.usbmodemXXXX cp "$fw/assets/menu_1.rle" :/assets/menu_1.rle
python3 -m mpremote connect /dev/cu.usbmodemXXXX cp "$fw/assets/menu_2.rle" :/assets/menu_2.rle
python3 -m mpremote connect /dev/cu.usbmodemXXXX reset
```

## Offene Designfrage

Neben den Tonnen-Icons gibt es ein allgemeines Lesbarkeitsproblem:

- Das UI ist sehr dunkel.
- Die Menues bestehen aus Grau auf Grau.
- Bei Lichteinstrahlung ist der Kontrast schwach.

Moeglicher spaeterer Schritt:

- den allgemeinen Menue-Hintergrund minimal heller oder neutraler machen,
- die Buttonflaechen klarer vom Hintergrund trennen,
- aber Gelb-Kontrast erhalten.

Dieser Schritt sollte getrennt vom Tonnen-Icon-Fix getestet werden. Erst die
Tonnen-Icons stabil bekommen, dann den allgemeinen Hintergrund anpassen.
