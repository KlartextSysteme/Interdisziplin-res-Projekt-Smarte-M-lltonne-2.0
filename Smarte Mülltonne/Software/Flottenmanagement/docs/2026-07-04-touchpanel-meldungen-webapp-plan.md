# Touchpanel-Meldungen → Web-App: Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Panel-Buttons „SCHADEN"/„HYGIENE" lösen Meldungen aus, die live im Leitstand erscheinen (mit Icon) und dort erledigt werden; das Panel zeigt „Meldung gesendet".

**Architecture:** Touchpanel → Controller `_bridge_send("REPORT:*")` → TCP-Bridge parst und `POST /security/events` → `SecurityEvent(event_type=damage_report|hygiene_report)` → bestehender WS-Broadcast → bestehende Frontend-Anzeige (Wrench/Sparkles) + Erledigen.

**Tech Stack:** MicroPython (Pico), Python/asyncio + httpx (Bridge), FastAPI + SQLAlchemy (Backend), Next.js/React (Frontend, keine Änderung), Pillow (WF1-Asset-Encoder).

Spec: `Flottenmanagement/docs/2026-07-04-touchpanel-meldungen-webapp-design.md`

## Global Constraints

- event_type-Werte exakt: **`damage_report`**, **`hygiene_report`** (Frontend kennt sie schon).
- Bridge-Pico-Zeilen exakt: **`REPORT:DAMAGE`**, **`REPORT:HYGIENE`**.
- `bin_id` = `self.state.bin_id` der Bridge (Demo = 22). Nicht hardcoden.
- Firmware läuft mit der **firmware-`ui.py`** auf dem Pico; `Quellcode/Client/ui.py` parallel pflegen (Repo-Konsistenz).
- Keine DB-Migration (SecurityEvent.event_type ist freier String).
- Commits pro Task. Arbeitsverzeichnis: `Smarte Mülltonne/Software`.
- pytest liegt in `Flottenmanagement/backend/.venv/bin/pytest`.

---

### Task 1: Bridge parst REPORT und meldet ans Backend

**Files:**
- Modify: `Flottenmanagement/bridge/tcp_bridge.py` (`_handle_pico_line`, neue Methode `_post_report`)
- Test: `Flottenmanagement/bridge/test_report.py`

**Interfaces:**
- Consumes: `PicoBridge(backend_url, bin_id, poll_interval_s)`, `self.client` (httpx.AsyncClient), `self.state.bin_id`, `self.backend_url`.
- Produces: `PicoBridge._post_report(event_type: str)`; `_handle_pico_line` erkennt `REPORT:<DAMAGE|HYGIENE>`.

- [ ] **Step 1: Failing test schreiben** — `Flottenmanagement/bridge/test_report.py`

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock
from tcp_bridge import PicoBridge  # gleiches Verzeichnis


def _bridge_with_mock_client():
    bridge = PicoBridge(backend_url="http://test", bin_id=22, poll_interval_s=1.0)
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    bridge.client = MagicMock()
    bridge.client.post = AsyncMock(return_value=resp)
    return bridge


def test_report_hygiene_posts_hygiene_report():
    bridge = _bridge_with_mock_client()
    asyncio.run(bridge._handle_pico_line("REPORT:HYGIENE", MagicMock()))
    bridge.client.post.assert_awaited_once()
    args, kwargs = bridge.client.post.call_args
    assert args[0].endswith("/security/events")
    assert kwargs["json"] == {"bin_id": 22, "event_type": "hygiene_report"}


def test_report_damage_posts_damage_report():
    bridge = _bridge_with_mock_client()
    asyncio.run(bridge._handle_pico_line("REPORT:DAMAGE", MagicMock()))
    args, kwargs = bridge.client.post.call_args
    assert kwargs["json"] == {"bin_id": 22, "event_type": "damage_report"}


def test_unknown_report_kind_does_not_post():
    bridge = _bridge_with_mock_client()
    asyncio.run(bridge._handle_pico_line("REPORT:FOO", MagicMock()))
    bridge.client.post.assert_not_awaited()
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag bestätigen**

Run: `cd "Smarte Mülltonne/Software/Flottenmanagement/bridge" && ../backend/.venv/bin/pytest test_report.py -v`
Expected: FAIL (REPORT wird noch nicht geparst → `post` nicht aufgerufen / KeyError).

- [ ] **Step 3: Implementierung** — in `tcp_bridge.py` `_handle_pico_line`, direkt vor der abschließenden `LOGGER.debug("ignored pico line: %s", line)`-Zeile einfügen:

