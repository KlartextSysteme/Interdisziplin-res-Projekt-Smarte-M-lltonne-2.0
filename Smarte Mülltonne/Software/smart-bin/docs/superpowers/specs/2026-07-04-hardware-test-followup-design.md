# Spec: Hardware-Test Follow-up (2026-07-04)

Sammel-Spec für die Fixes/Verbesserungen, die beim Hardware-Testlauf am
physischen Pico aufgefallen sind (Testkatalog `hardwaretestkatalog_2026-07-04.md`).
Sechs unabhängige Punkte über Backend, Frontend und Firmware.

## Kontext / Betroffene Komponenten

- **Backend** (`smart-bin/backend`): FastAPI, SQLAlchemy/SQLite.
- **Frontend** (`smart-bin/frontend`): Next.js Leitstand (`app/dashboard`).
- **Firmware** (`Quellcode/Client` = laufender Stack, `smart-bin/firmware/pico_touchpanel/ui.py` = laufende UI).

Reihenfolge: **A+B (Web, per pytest/Preview testbar)** → **C+D (Firmware Diagnose)**
→ **E+F (Hardware-Kalibrierung am Pico, gemeinsame Session)**.

---

## A — Security: Quittieren pro Meldung

**Problem:** Quittiert der Operator eine Meldung, verschwinden **alle** offenen
Meldungen derselben Tonne mit.

**Ursache:**
- `routers/security.py:68` `resolve_events(bin_id)` setzt **alle** offenen Events
  der Tonne auf `resolved=True`.
- `SecurityPanel.tsx:78` ruft `onResolve(e.bin_id)` — also pro Tonne, nicht pro Event.

**Design:**
- Backend: neuer Endpoint `POST /security/events/{event_id}/resolve` → setzt genau
  dieses Event auf `resolved=True`; `404` wenn nicht gefunden. Rückgabe
  `{event_id, resolved: true}`.
- Der bestehende `POST /security/{bin_id}/resolve` bleibt erhalten (Bulk-Auflösung,
  z.B. bei Service/Entsperren), wird vom Button aber nicht mehr benutzt.
- Frontend: `SecurityPanel` Prop `onResolve(eventId: number)`, Button ruft
  `onResolve(e.id)`; Dashboard-Handler postet an den Event-Endpoint. Types anpassen.

**Betroffene Dateien:** `backend/routers/security.py`,
`frontend/app/dashboard/components/SecurityPanel.tsx`,
`frontend/app/dashboard/page.tsx`, `frontend/types` (Prop/Signatur).

**Akzeptanz / Test:** `backend/test_reports.py` erweitern: zwei Events auf Tonne 22
(hygiene + damage) anlegen, eines quittieren → das andere bleibt offen.

---

## B — Zeitzonen-Fix (Backend UTC-aware)

**Problem:** Im Leitstand angezeigte Zeiten liegen 2 h neben der lokalen Zeit (CEST).

**Ursache:** Timestamps werden als **naives UTC** ohne Zeitzonen-Kennung serialisiert
(z.B. `last_seen: "2026-07-04T13:30:29"`, kein `Z`). `security.py:31` speichert zwar
`datetime.now(timezone.utc)`, aber die SQLite-`DateTime`-Spalte legt naiv ab und
Pydantic/ORM gibt den Wert ohne Offset aus. Das Frontend
(`SecurityPanel.tsx:62` `new Date(e.timestamp).toLocaleString("de-DE")`)
interpretiert den offset-losen String als lokal → 2 h Versatz.

**Design (Backend UTC-aware):**
- Gemeinsamer Helper, der Zeitwerte als UTC-aware ISO-8601 mit `Z`/`+00:00` ausgibt.
- Anwenden auf die im Leitstand sichtbaren Zeitfelder: `SecurityEvent.timestamp`
  und `Bin.last_seen` — über Pydantic-Response-Schemas mit Field-Serializer
  (Endpoints geben aktuell rohe ORM-Objekte zurück; hier Response-Modelle einführen
  bzw. Serializer ergänzen).
