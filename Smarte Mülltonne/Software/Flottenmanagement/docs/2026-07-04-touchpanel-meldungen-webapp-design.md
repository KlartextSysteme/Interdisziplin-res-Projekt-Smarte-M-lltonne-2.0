# Design-Spec: Touchpanel-Meldungen (Hygiene/Geruch, Beschädigung) → Web-App

Stand: 2026-07-04 · Status: abgenommen, bereit für Umsetzung

## 1. Ziel

Der Operator kann am **physischen Touchpanel** der Tonne zwei Zustandsmeldungen
auslösen — **Hygiene/Geruch** und **Beschädigung**. Diese Meldungen sollen bei
Auslösung **live in der Web-App (Leitstand)** erscheinen und dort vom Operator
**erledigt** werden können. Am Panel bestätigt ein Screen „Meldung gesendet".

Vertical Slice über: Touchpanel-Firmware → TCP-Bridge → Backend → Frontend.

## 2. Ist-Zustand (verifiziert)

- **Touchpanel:** Submenü „problem" hat bereits die Buttons `("SCHADEN", "report_damage")`
  und `("HYGIENE", "report_hygiene")` (`ui.py`). Buttons werden als `"do:report_*"`
  gerendert → `handle_action` → `_perform_action(report_*)`, das (a) die Action an
  `action_handler` (= Controller) weiterreicht und (b) `show_confirm(asset)` zeigt.
  **Heute:** Asset = `confirm_generic` („Auswahl bestätigt"), Controller ignoriert die Action.
- **Zwei `ui.py`-Kopien:** `Flottenmanagement/firmware/pico_touchpanel/ui.py` (läuft auf dem Pico)
  und `Quellcode/Client/ui.py` (Repo). Beide haben Buttons + Confirm-Mechanik.
- **Confirm-Screens sind fertige Bild-Assets** im Format `WF1` (RLE, palettenbasiert:
  Magic `WF1`, width/height, Palette, pro Zeile `(run, palette_index)`). Text ist
  eingebrannt — kein dynamischer Text. Vorhandene Assets: `confirm_generic/_locked/
  _unlocked/_connected/_disconnected.rle`.
- **Controller (`global_controller_test.py`):** `handle_touch_action` behandelt nur
  goto_street/goto_home/shutdown. `_bridge_send(line)` existiert (fehlertolerant).
- **Bridge (`tcp_bridge.py`):** `_handle_pico_line` parst `STATUS:`/`ARRIVED:`/`ACK ...`
  und POSTet ans Backend. Kennt `self.state.bin_id` (= 22).
- **Backend:** `SecurityEvent(bin_id, event_type: str [frei], timestamp, resolved)`.
  `POST /security/events {bin_id, event_type}`, `GET /security/events` (offene),
  `POST /security/{bin_id}/resolve` (alle offenen einer Tonne). `create_event` hat
  ein `# TODO: push alert via WebSocket`.
- **WebSocket (`ws.py`):** broadcastet `bins` + `alerts` (= offene SecurityEvents)
  alle ~0,35 s an das Frontend.
- **Frontend:** `AlertBanner.tsx` + `SecurityPanel.tsx` zeigen die WS-`alerts`;
  `resolveAlerts(binId)` → `POST /security/{bin_id}/resolve`.
- **Frontend kennt die Meldungstypen bereits:** `lib/labels.ts` hat
  `securityEventLabel`/`eventTone` für `damage_report` („Beschädigung gemeldet")
  und `hygiene_report` („Hygieneproblem gemeldet", beide amber). `SecurityPanel.tsx`
  rendert dafür schon eigene Icons: `Wrench` (damage_report) und `Sparkles`
  (hygiene_report). → **Das Frontend braucht keine Änderung, sofern der event_type
  exakt `damage_report`/`hygiene_report` heißt.**

## 3. Design & Datenfluss

```
Touchpanel  SCHADEN/HYGIENE
   → ui._perform_action(report_damage|report_hygiene)
       ├─ action_handler(action)  → controller.handle_touch_action   [NEU: reagieren]
       │      → _bridge_send("REPORT:DAMAGE" | "REPORT:HYGIENE")
       └─ show_confirm("confirm_report")   [NEU: Asset "Meldung gesendet"]
   ↓ (TCP-Bridge-Socket)
Bridge._handle_pico_line: "REPORT:<kind>"   [NEU: Parsing]
   → POST {backend}/security/events {bin_id: 22, event_type: "damage_report"|"hygiene_report"}
   ↓
Backend.create_event → SecurityEvent(event_type, resolved=False)   [wiederverwendet]
   ↓
ws.py Broadcast (alerts[] enthält die Meldung, ~0,35 s)            [existiert]
   ↓
Frontend AlertBanner/SecurityPanel: Meldung mit eigenem Icon       [NEU: Icon/Label]
   → Operator „Erledigen" → resolveAlerts(22) → verschwindet       [existiert]
```

## 4. Komponenten & Änderungen

1. **Neues Asset `assets/confirm_report.rle`** — „Meldung gesendet"-Screen
   (gelbes Häkchen-Quadrat + Text „Meldung gesendet", dunkler Hintergrund) im
   selben Schriftstil wie `confirm_generic`. Erzeugung:
   - Kleines Hilfsskript **PNG→WF1-Encoder** schreiben (Format ist in
     `wireframe.py`-Decoder + `docs/touchpanel_menu_icon_rework_result.md`
     dokumentiert: `WF1`, width/height big-endian, Palette `len×2B` RGB565,
     pro Zeile `row_len` + `(run, index)`-Bytes).
   - Referenzstil aus `confirm_generic.rle` (Palette/Layout/Schrift) und dem
     vom Operator gelieferten Wireframe. 320×240.
   - Ablage: `Flottenmanagement/firmware/pico_touchpanel/assets/` (läuft auf Pico) **und**
     `Quellcode/Client/assets/` (Repo-Konsistenz). Auf den Pico deployen.
2. **`ui.py` (firmware + Client)** — in `_perform_action`: vor dem `else`
   `report_damage`/`report_hygiene` → `asset = "confirm_report"`. Sonst unverändert
   (Weiterreichen an `action_handler` + `show_confirm` bleibt).
3. **`Quellcode/Client/global_controller_test.py`** — `handle_touch_action`:
   `report_damage` → `self._bridge_send("REPORT:DAMAGE")`,
   `report_hygiene` → `self._bridge_send("REPORT:HYGIENE")`.
4. **`Flottenmanagement/bridge/tcp_bridge.py`** — in `_handle_pico_line`: Zweig
   `line.startswith("REPORT:")` → kind = Rest (`DAMAGE`|`HYGIENE`) → mappe auf
   `event_type` **`"damage_report"`/`"hygiene_report"`** (exakt die vom Frontend
   erwarteten Keys) → `POST {backend}/security/events {bin_id: self.state.bin_id,
   event_type}`. Fehler tolerieren (loggen, kein Crash).
5. **`Flottenmanagement/backend/routers/security.py`** — unverändert nutzbar (`event_type`
   frei). Optional (nicht zwingend): das `# TODO`-WS-Push implementieren für sofortige
   Anzeige; ohne das deckt der ~0,35-s-Broadcast es ab.
6. **Frontend — keine Änderung nötig.** `damage_report`/`hygiene_report` sind in
   `lib/labels.ts` (Label + amber-Ton) und `SecurityPanel.tsx` (Icons `Wrench`/
   `Sparkles`) bereits umgesetzt; Erledigen-Button (`resolveAlerts`) existiert.
   *Optionaler Polish (nicht im Slice):* `AlertBanner.tsx` nutzt ein generisches
   `AlertTriangle`-Icon — dort könnte man später auch das typ-spezifische Icon zeigen.

## 5. Datenmodell

Wiederverwendung von `SecurityEvent`. Keine Migration. `event_type` nutzt zwei
Werte, die das Frontend **bereits kennt**: `"damage_report"`, `"hygiene_report"`.
(String-Feld, kein Enum-Zwang.)

## 6. Fehlerbehandlung & Grenzen (YAGNI)

- `_bridge_send` ist fehlertolerant: offline geht die Meldung **best-effort verloren**
  (wie STATUS). Kein Retry/Queue im Slice.
- Bridge-POST scheitert → loggen, kein Crash.
- `bin_id` = die konfigurierte Bridge-Tonne (22, physische Demo-Tonne).
- `/resolve` löst **alle** offenen Events der Tonne 22 gemeinsam (Tamper + Hygiene +
  Schaden). Für die Demo akzeptabel; pro-Meldung-Resolve ist **nicht** im Scope.
- Kein Debounce bei Mehrfach-Tap (jeder Tap = ein Event). Akzeptabel.

## 7. Verifikation

- **Backend/Bridge isoliert:** simulierte Pico-Zeile `REPORT:HYGIENE` an die Bridge
  → `POST /security/events` → `GET /security/events` enthält `{event_type:"hygiene"}`
  → WS-Payload `alerts[]` enthält sie.
- **Frontend:** Alert mit event_type „hygiene"/„damage" → korrektes Icon + Label,
  „Erledigen" entfernt sie (nach nächstem WS-Push).
- **End-to-End:** Am Panel „HYGIENE" tippen → Panel zeigt „Meldung gesendet" →
  Meldung erscheint live im Leitstand mit `Wind`-Icon → „Erledigen" → verschwindet.
  Analog „SCHADEN" → `Hammer`-Icon.

## 8. Nicht im Scope

- Kein neues Meldungs-Datenmodell / keine eigene UI-Fläche (Wiederverwendung Alerts).
- Kein pro-Meldung-Resolve, kein Offline-Retry/Queue, kein Debounce.
- Keine neuen Touchpanel-Buttons (existieren bereits).

## 9. Getroffene Entscheidungen

- Modellierung: **A** — bestehenden Alert-Kanal (`SecurityEvent`) wiederverwenden.
- Lifecycle: **B** — Anzeigen **und** Erledigen.
- Panel-Bestätigung: **ja**, neues Asset „Meldung gesendet" im Confirm-Stil.
- Icons: **bereits im Frontend vorhanden** — Beschädigung = `Wrench`,
  Hygiene = `Sparkles` (SecurityPanel). Keine neuen Icons nötig.