```python
        if line.startswith("REPORT:"):
            kind = line.split(":", 1)[1].strip().upper()
            event_type = {"DAMAGE": "damage_report", "HYGIENE": "hygiene_report"}.get(kind)
            if event_type is None:
                LOGGER.warning("unknown report kind: %s", kind)
                return
            await self._post_report(event_type)
            return
```

Und als neue Methode (z. B. direkt nach `_post_telemetry`):

```python
    async def _post_report(self, event_type: str) -> None:
        resp = await self.client.post(
            f"{self.backend_url}/security/events",
            json={"bin_id": self.state.bin_id, "event_type": event_type},
        )
        resp.raise_for_status()
        LOGGER.info("report %s -> backend for bin %s", event_type, self.state.bin_id)
```

- [ ] **Step 4: Tests grün**

Run: `cd "Smarte Mülltonne/Software/Flottenmanagement/bridge" && ../backend/.venv/bin/pytest test_report.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add "Smarte Mülltonne/Software/Flottenmanagement/bridge/tcp_bridge.py" "Smarte Mülltonne/Software/Flottenmanagement/bridge/test_report.py"
git commit -m "Bridge: REPORT:DAMAGE/HYGIENE -> POST /security/events"
```

---

### Task 2: Backend-Contract-Test (Meldungen fließen in Events + WS)

**Files:**
- Test: `Flottenmanagement/backend/test_reports.py`

**Interfaces:**
- Consumes: FastAPI `app` (`main.app`), Routen `POST/GET /security/events`, `POST /security/{bin_id}/resolve`, `routers.ws._build_live_payload`.
- Produces: nichts (Regressionsschutz, sichert die vom Frontend erwarteten event_type-Keys backend-seitig).

- [ ] **Step 1: Test schreiben** — `Flottenmanagement/backend/test_reports.py`

```python
from fastapi.testclient import TestClient
from main import app
from routers.ws import _build_live_payload

client = TestClient(app)


def test_report_event_flows_into_events_and_ws():
    r = client.post("/security/events", json={"bin_id": 22, "event_type": "hygiene_report"})
    assert r.status_code == 200
    assert r.json()["event_type"] == "hygiene_report"

    open_events = client.get("/security/events").json()
    assert any(e["event_type"] == "hygiene_report" and e["bin_id"] == 22 for e in open_events)

    payload = _build_live_payload()
    assert any(a["event_type"] == "hygiene_report" for a in payload["alerts"])

    # Cleanup: Demo-DB nicht mit Test-Events verschmutzen
    client.post("/security/22/resolve")
    assert all(a["event_type"] != "hygiene_report" for a in _build_live_payload()["alerts"])
```

- [ ] **Step 2: Test laufen lassen (soll direkt grün sein — Backend kann das schon)**

Run: `cd "Smarte Mülltonne/Software/Flottenmanagement/backend" && .venv/bin/pytest test_reports.py -v`
Expected: PASS. Falls FAIL → Backend-Bug, hier fixen (nicht erwartet).

- [ ] **Step 3: Commit**

```bash
git add "Smarte Mülltonne/Software/Flottenmanagement/backend/test_reports.py"
git commit -m "Backend: Contract-Test fuer damage_report/hygiene_report Events"
```

---

### Task 3: Controller reagiert auf report_damage/report_hygiene

**Files:**
- Modify: `Smarte Mülltonne/Software/Quellcode/Client/global_controller_test.py` (`handle_touch_action`)

**Interfaces:**
- Consumes: `self._bridge_send(line: str)` (existiert, fehlertolerant).
- Produces: `handle_touch_action("report_damage"|"report_hygiene")` sendet `REPORT:DAMAGE`/`REPORT:HYGIENE`.

- [ ] **Step 1: Implementierung** — in `handle_touch_action`, nach dem `goto_home`-Block, vor `shutdown`:

```python
        if action == "report_damage":
            self._bridge_send("REPORT:DAMAGE")
            return

        if action == "report_hygiene":
            self._bridge_send("REPORT:HYGIENE")
            return
```

- [ ] **Step 2: Syntax-Check (MicroPython nicht lokal ausführbar, daher py_compile)**

Run: `cd "Smarte Mülltonne/Software" && Flottenmanagement/backend/.venv/bin/python -m py_compile Quellcode/Client/global_controller_test.py && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add "Smarte Mülltonne/Software/Quellcode/Client/global_controller_test.py"
git commit -m "Controller: report_damage/report_hygiene -> _bridge_send(REPORT:*)"
```