- Frontend bleibt unverändert (`toLocaleString` konvertiert dann korrekt nach CEST).

**Betroffene Dateien:** `backend/routers/security.py`, `backend/routers/bins.py`
(bzw. das/die Schema-Modul(e)), ggf. neuer `backend/schemas`-Helper.

**Akzeptanz / Test:** Neuer Backend-Test: `GET /security/events` liefert
`timestamp`, der auf `Z`/`+00:00` endet; ein bekannter UTC-Wert erscheint nach
Frontend-Konvertierung als korrekte CEST-Zeit (manuell/Preview gegengeprüft).

---

## C — Diagnose-Panel: Zurück-Button

**Problem:** Der Zurück-Button im Diagnose-Panel funktioniert nicht/sehr schlecht —
obwohl er größer (vollflächig) ist als die anderen.

**Ursache:** **Kein** Trefferflächen-Problem. `ui.py:315` setzt
`self.buttons = [Button(0, 0, 320, 240, "confirm_back")]`, aber `handle_action()`
(`ui.py:117`–`139`) hat **keinen** Zweig für `"confirm_back"` → der Tap wird
ausgewertet, löst aber keine Aktion aus.

**Design:** Diagnose-Zurück-Button auf eine behandelte Aktion umstellen; Rücksprung
nach `SCREEN_MENU_2` (dort wird Diagnose gestartet, `ui.py:321`). Vollflächiger
Tap-to-back bleibt. Entweder eigenen Handler-Zweig ergänzen oder eine bestehende
behandelte Aktion (z.B. `menu_2`) verwenden.

**Betroffene Dateien:** `smart-bin/firmware/pico_touchpanel/ui.py`
(+ Repo-Konsistenz `Quellcode/Client/ui.py`, falls vorhanden).

**Akzeptanz:** Tippen auf das Diagnose-Panel führt zuverlässig zurück ins Menü.

---

## D — Diagnose-Panel: Live-Werte (Füllstand %, Hindernis cm)

**Problem:** Das Diagnose-Panel zeigt keine dynamischen Werte; die Daten sind im
UI-Objekt vorhanden, werden aber nicht gerendert.

**Ursache:** `draw_diagnose()` (`ui.py:310`) zeichnet nur ein statisches Asset
(`diagnose_ok`/`diagnose_alert`). `obstacle_cm` (`ui.py:58`, gesetzt via
`set_status` `ui.py:83`) und `fill_level` werden dort nicht ausgegeben.

**Design:**
- `draw_diagnose()` überlagert das Basisbild mit zwei Textwerten: **Füllstand %**
  und **Hindernis cm** an definierten Positionen (Layout im Plan festlegen).
- Live-Refresh: in `tick()` bei `screen == SCREEN_DIAGNOSE` die beiden Felder neu
  zeichnen, wenn sich `fill_level`/`obstacle_cm` seit dem letzten Frame geändert
  haben — partielles Repaint (Rechteck hinter dem Text neu füllen, dann Text),
  analog `draw_fill_overlay()` (`ui.py:261`), kein Vollbild-Flackern.
- Feed-Kette verifizieren: Controller (`global_controller_test.py`) muss
  `obstacle_cm` und `fill_level` regelmäßig via `set_status` an die UI liefern.

**Betroffene Dateien:** `smart-bin/firmware/pico_touchpanel/ui.py`,
ggf. `Quellcode/Client/global_controller_test.py` (Feed).

**Akzeptanz:** Bei geöffnetem Diagnose-Panel ändern sich Füllstand % und Hindernis cm
sichtbar, wenn sich die realen Sensorwerte ändern.

---

## E — Touch: 5-Punkt-Neukalibrierung

