# Hardware-Test Follow-up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die beim Hardware-Testlauf 2026-07-04 gefundenen Fixes umsetzen: Security-Quittieren pro Meldung, Zeitzonen-Anzeige, Diagnose-Panel-Live-Werte, Touch-Neukalibrierung und Party-Modus-Endlage.

**Architecture:** Drei Schichten. Backend (FastAPI/SQLAlchemy) + Frontend (Next.js Leitstand) sind per pytest/Preview testbar. Firmware (MicroPython auf Pico) wird per `mpremote` geflasht und am Gerät über Serial/Bridge-Log verifiziert. Reihenfolge: Web zuerst (Task 1–3), dann Firmware-Code (Task 4), dann Hardware-Kalibrierung (Task 5–6).

**Tech Stack:** Python 3 / FastAPI / SQLAlchemy / Pydantic v2 / pytest 9; TypeScript / Next.js / React; MicroPython / mpremote / pyserial.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-04-hardware-test-followup-design.md`.
- Pico-Serial-Port: `/dev/cu.usbmodem114301`. Flashen via `mpremote connect port:$DEV fs cp …`.
- Serial nicht-invasiv per system-`python3` (pyserial 3.5); **niemals** `mpremote repl`/`fs cat` während laufender Firmware. Nach `reset` ~1,5 s warten.
- Laufende UI = `Flottenmanagement/firmware/pico_touchpanel/ui.py`. Laufender Controller = `Quellcode/Client/*`.
- **Linien-Regler-Werte NICHT hochdrehen** (Regressionshistorie): `base_speed≈45–60, max_freq=4500, max_correction=60, kp=32`.
- **Motor-Pins nicht anfassen** (T1-Fix bereits geflasht): links `DIR13/STEP8/EN9`, rechts `DIR10/STEP11/EN12`.
- Backend-Tests: aus `Flottenmanagement/backend/` mit `.venv/bin/python -m pytest`.
- Branch: `hardware-test-followup`.

---

### Task 1: Backend — Quittieren pro Event (Punkt A)

**Files:**
- Modify: `Flottenmanagement/backend/routers/security.py` (nach `resolve_events`, ~Zeile 74)
- Test: `Flottenmanagement/backend/test_reports.py` (neue Testfunktionen anhängen)

**Interfaces:**
- Produces: `POST /security/events/{event_id}/resolve` → `{"event_id": int, "resolved": true}`; `404` wenn Event nicht existiert. Setzt nur dieses eine Event auf `resolved=True`.
- Der bestehende `POST /security/{bin_id}/resolve` bleibt unverändert (Bulk).

- [ ] **Step 1: Failing tests schreiben** — an `Flottenmanagement/backend/test_reports.py` anhängen:

```python
def test_resolve_single_event_leaves_others():
    a = client.post("/security/events", json={"bin_id": 22, "event_type": "hygiene_report"}).json()
    b = client.post("/security/events", json={"bin_id": 22, "event_type": "damage_report"}).json()

    r = client.post(f"/security/events/{a['id']}/resolve")
    assert r.status_code == 200
    assert r.json() == {"event_id": a["id"], "resolved": True}

    open_ids = [e["id"] for e in client.get("/security/events").json()]
    assert a["id"] not in open_ids          # quittiertes Event weg
    assert b["id"] in open_ids              # anderes Event derselben Tonne bleibt

    client.post(f"/security/events/{b['id']}/resolve")  # cleanup


def test_resolve_unknown_event_returns_404():
    r = client.post("/security/events/99999999/resolve")
    assert r.status_code == 404
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag prüfen**

Run: `cd "Flottenmanagement/backend" && .venv/bin/python -m pytest test_reports.py -q`
Expected: FAIL — `test_resolve_single_event_leaves_others` bekommt `404`/`405` auf den neuen Pfad; `test_resolve_unknown_event_returns_404` schlägt fehl (Route existiert noch nicht).

- [ ] **Step 3: Endpoint implementieren** — in `Flottenmanagement/backend/routers/security.py` direkt hinter `resolve_events` (nach ~Zeile 74) einfügen:

```python
@router.post("/events/{event_id}/resolve")
def resolve_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.resolved = True
    db.commit()
    return {"event_id": event_id, "resolved": True}
```

(`HTTPException` und `SecurityEvent` sind oben in der Datei bereits importiert.)

- [ ] **Step 4: Tests laufen lassen, grün prüfen**

Run: `cd "Flottenmanagement/backend" && .venv/bin/python -m pytest test_reports.py -q`
Expected: PASS (alle Tests, inkl. der alten).

- [ ] **Step 5: Commit**

```bash
git add "Smarte Mülltonne/Software/Flottenmanagement/backend/routers/security.py" "Smarte Mülltonne/Software/Flottenmanagement/backend/test_reports.py"
git commit -m "feat(security): resolve single event by id (leaves other events of same bin)"
```

---

### Task 2: Backend — UTC-aware Alert-Timestamp (Punkt B)

**Files:**
- Modify: `Flottenmanagement/backend/routers/ws.py` (Import + Helper + Alert-Serialisierung ~Zeile 61)
- Test: `Flottenmanagement/backend/test_reports.py` (neue Testfunktion)

**Interfaces:**
- Consumes: `_build_live_payload()` (bereits in `test_reports.py` importiert).
- Produces: `_build_live_payload()["alerts"][i]["timestamp"]` endet auf `"Z"` (UTC-aware ISO-8601).

- [ ] **Step 1: Failing test schreiben** — an `test_reports.py` anhängen:

```python
def test_alert_timestamp_is_utc_z():
    created = client.post("/security/events", json={"bin_id": 22, "event_type": "hygiene_report"}).json()
    payload = _build_live_payload()
    alert = next(a for a in payload["alerts"] if a["id"] == created["id"])
    assert alert["timestamp"].endswith("Z")
    assert "T" in alert["timestamp"]          # ISO-8601, kein Space-Separator
    client.post(f"/security/events/{created['id']}/resolve")  # cleanup
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag prüfen**

Run: `cd "Flottenmanagement/backend" && .venv/bin/python -m pytest test_reports.py::test_alert_timestamp_is_utc_z -q`
Expected: FAIL — aktuell ist `timestamp` z.B. `"2026-07-04 13:30:29.204788"` (Space, kein `Z`).

- [ ] **Step 3: Helper + Serialisierung anpassen** — in `Flottenmanagement/backend/routers/ws.py`:

Import oben ergänzen (zu den bestehenden Imports):

```python
from datetime import timezone
```

Helper direkt vor `_build_live_payload` (vor ~Zeile 39) einfügen:

```python
def _iso_utc(value):
    """Naiv gespeicherte UTC-Zeit -> ISO-8601 mit Z. None bleibt None."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
```

Alert-Zeile (~61) von:

```python
                {"id": e.id, "bin_id": e.bin_id, "event_type": e.event_type, "timestamp": str(e.timestamp)}
```

ändern zu:

```python
                {"id": e.id, "bin_id": e.bin_id, "event_type": e.event_type, "timestamp": _iso_utc(e.timestamp)}
```

(`Bin.last_seen` in `ws.py:56` bleibt unverändert — wird im UI nicht als Uhrzeit angezeigt.)

- [ ] **Step 4: Tests laufen lassen, grün prüfen**

Run: `cd "Flottenmanagement/backend" && .venv/bin/python -m pytest test_reports.py -q`
Expected: PASS (alle).

- [ ] **Step 5: Commit**

```bash
git add "Smarte Mülltonne/Software/Flottenmanagement/backend/routers/ws.py" "Smarte Mülltonne/Software/Flottenmanagement/backend/test_reports.py"
git commit -m "fix(ws): alert timestamp als UTC-aware ISO (Z) -> Leitstand zeigt korrekte Ortszeit"
```

---

### Task 3: Frontend — Quittieren pro Event-id verdrahten (Punkt A)

**Files:**
- Modify: `Flottenmanagement/frontend/lib/api.ts` (neue Funktion bei den Security-Calls, ~Zeile 121)
- Modify: `Flottenmanagement/frontend/app/dashboard/components/SecurityPanel.tsx` (Props + Button, Zeilen 9, 78)
- Modify: `Flottenmanagement/frontend/app/dashboard/page.tsx` (Import Zeile 15 + `handleResolve` Zeile 116)

**Interfaces:**
- Consumes: Backend `POST /security/events/{event_id}/resolve` (Task 1); Event-Feld `e.id` (SecurityEvent-Type).
- Produces: `resolveAlert(eventId: number)`; `SecurityPanel`-Prop `onResolve: (eventId: number) => void`.

- [ ] **Step 1: API-Funktion ergänzen** — in `Flottenmanagement/frontend/lib/api.ts` direkt nach `resolveAlerts` (~Zeile 122) einfügen:

```ts
export const resolveAlert = (eventId: number) =>
  post(`/security/events/${eventId}/resolve`);
```

- [ ] **Step 2: SecurityPanel auf Event-id umstellen** — in `SecurityPanel.tsx`:

Props (Zeile 9) von `onResolve: (binId: number) => void;` zu:

```tsx
  onResolve: (eventId: number) => void;
```

Button-`onClick` (Zeile 78) von `onClick={() => onResolve(e.bin_id)}` zu:

```tsx
                onClick={() => onResolve(e.id)}
```

- [ ] **Step 3: page.tsx-Handler umstellen** — in `app/dashboard/page.tsx`:

Import (Zeile 15) `resolveAlerts` ersetzen durch `resolveAlert`.

`handleResolve` (Zeile 116–118) von:

```tsx
  async function handleResolve(binId: number) {
    await resolveAlerts(binId);
  }
```

zu:

```tsx
  async function handleResolve(eventId: number) {
    await resolveAlert(eventId);
  }
```

- [ ] **Step 4: Typecheck / Build**

Run: `cd "Flottenmanagement/frontend" && npx tsc --noEmit`
Expected: keine Fehler.

- [ ] **Step 5: Live verifizieren** (Backend + Bridge + Pico laufen)

Preview-Server (Port 3000) starten/neuladen, `http://localhost:3000/dashboard` öffnen. Zwei Meldungen auf Tonne 22 erzeugen (Panel HYGIENE + SCHADEN, oder `curl`):
```bash
curl -s -XPOST http://127.0.0.1:8000/security/events -H 'Content-Type: application/json' -d '{"bin_id":22,"event_type":"hygiene_report"}'
curl -s -XPOST http://127.0.0.1:8000/security/events -H 'Content-Type: application/json' -d '{"bin_id":22,"event_type":"damage_report"}'
```
Im Security-Panel EINE Meldung „Quittieren" → die **andere bleibt** stehen. Zeitstempel zeigt korrekte **CEST**-Zeit (nicht 2 h daneben).

- [ ] **Step 6: Commit**

```bash
git add "Smarte Mülltonne/Software/Flottenmanagement/frontend/lib/api.ts" "Smarte Mülltonne/Software/Flottenmanagement/frontend/app/dashboard/components/SecurityPanel.tsx" "Smarte Mülltonne/Software/Flottenmanagement/frontend/app/dashboard/page.tsx"
git commit -m "feat(dashboard): Meldung einzeln quittieren (per Event-id)"
```

---

### Task 4: Firmware — Diagnose-Panel Live-Werte (Punkt D)

**Files:**
- Modify: `Flottenmanagement/firmware/pico_touchpanel/ui.py` (`__init__`, `set_status`, `tick`, `draw_diagnose`, neue `_draw_diag_values`)
- Modify: `Quellcode/Client/global_controller_test.py` (AT_HOME-Feed, ~Zeile 740–753)

**Interfaces:**
- Consumes: `self.d.text(text, x, y, color, scale, spacing)`, `self.d.fill_rect(x, y, w, h, color)` (display.py); `self.fill_level`, `self.obstacle_cm`; `self.obstacle_sensors.run_front(force=True) -> float|None`.
- Produces: Diagnose-Screen zeigt „FUELLSTAND nn%" und „HINDERNIS nn CM", live aktualisiert.

- [ ] **Step 1: State-Tracking + Feld-Zeichnung in `ui.py`**

In `TouchUi.__init__` (nach `self.obstacle_cm = None`, ~Zeile 58) ergänzen:

```python
        self._diag_last_fill = None
        self._diag_last_obstacle = None
```

Neue Methode einfügen (z.B. direkt nach `draw_fill_overlay`, ~Zeile 269):

```python
    def _draw_diag_values(self):
        # Zwei Textfelder unten links ueber dem Diagnose-Bild, partielles Repaint.
        fill_txt = ("FUELLSTAND " + str(self.fill_level) + "%") if self.fill_level is not None else "FUELLSTAND --"
        if self.obstacle_cm is None:
            obst_txt = "HINDERNIS --"
        else:
            obst_txt = "HINDERNIS " + str(int(self.obstacle_cm)) + " CM"
        # Hintergrundstreifen freiraeumen, dann Text
        self.d.fill_rect(8, 150, 230, 20, BIN_BODY)
        self.d.fill_rect(8, 172, 230, 20, BIN_BODY)
        self.d.text(fill_txt, 12, 152, BIN_LABEL, 2, 1)
        self.d.text(obst_txt, 12, 174, BIN_LABEL, 2, 1)
        self._diag_last_fill = self.fill_level
        self._diag_last_obstacle = self.obstacle_cm
```

- [ ] **Step 2: `draw_diagnose` zeichnet die Werte mit**

`draw_diagnose` (~Zeile 310) von:

```python
    def draw_diagnose(self):
        self.buttons = [Button(92, 188, 136, 46, "menu_2")]
        self.r.draw("diagnose_ok" if self.connected and self.line_ok else "diagnose_alert")
```

zu:

```python
    def draw_diagnose(self):
        self.buttons = [Button(92, 188, 136, 46, "menu_2")]
        self.r.draw("diagnose_ok" if self.connected and self.line_ok else "diagnose_alert")
        self._draw_diag_values()
```

- [ ] **Step 3: Live-Refresh in `tick`, Voll-Redraw von Diagnose vermeiden**

In `set_status` (~Zeile 93) die Auto-Draw-Bedingung von:

```python
        if self.screen in (SCREEN_STATUS, SCREEN_DIAGNOSE):
            self.draw()
```

ändern zu (Diagnose wird nicht mehr voll neu gemalt -> kein Flackern; Refresh macht `tick`):

```python
        if self.screen == SCREEN_STATUS:
            self.draw()
```

In `tick` (nach dem CONFIRM-Block, vor dem `return`/Ende der Methode, ~Zeile 104) ergänzen:

```python
        if self.screen == SCREEN_DIAGNOSE:
            if (self.fill_level != self._diag_last_fill
                    or self.obstacle_cm != self._diag_last_obstacle):
                self._draw_diag_values()
```

- [ ] **Step 4: Controller speist `obstacle_cm` im AT_HOME-Status mit** — in `Quellcode/Client/global_controller_test.py`, den AT_HOME-Feed (~Zeile 740–753). `fill_level`-Zeile ergänzen und Front-Distanz messen:

Von:

```python
        fill_level = self._read_fuellstand_for_status()

        if self.touchpanel is not None:
            if fill_level is None:
                self.touchpanel.set_status(
                    status_kind="full_home",
                    location="home",
                )
            else:
                self.touchpanel.set_status(
                    status_kind="full_home",
                    location="home",
                    fill_level=fill_level,
                )
```

zu:

```python
        fill_level = self._read_fuellstand_for_status()

        obstacle_cm = None
        if self.obstacle_sensors is not None:
            obstacle_cm = self.obstacle_sensors.run_front(force=True)

        if self.touchpanel is not None:
            if fill_level is None:
                self.touchpanel.set_status(
                    status_kind="full_home",
                    location="home",
                    obstacle_cm=obstacle_cm,
                )
            else:
                self.touchpanel.set_status(
                    status_kind="full_home",
                    location="home",
                    fill_level=fill_level,
                    obstacle_cm=obstacle_cm,
                )
```

- [ ] **Step 5: Syntax prüfen (AST-Parse auf dem Host)**

Run:
```bash
python3 -c "import ast; ast.parse(open('Smarte Mülltonne/Software/Flottenmanagement/firmware/pico_touchpanel/ui.py').read()); ast.parse(open('Smarte Mülltonne/Software/Quellcode/Client/global_controller_test.py').read()); print('parse OK')"
```
Expected: `parse OK`.

- [ ] **Step 6: Flashen + am Gerät verifizieren** (Pico per USB, `DEV=/dev/cu.usbmodem114301`)

```bash
DEV=/dev/cu.usbmodem114301
mpremote connect port:$DEV fs cp "Smarte Mülltonne/Software/Flottenmanagement/firmware/pico_touchpanel/ui.py" :ui.py
mpremote connect port:$DEV fs cp "Smarte Mülltonne/Software/Quellcode/Client/global_controller_test.py" :global_controller_test.py
mpremote connect port:$DEV reset
```
Am Panel: Menü → Diagnose öffnen. Erwartet: „FUELLSTAND nn%" und „HINDERNIS nn CM" sichtbar; Hand vor den Frontsensor → **Hindernis-cm ändert sich live**; Tonne füllen/leeren → **Füllstand-% ändert sich**. (Ohne verbauten Füllstand-Sensor zeigt Füllstand den zuletzt bekannten Wert bzw. `--`.)

- [ ] **Step 7: Commit**

```bash
git add "Smarte Mülltonne/Software/Flottenmanagement/firmware/pico_touchpanel/ui.py" "Smarte Mülltonne/Software/Quellcode/Client/global_controller_test.py"
git commit -m "feat(ui): Diagnose-Panel zeigt Fuellstand % und Hindernis cm live"
```

---

### Task 5: Hardware — Touch 5-Punkt-Neukalibrierung (Punkt E, inkl. Gegenprobe C)

**Files:**
- Modify: `Quellcode/Client/config.py` (`TOUCH_X_MIN/MAX`, `TOUCH_Y_MIN/MAX`, ggf. `SWAP/INVERT`)

**Interfaces:**
- Consumes: `Flottenmanagement/firmware/pico_touchpanel/touch_calibrate.py` (5-Punkt-Routine, gibt `RESULT`-Zeilen mit Rohwerten aus).
- Produces: aktualisierte Kalibrierkonstanten in `config.py`.

**Hinweis:** Hardware-in-the-loop — Pico per USB, Operator tippt die Kreuze. Kein Unit-Test.

- [ ] **Step 1: Kalibrier-Routine flashen + starten** (Firmware wird dabei gestoppt — ok)

```bash
DEV=/dev/cu.usbmodem114301
mpremote connect port:$DEV fs cp "Smarte Mülltonne/Software/Flottenmanagement/firmware/pico_touchpanel/touch_calibrate.py" :touch_calibrate.py
# im Hintergrund starten und Serial mitlesen; Operator tippt TOP_LEFT..CENTER
mpremote connect port:$DEV run "Smarte Mülltonne/Software/Flottenmanagement/firmware/pico_touchpanel/touch_calibrate.py" > /tmp/touch_cal.log 2>&1 &
```

- [ ] **Step 2: 5 Kreuze tippen, `RESULT`-Rohwerte sammeln**

Operator tippt in Reihenfolge TOP_LEFT, TOP_RIGHT, BOTTOM_RIGHT, BOTTOM_LEFT, CENTER. Danach `RESULT`-Zeilen aus `/tmp/touch_cal.log` lesen (Format `RESULT label target= tx ty mapped= x y raw= rx ry`).

- [ ] **Step 3: Neue Min/Max berechnen**

Aus den `raw_x`/`raw_y` der Eckpunkte die neuen `TOUCH_X_MIN/MAX`, `TOUCH_Y_MIN/MAX` bestimmen (min/max der Ecken je Achse, unter Berücksichtigung von `TOUCH_SWAP_XY`/`INVERT`). Prüfen, ob `SWAP/INVERT` noch stimmen (Zielkreuz vs. `mapped`-Richtung).

- [ ] **Step 4: `config.py` aktualisieren**

In `Quellcode/Client/config.py` die Konstanten `TOUCH_X_MIN`, `TOUCH_X_MAX`, `TOUCH_Y_MIN`, `TOUCH_Y_MAX` (und ggf. `TOUCH_SWAP_XY`/`TOUCH_INVERT_X`/`TOUCH_INVERT_Y`) auf die gemessenen Werte setzen.

- [ ] **Step 5: config flashen + reset**

```bash
DEV=/dev/cu.usbmodem114301
mpremote connect port:$DEV fs cp "Smarte Mülltonne/Software/Quellcode/Client/config.py" :config.py
mpremote connect port:$DEV reset
```

- [ ] **Step 6: Verifizieren (inkl. Gegenprobe Punkt C)**

Am Panel jeden Button testen: Treffer decken sich mit den Icons (kein „sitzt drunter"). **Speziell:** Menü → Diagnose öffnen → **Zurück-Button (unterster, `y=188…234`) trifft zuverlässig** → zurück ins Menü. Falls der Rand-Button trotz sauberer Kalibrierung zickt, Nachtrag: in `ui.py` `draw_diagnose` den Button höher/größer setzen (z.B. `Button(92, 176, 136, 52, "menu_2")`), flashen, erneut testen.

- [ ] **Step 7: Commit**

```bash
git add "Smarte Mülltonne/Software/Quellcode/Client/config.py"
git commit -m "fix(touch): 5-Punkt-Neukalibrierung -> Treffer decken sich mit Buttons"
```

---

### Task 6: Hardware — Party-Modus Endlage = Startlage (Punkt F)

**Files:**
- Modify: `Quellcode/Client/global_controller_test.py` (`party_speed`, `party_full_rotations`, ggf. `turn_home_180_steps`)

**Interfaces:**
- Consumes: `motors.steps_to_ms(steps, speed)`; `_logic_party` (zeitbasierter Spin).
- Produces: kalibrierte Party-Konstanten, Endlage ≈ Startlage.

**Hinweis:** Hardware-in-the-loop — Tonne im Leerlauf (`AT_HOME`), freier Drehraum. Kein Unit-Test.

- [ ] **Step 1: Ausgangslage markieren + Party auslösen**

Tonne AT_HOME, Startorientierung physisch markieren (Klebeband). Panel: PIN-Screen → `***` → OK. Sequenz laufen lassen, Enddrift gegen Marke messen.

- [ ] **Step 2: Kalibrieren** — in `global_controller_test.py` (~Zeile 197–199):

Stellschrauben (in kleinen Schritten, einzeln testen — Regel: Tempo behutsam):
- `party_full_rotations` = Anzahl voller 360°-Drehungen (aktuell `1`).
- `party_speed` (aktuell `65`) ggf. senken, um Anlauf-/Schrittverlust zu reduzieren.
- Falls konsistenter Rest-Offset: `turn_home_180_steps` (aktuell `44000`) feinjustieren, bis 2·N·steps sauber am Start landen.

Nach jeder Änderung: `global_controller_test.py` flashen (`mpremote … fs cp … :global_controller_test.py`), `reset`, erneut `***` auslösen, Enddrift messen.

- [ ] **Step 3: Verifizieren**

Nach Ablauf zeigt die Tonne wieder in Startrichtung (Rest-Drift innerhalb weniger Grad akzeptabel, open-loop). Buzzer-Jingle läuft während der Drehung.

- [ ] **Step 4: Commit**

```bash
git add "Smarte Mülltonne/Software/Quellcode/Client/global_controller_test.py"
git commit -m "fix(party): Endlage = Startlage (party-Konstanten am Aufbau kalibriert)"
```

---

## Self-Review

- **Spec-Abdeckung:** A→Task 1+3; B→Task 2; C→in E aufgegangen (Task 5 Step 6); D→Task 4; E→Task 5; F→Task 6. ✔
- **Platzhalter:** keine offenen TODOs/„später". Hardware-Kalibrier-Rechenschritte (Task 5 Step 3, Task 6 Step 2) sind messwertabhängig und bewusst als Prozedur formuliert. ✔
- **Typ-/Namenskonsistenz:** `resolveAlert(eventId)` (Task 3) ↔ `POST /security/events/{event_id}/resolve` (Task 1); `onResolve(eventId)` konsistent; `_draw_diag_values`/`_diag_last_fill`/`_diag_last_obstacle` in Task 4 durchgängig. ✔