*(End-to-End-Verifikation über den Pico erfolgt in Task 6.)*

---

### Task 4: WF1-Encoder + Asset „confirm_report.rle" (Meldung gesendet)

**Files:**
- Create: `Flottenmanagement/firmware/pico_touchpanel/tools/png_to_wf1.py` (Encoder + Decoder-Helfer)
- Create: `Flottenmanagement/firmware/pico_touchpanel/tools/test_wf1_roundtrip.py`
- Create: `Flottenmanagement/firmware/pico_touchpanel/assets/confirm_report.rle`
- Create: `Quellcode/Client/assets/confirm_report.rle` (Kopie, Repo-Konsistenz)

**Interfaces:**
- Consumes: Pillow (`PIL.Image`), WF1-Format (Magic `WF1`, w/h big-endian, palette_len 1B, Palette 2B RGB565, pro Zeile `row_len` 2B + `(run 1B, index 1B)`-Paare, run ≤255).
- Produces: `encode_png_to_wf1(png_path, rle_path)`, `decode_wf1(rle_path) -> (w, h, list[list[(r,g,b)]])`.

- [ ] **Step 1: Pillow sicherstellen**

Run: `cd "Smarte Mülltonne/Software/Flottenmanagement/backend" && .venv/bin/python -c "import PIL; print(PIL.__version__)" || .venv/bin/pip install Pillow`
Expected: eine Versionsnummer.

- [ ] **Step 2: Encoder + Decoder schreiben** — `tools/png_to_wf1.py`

```python
"""PNG -> WF1 (Touchpanel-RLE) Encoder + Decoder.
WF1: b'WF1' | w(2B BE) | h(2B BE) | palette_len(1B) | palette(palette_len * 2B RGB565)
     | pro Zeile: row_len(2B BE) + row_len Bytes als (run 1B, palette_index 1B)-Paare.
run 1..255; sum(runs) je Zeile == w; palette <= 256 Farben (RGB565).
"""
from PIL import Image


def _rgb_to_565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def _565_to_rgb(c):
    r = (c >> 11) & 0x1F
    g = (c >> 5) & 0x3F
    b = c & 0x1F
    return (r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)


def encode_png_to_wf1(png_path, rle_path):
    img = Image.open(png_path).convert("RGB")
    w, h = img.size
    px = img.load()

    # 565-Werte je Pixel + Palette (max 256 via Pillow-Quantisierung, falls noetig)
    cells = [[_rgb_to_565(*px[x, y]) for x in range(w)] for y in range(h)]
    uniq = sorted({c for row in cells for c in row})
    if len(uniq) > 256:
        q = img.convert("P", palette=Image.ADAPTIVE, colors=256).convert("RGB")
        qpx = q.load()
        cells = [[_rgb_to_565(*qpx[x, y]) for x in range(w)] for y in range(h)]
        uniq = sorted({c for row in cells for c in row})
    index_of = {c: i for i, c in enumerate(uniq)}

    out = bytearray(b"WF1")
    out += w.to_bytes(2, "big") + h.to_bytes(2, "big")
    out += bytes([len(uniq)])
    for c in uniq:
        out += c.to_bytes(2, "big")

    for y in range(h):
        row = bytearray()
        x = 0
        while x < w:
            c = cells[y][x]
            run = 1
            while x + run < w and cells[y][x + run] == c and run < 255:
                run += 1
            row += bytes([run, index_of[c]])
            x += run
        out += len(row).to_bytes(2, "big") + row

    with open(rle_path, "wb") as f:
        f.write(out)


def decode_wf1(rle_path):
    with open(rle_path, "rb") as f:
        assert f.read(3) == b"WF1"
        w = int.from_bytes(f.read(2), "big")
        h = int.from_bytes(f.read(2), "big")
        n = f.read(1)[0]
        pal = [_565_to_rgb(int.from_bytes(f.read(2), "big")) for _ in range(n)]
        rows = []
        for _ in range(h):
            row_len = int.from_bytes(f.read(2), "big")
            data = f.read(row_len)
            row = []
            for i in range(0, row_len, 2):
                row += [pal[data[i + 1]]] * data[i]
            rows.append(row)
    return w, h, rows
```

- [ ] **Step 3: Round-Trip-Test schreiben** — `tools/test_wf1_roundtrip.py`