**Problem:** Touch-Treffer sitzen leicht **unter** den Buttons; Touch-Qualität
insgesamt schlecht.

**Ursache:** Kalibrierwerte (`config.py` `TOUCH_X/Y_MIN/MAX`, `SWAP/INVERT`) leicht
daneben → systematischer Y-Versatz. `read_raw()` (`touch.py`) macht eine
Einzelmessung ohne Mittelung (nicht Teil dieses Fixes — bewusst außen vor gelassen).

**Design (Hardware-in-the-loop, nur Neukalibrierung):**
- `touch_calibrate.py` per USB auf dem Pico laufen lassen (5 Zielkreuze:
  TOP_LEFT, TOP_RIGHT, BOTTOM_RIGHT, BOTTOM_LEFT, CENTER).
- Operator tippt die Kreuze; Rohwerte (`RESULT`-Zeilen) seriell mitlesen.
- Daraus neue `TOUCH_X_MIN/MAX`, `TOUCH_Y_MIN/MAX` berechnen; `SWAP_XY`/`INVERT_*`
  gegenprüfen. In `config.py` schreiben und reflashen.

**Betroffene Dateien:** `Quellcode/Client/config.py` (Kalibrierkonstanten).

**Akzeptanz:** Touch-Treffer decken sich mit den sichtbaren Buttons (kein
„sitzt drunter"); alle Menü-/PIN-Buttons zuverlässig bedienbar.

**Hinweis:** Erfordert USB + Operator am Panel. Fällt-back auf Offset-Korrektur/
Mehrfachmessung nur, falls die reine Neukalibrierung das Problem nicht löst
(dann Nachtrag im Spec).

---

## F — Party-Modus: Endlage = Startlage (zeitbasiert kalibriert)

**Problem:** Party-Modus dreht, endet aber nicht in der Startorientierung.

**Ursache:** `_logic_party()` (`global_controller_test.py:558`) dreht **open-loop
zeitbasiert**: PWM-Spin bei `party_speed=65` für `party_duration_ms`, berechnet aus
`steps_to_ms(rotation_steps, party_speed)` (`:253`) mit
`steps_to_ms = steps*1000/freq` (`steppermotor.py:188`). Die Step-Rechnung
(`rotation_steps = 2*44000*party_full_rotations` = N volle 360°-Drehungen) ist
korrekt, aber die zeitbasierte Ausführung zählt keine echten Schritte → Anlauf-
Rampe und Schrittverluste bei Tempo 65 lassen die Endlage driften.

**Design (zeitbasiert kalibrieren, kein Umbau auf Schrittzählung):**
- Logik bleibt: N volle Umdrehungen, `party_duration_ms` aus `steps_to_ms`.
- Am realen Aufbau `party_speed` und die 180°-Konstante (`turn_home_180_steps=44000`)
  einmessen, bis N Drehungen sauber am Start landen (ggf. `party_full_rotations`/
  Tempo anpassen, um Rampen-Drift zu minimieren).
- Konstanten in `global_controller_test.py` festschreiben.

**Betroffene Dateien:** `Quellcode/Client/global_controller_test.py`
(`party_speed`, `party_full_rotations`, `turn_home_180_steps`).

**Akzeptanz:** Nach Ablauf der Party-Sequenz zeigt die Tonne wieder in
Startrichtung (Rest-Drift innerhalb weniger Grad akzeptabel, open-loop).

---

## Nicht im Scope (YAGNI)

- Touch: Offset-Term, Mehrfachmessung/Entprellung, größere Hitboxen (nur falls
  Neukalibrierung E nicht reicht).
- Party: echter Umbau auf schrittgenaues Pulsen (`rotate_steps`).
- Füllstand-Sensor C8 / T2 (Sensor noch nicht verbaut) — separater Vorgang.
- Motor-Pin-Swap-Fix aus T1 ist bereits umgesetzt/geflasht (uncommitted), nicht Teil
  dieses Specs.
