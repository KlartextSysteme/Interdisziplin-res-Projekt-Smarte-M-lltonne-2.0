# Claude Prompt: Touchpanel Hauptmenue-Tonnenicons ueberarbeiten

Du arbeitest im Repository der smarten Muelltonne 2.0. Ziel ist eine sehr
gezielte Ueberarbeitung der Touchpanel-Hauptmenues auf dem Pico-Display.

## Ausgangslage

Die Touchpanel-Firmware liegt hier:

```text
Smarte Mülltonne/Software/Flottenmanagement/firmware/pico_touchpanel/
```

Die beiden Hauptmenues werden als vorberechnete RLE-Bitmap-Assets angezeigt:

```text
firmware/pico_touchpanel/assets/menu_1.rle
firmware/pico_touchpanel/assets/menu_2.rle
```

Die aktuelle aktive Version ist ein Rollback auf den letzten guten Stand. Diese
Version ist geometrisch korrekt:

- Buttonpositionen passen.
- Buttongroessen passen.
- Zurueck-Pfeil passt.
- Seitenwechsel-Pfeile passen.
- Statuspunkte unten passen.
- Tonnen-Icons sitzen grundsaetzlich an der richtigen Stelle.
- Touchboxen und Navigation sollen nicht angefasst werden.

Wichtig: Die Datei `ui.py` soll fuer diesen Task normalerweise nicht geaendert
werden. Die sichtbaren Iconformen stecken in `menu_1.rle` und `menu_2.rle`.

## Unbedingt zuerst lesen

Lies vor der Umsetzung diese Doku:

```text
Smarte Mülltonne/Software/Flottenmanagement/docs/touchpanel_tonnenicon_design_notes.md
```

Darin stehen die Learnings aus dem letzten fehlgeschlagenen Versuch, der
Rollback-Stand und die Display-spezifischen Designentscheidungen.

## Ziel

Die Tonnen-Icons in den beiden Hauptmenues sollen auf dem echten Touchdisplay
sichtbar gefuellt wirken.

Aktuelles Problem:

- Die Tonnenkoerper haben fast dieselbe Farbe wie die Button-Hintergruende.
- Dadurch wirken die Tonnen im Hauptmenue teilweise ungefuellt.
- Sichtbar bleiben vor allem Deckel, gelbe Symbole und schwarze Kanten.
- Bei Lichteinstrahlung wird der Kontrast deutlich schlechter.

Gesucht ist kein neues Design, sondern eine vorsichtige Kontrastkorrektur.

## Was erhalten bleiben muss

Bitte unveraendert lassen:

- Layout der beiden Hauptmenues.
- Position und Groesse der Buttons.
- Position der Tonnen-Icons.
- Proportionen der Tonnen.
- Zurueck-Pfeil oben links.
- Pfeile zum Seitenwechsel.
- Statuspunkte unten.
- Gelbe Funktionssymbole.
- Schwarze/dunkle Raeder und Deckelkanten.
- Allgemeine Wireframe-Optik.

Die Formen waren vor dem letzten Experiment gut. Es geht nur darum, die
Tonnenkoerper klarer vom Button-Hintergrund abzusetzen.

## Was beim letzten Versuch falsch lief

Nicht wiederholen:

- grosse geometrische Flaechen ueber die Tonnen malen,
- Tonnenkoerper zu plakativ abdunkeln,
- Layer/Details der Tonne zerstoeren,
- Tonnen neu positionieren,
- Button-Hintergruende neu layouten,
- Gelb entsaettigen,
- die Wireframe-Anmutung durch flache Blockformen ersetzen.

Der letzte Ansatz, die RLEs per grobem Recoloring mit Masken zu uebermalen, hat
auf dem echten Display nicht funktioniert.

## Gewuenschter Ansatz

Arbeite minimalinvasiv:

1. Sichere vor jeder Aenderung den aktuellen Stand.
2. Nutze die aktive Rollback-Version als geometrische Basis.
3. Veraendere nur die Farbwerte der Tonnenkoerper bzw. ihrer direkten
   Koerper-Layer in `menu_1.rle` und `menu_2.rle`.