```python
import os, tempfile
from PIL import Image
from png_to_wf1 import encode_png_to_wf1, decode_wf1


def test_roundtrip_matches_source_in_565():
    tmp = tempfile.mkdtemp()
    src = os.path.join(tmp, "src.png")
    rle = os.path.join(tmp, "out.rle")
    img = Image.new("RGB", (12, 5), (30, 30, 34))
    for x in range(12):
        img.putpixel((x, 2), (242, 201, 76))   # gelbe Linie
    img.putpixel((0, 0), (248, 250, 252))       # ein heller Pixel
    img.save(src)

    encode_png_to_wf1(src, rle)
    w, h, rows = decode_wf1(rle)
    assert (w, h) == (12, 5)

    # Quelle in RGB565 gerundet == decodiert (verlustfrei ueber 565)
    from png_to_wf1 import _rgb_to_565, _565_to_rgb
    spx = img.load()
    for y in range(h):
        for x in range(w):
            assert rows[y][x] == _565_to_rgb(_rgb_to_565(*spx[x, y]))
```

- [ ] **Step 4: Round-Trip-Test laufen lassen**

Run: `cd "Smarte Mülltonne/Software/Flottenmanagement/firmware/pico_touchpanel/tools" && ../../../backend/.venv/bin/pytest test_wf1_roundtrip.py -v`
Expected: PASS. (Sichert, dass der Encoder exakt zum `wireframe.py`-Decoder passt.)

- [ ] **Step 5: Referenzstil aus `confirm_generic.rle` ziehen**