4. Der Tonnenkoerper soll etwas dunkler/neutraler als der Button-Hintergrund
   sein, aber nicht schwarz.
5. Seiten/Kanten duerfen minimal dunkler sein als die Hauptflaeche.
6. Das kleine helle Rechteck/Display vorne an der Tonne bleibt hell.
7. Deckel und gelbe Akzente bleiben in ihrer aktuellen Wirkung.

Falls moeglich, bevorzuge eine saubere Re-Export- oder palettebasierte
Recoloring-Loesung statt grobem Pixel-Uebermalen.

## Designrichtung

Das Touchpanel ist klein und zeigt feine Grauabstufungen schlecht.

Daher:

- keine subtilen Grau-auf-Grau-Unterschiede als alleinigen Kontrast verwenden,
- keine Verlaeufe als Hauptloesung,
- lieber wenige klare Tonwerte,
- Tonnenkoerper sichtbar gefuellt, aber weiterhin dezent,
- Gelb muss auf dem Display gut sichtbar bleiben.

Kontrastidee:

- Button: aktueller mittlerer blaugrauer Ton bleibt weitgehend.
- Tonnenkoerper: eine klar erkennbare Stufe dunkler als Button.
- Tonnenkanten/Seiten: noch eine kleine Stufe dunkler.
- Label/Touchpanel-Flaeche: hell.
- Funktionssymbol: gelb.

## Backup-Pflicht

Vor dem Bearbeiten ein Backup anlegen:

```text
firmware/pico_touchpanel/backups/YYYY-MM-DD_before_claude_menu_icon_rework/
```

Mindestens sichern:

```text
firmware/pico_touchpanel/assets/menu_1.rle
firmware/pico_touchpanel/assets/menu_2.rle
firmware/pico_touchpanel/ui.py
```

Es gibt bereits relevante Backups:

```text
firmware/pico_touchpanel/backups/2026-06-22_before_menu_contrast_fix/
firmware/pico_touchpanel/backups/2026-06-22_failed_menu_contrast_attempt/
```

Auf keinen Fall auf dem failed attempt aufbauen.

## Test auf dem Pico

Nach Aenderungen nur die beiden Menue-Assets auf den Pico kopieren und resetten:

```bash
fw="/ABSOLUTER/PFAD/ZU/firmware/pico_touchpanel"
python3 -m mpremote connect /dev/cu.usbmodemXXXX cp "$fw/assets/menu_1.rle" :/assets/menu_1.rle
python3 -m mpremote connect /dev/cu.usbmodemXXXX cp "$fw/assets/menu_2.rle" :/assets/menu_2.rle
python3 -m mpremote connect /dev/cu.usbmodemXXXX reset
```

Falls der Pico wie zuletzt verbunden ist, ist der Port wahrscheinlich:

```text
/dev/cu.usbmodem21101
```

Bitte trotzdem vorher kurz pruefen.

## Akzeptanzkriterien

Die Ueberarbeitung ist nur erfolgreich, wenn auf dem echten Display gilt:

- Die Tonnenkoerper wirken sichtbar gefuellt.
- Die Tonnen heben sich klarer vom Button-Hintergrund ab.
- Die Buttonpositionen und Iconpositionen sind unveraendert.
- Die Wireframe-Optik bleibt erhalten.
- Das Gelb bleibt gut lesbar.
- Kein neuer Pixelart-/8-Bit-Look entsteht.
- Bei Lichteinstrahlung ist die Menuefunktion besser erkennbar als vorher.

## Ergebnis bitte dokumentieren

Am Ende kurz dokumentieren:

- Welche Dateien geaendert wurden.
- Welche Farb-/Palettewerte angepasst wurden.
- Welches Backup angelegt wurde.
- Ob auf dem Pico getestet wurde.
- Was auf dem echten Display beobachtet wurde.