Run: `cd "Smarte Mülltonne/Software/Flottenmanagement/firmware/pico_touchpanel/tools" && ../../../backend/.venv/bin/python -c "from png_to_wf1 import decode_wf1; from PIL import Image; w,h,rows=decode_wf1('../assets/confirm_generic.rle'); img=Image.new('RGB',(w,h)); [img.putpixel((x,y),rows[y][x]) for y in range(h) for x in range(w)]; img.save('confirm_generic_ref.png'); print(w,h)"`
Expected: `320 240` + Datei `confirm_generic_ref.png` (Referenz: Hintergrundfarben, gelbes Häkchen-Quadrat, Schriftposition/-farbe von „Auswahl bestätigt").

- [ ] **Step 6: „Meldung gesendet"-PNG rendern** — `tools/render_confirm_report.py`
  (Farben/Positionen ggf. an `confirm_generic_ref.png` aus Step 5 angleichen):

```python
from PIL import Image, ImageDraw, ImageFont

W, H = 320, 240
BG_TOP, BG_BOT = (58, 58, 62), (42, 42, 46)   # dunkler Verlauf (an Referenz pruefen)
YELLOW, DARK, WHITE = (242, 201, 76), (45, 45, 48), (248, 250, 252)

img = Image.new("RGB", (W, H))
for y in range(H):
    t = y / (H - 1)
    img.paste(tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3)), (0, y, W, y + 1))
d = ImageDraw.Draw(img)

sq, sy = 96, 44
sx = (W - sq) // 2
d.rounded_rectangle([sx, sy, sx + sq, sy + sq], radius=22, fill=YELLOW)
d.line([(sx + 26, sy + 50), (sx + 42, sy + 66), (sx + 72, sy + 30)], fill=DARK, width=10, joint="curve")

try:
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)   # falls confirm_generic-Font bekannt: den nehmen
except OSError:
    font = ImageFont.load_default()
text = "Meldung gesendet"
tw = d.textlength(text, font=font)
d.text(((W - tw) // 2, 168), text, fill=WHITE, font=font)

img.save("confirm_report.png")
print("OK")
```

Run: `cd "Smarte Mülltonne/Software/Flottenmanagement/firmware/pico_touchpanel/tools" && ../../../backend/.venv/bin/python render_confirm_report.py`
Expected: `OK` + `confirm_report.png`. **Visuell** gegen `confirm_generic_ref.png` + Operator-Wireframe prüfen und Farben/Positionen/Font iterieren, bis die Anmutung dem „Auswahl bestätigt"-Screen entspricht.

- [ ] **Step 7: Encodieren + in beide assets/ ablegen**

```bash
cd "Smarte Mülltonne/Software/Flottenmanagement/firmware/pico_touchpanel/tools"
../../../backend/.venv/bin/python -c "from png_to_wf1 import encode_png_to_wf1; encode_png_to_wf1('confirm_report.png','../assets/confirm_report.rle')"
cp ../assets/confirm_report.rle "../../../../Quellcode/Client/assets/confirm_report.rle"
ls -l ../assets/confirm_report.rle
```
Expected: `confirm_report.rle` in beiden assets/-Ordnern.

- [ ] **Step 8: Commit**

```bash
cd "Smarte Mülltonne/Software"
git add Flottenmanagement/firmware/pico_touchpanel/tools/ Flottenmanagement/firmware/pico_touchpanel/assets/confirm_report.rle Quellcode/Client/assets/confirm_report.rle
git commit -m "Touchpanel-Asset: confirm_report.rle (Meldung gesendet) + WF1-Encoder"
```

---

### Task 5: ui.py zeigt „Meldung gesendet" bei report_*

**Files:**
- Modify: `Flottenmanagement/firmware/pico_touchpanel/ui.py` (`_perform_action`)
- Modify: `Quellcode/Client/ui.py` (`_perform_action`)

**Interfaces:**
- Consumes: Asset `confirm_report` (Task 4), `show_confirm(asset)`.
- Produces: report_* → `show_confirm("confirm_report")`.

- [ ] **Step 1: firmware-ui.py anpassen** — in `_perform_action`, im if/elif-Block der Asset-Wahl, vor dem `else: asset = "confirm_generic"`:

```python
        elif action in ("report_damage", "report_hygiene"):
            asset = "confirm_report"
```

- [ ] **Step 2: Gleiche Änderung in `Quellcode/Client/ui.py`** (identischer Block).

- [ ] **Step 3: Syntax-Check beider Dateien**

Run: `cd "Smarte Mülltonne/Software" && Flottenmanagement/backend/.venv/bin/python -m py_compile Flottenmanagement/firmware/pico_touchpanel/ui.py Quellcode/Client/ui.py && echo OK`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add "Smarte Mülltonne/Software/Flottenmanagement/firmware/pico_touchpanel/ui.py" "Smarte Mülltonne/Software/Quellcode/Client/ui.py"
git commit -m "Touchpanel: report_* zeigt confirm_report (Meldung gesendet)"
```

---

### Task 6: Deploy auf Pico + End-to-End-Verifikation

**Files:** keine Code-Änderung (Deploy + Verifikation).

**Interfaces:** Consumes alle vorherigen Tasks.

- [ ] **Step 1: Geänderte Firmware-Dateien + Asset auf den Pico flashen**

```bash
cd "Smarte Mülltonne/Software"
DEV=/dev/cu.usbmodem14301
pkill -f usbmodem14301; sleep 1
mpremote connect port:$DEV fs cp Quellcode/Client/global_controller_test.py :global_controller_test.py
mpremote connect port:$DEV fs cp Flottenmanagement/firmware/pico_touchpanel/ui.py :ui.py
mpremote connect port:$DEV fs cp Flottenmanagement/firmware/pico_touchpanel/assets/confirm_report.rle :assets/confirm_report.rle
mpremote connect port:$DEV reset
```
Expected: keine Fehler; nach Reset `Main gestartet` auf der seriellen Konsole.

- [ ] **Step 2: Infrastruktur sicherstellen** — Backend (`:8000`) + Bridge (`:50002`) laufen, Pico mit Bridge verbunden (Bridge-Log: `Pico ist bereit`).

- [ ] **Step 3: Panel-Test HYGIENE** — am Touchpanel Menü → PIN `12#` → „problem" → „HYGIENE" tippen.
  - Panel zeigt **„Meldung gesendet"** (neues Asset).
  - Bridge-Log zeigt `report hygiene_report -> backend for bin 22` + `POST /security/events`.
  - Leitstand zeigt binnen ~0,5 s die Meldung „Hygieneproblem gemeldet" mit `Sparkles`-Icon (amber).

- [ ] **Step 4: Erledigen** — im Leitstand die Meldung „Erledigen" → verschwindet (nach nächstem WS-Push).

- [ ] **Step 5: Panel-Test SCHADEN** — „SCHADEN" → „Meldung gesendet" → Leitstand „Beschädigung gemeldet" mit `Wrench`-Icon → Erledigen.

- [ ] **Step 6: Commit (nur falls in diesem Task noch etwas justiert wurde)** — sonst entfällt.

---

## Self-Review-Notizen

- Spec-Abdeckung: Panel-Action (T3), Panel-Bestätigung/Asset (T4/T5), Transport/Bridge (T1), Backend (T2, unverändert), Anzeige+Erledigen (Frontend bereits vorhanden, in T6 verifiziert). ✅
- event_type durchgängig `damage_report`/`hygiene_report` (T1↔T2↔Frontend). ✅
- Zwei `ui.py` + zwei `assets/` konsistent gepflegt (T4/T5). ✅
