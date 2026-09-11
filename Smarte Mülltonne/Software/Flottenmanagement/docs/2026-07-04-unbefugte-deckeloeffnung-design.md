# Design-Spec: Unbefugte Deckelöffnung → Alarm (Buzzer + Leitstand)

Stand: 2026-07-04 · Status: abgenommen (Brainstorming), bereit für Umsetzungsplan

## 1. Ziel

Die Tonne erkennt eine **Deckelöffnung** und entscheidet, ob sie **legitim**
(Einwurf zuhause / Leerung durch den Müllwagen) oder **unbefugt** ist. Bei einer
unbefugten Öffnung reagiert sie **sofort beim Öffnen**:

- **Buzzer-Alarm** am Fahrzeug (Abschreckung),
- **`unauthorized_open`-Meldung live im Leitstand** (Security-Panel).

Sofort-beim-Öffnen (nicht beim Schließen) ist bewusst: Abschreckeffekt + nicht
umgehbar durch „Deckel offen lassen und abhauen".

## 2. Ist-Zustand (verifiziert)

- **Deckel-offen-Erkennung existiert heuristisch:** `FuellstandSensor.is_deckel_offen()`
  wird True, wenn der Füllstand-Ultraschall (Kanal C8) mehrfach **kein Echo** liefert
  (`no_echo_for_deckel_offen=3`). Aktuell nur ~alle 2 s gemessen → ~6 s träge.
- **Geofence existiert schon** in `services/truck_simulator.py`:
  `ARRIVAL_THRESHOLD_M = 10.0`; bei Annäherung des Trucks wird die Tonne
  losgeschickt (`_schedule_bin_move(pickup)`), bei `_haversine_m(pos, bin) <= 10 m`
  erfolgt `_empty_bin`. Backend kennt Truck-Position (`truck_state`) + Bin-Position.
- **Sim bewegt nur virtuelle Tonnen** (1–35). Die **physische Tonne 22** wird
  **manuell** über die Web-App (`goto_street`) losgeschickt — „Nutzer schickt Tonne
  eher zur Straße" ist bei 22 also der Normalfall.
- **SecurityEvent** unterstützt `event_type` als freien String; `unauthorized_open`
  war von Anfang an ein vorgesehener Typ. WS broadcastet offene Events; Security-Panel
  zeigt sie + „Erledigen". *(Zu prüfen: Label/Icon für `unauthorized_open` im Frontend.)*
- **Bridge** relayt Pico-Zeilen (`STATUS`/`ARRIVED`/`ACK`) ↔ Backend und pollt
  `/bins/22/pending-command`. `_bridge_send`/`REPORT:`-Mechanik ist da (Meldungs-Slice).
- **Lücke:** Eine **Touchpanel-`goto_street`** setzt im Backend nur `status="en_route"`,
  aber **nicht** `location_state`/Position (erst bei `ARRIVED:STREET`). Web-App zeigt die
  Tonne während der Fahrt noch „zuhause".

## 3. Klassifizierungs-Regel

**Scharf (armed) = Deckel-Öffnung löst Alarm aus**, außer in zwei Fällen:

| Deckel öffnet, wenn … | Bewertung |
|---|---|
| **zuhause** (`AT_HOME`/`PARTY`) | Einwurf → erlaubt (der Pico weiß das lokal) |
| **Truck aktiv am Leeren** (Truck ≤ 10 m, Backend meldet „disarm") | Leerung → erlaubt |
| **sonst** (Fahren, an der Abholpos ohne Truck, geparkt) | **unbefugt → Alarm** |

Bewusst: **entschärft nur bei tatsächlicher Leerung** (Truck wirklich da), nicht
schon beim Losfahren — so bleibt die manuell rausgeschickte Tonne die ganze Wartezeit
an der Straße geschützt.

## 4. Architektur & Datenfluss

```
Pico (lokal):
  Deckel-Monitor (schnell, ~500 ms): FuellstandSensor -> deckel_offen
  armed = (state NICHT in {AT_HOME, PARTY}) UND (nicht disarm_by_truck)
  deckel geht auf & armed  ->  SOFORT:
        buzzer.play(alarm_pattern, repeat)        (Abschreckung)
        _bridge_send("REPORT:UNAUTHORIZED_OPEN")   (einmal pro Öffnung)
  deckel zu / wieder disarmed  ->  buzzer aus

Backend (Geofence, erbt truck_simulator):
  disarm(bin) = _haversine_m(truck_pos, bin_pos) <= ARRIVAL_THRESHOLD_M (10 m)
  -> als Arm/Disarm-Zustand bereitstellen (Endpoint, den die Bridge pollt)

Bridge:
  pollt Arm/Disarm-Zustand -> sendet "ARM"/"DISARM" an den Pico bei Wechsel
  relayt "REPORT:UNAUTHORIZED_OPEN" -> POST /security/events
        {bin_id: 22, event_type: "unauthorized_open"}

Backend -> WS -> Security-Panel (live), "Erledigen" wie bei den Meldungen.
```

## 5. Komponenten & Änderungen

1. **Pico `global_controller_test.py`**
   - Deckel-Monitor als Querschnitts-Check in `run()` (throttled ~500 ms): misst
     Füllstand → `deckel_offen`. Schnellere Bestätigung (z. B. `no_echo=2`) für knackige
     Reaktion; Kompromiss gegen Fehlalarm.
   - `self._armed_by_truck_disarm` (Flag, gesetzt von `handle_network_command("ARM"/"DISARM")`).
   - `armed`-Ableitung + Alarm-Logik (Buzzer-Pattern + einmalig `REPORT:UNAUTHORIZED_OPEN`
     pro Öffnungs-Transition; Buzzer läuft bis Deckel zu / disarmed).
   - `handle_network_command`: neue Kommandos `ARM`/`DISARM`.
2. **Bridge `tcp_bridge.py`**
   - Arm/Disarm-Zustand vom Backend pollen → `ARM`/`DISARM` an Pico bei Änderung.
   - `REPORT:UNAUTHORIZED_OPEN` → `POST /security/events {event_type:"unauthorized_open"}`.
3. **Backend**
   - Geofence-Auswertung für Bin 22 (Distanz Truck↔Bin ≤ 10 m) → Arm/Disarm-Zustand
     bereitstellen (kleiner Endpoint oder Feld, das die Bridge pollt). Reuse
     `_haversine_m` + `truck_state`.
   - **Telemetry-Fix** (`routers/bins.py`): pico_state → `location_state` mappen
     (`MANUAL_GOTO_STREET_REQUEST`→`moving_to_pickup`, `MANUAL_RETURN_HOME_REQUEST`→
     `moving_home`, `WAIT_AT_STREET`→`truck`, `STANDBY`/`AT_HOME`→`home`), damit eine
     Touchpanel-Fahrt Web-App + Backend-Zustand sofort konsistent überschreibt.
   - `SecurityEvent(unauthorized_open)` bleibt (freier event_type).
4. **Frontend**
   - Prüfen/ergänzen: Label + Icon für `event_type="unauthorized_open"` in
     `lib/labels.ts` + `SecurityPanel.tsx` (falls noch nicht vorhanden). Erledigen-Loop existiert.

## 6. Fehlerbehandlung & Grenzen (YAGNI)

- Deckel-Erkennung ist heuristisch (kein Echo). Fehlmessungen → durch N-Bestätigung
  gedämpft; Kompromiss Reaktionszeit ↔ Fehlalarm ist ein Tuning-Knopf.
- `_bridge_send` fehlertolerant: offline geht die Meldung best-effort verloren; der
  **Buzzer-Alarm läuft lokal trotzdem** (Abschreckung unabhängig vom Netz).
- Fällt der Arm/Disarm-Poll aus (Bridge/Backend weg), bleibt der zuletzt bekannte
  Zustand; Default = **scharf, sobald außer Haus** (sicherheitskonservativ).
- Deckel-Check läuft auch während der Fahrt (~8 ms Messung / 500 ms = akzeptabler Jitter).
- Ein Alarm/Event pro Öffnung (kein Spam), reset bei Deckel-zu.

## 7. Verifikation

- **Backend/Bridge isoliert:** Truck-Position nah/fern an Bin 22 setzen →
  Arm/Disarm-Zustand kippt; simulierte `REPORT:UNAUTHORIZED_OPEN` → `GET /security/events`.
- **Telemetry:** Touchpanel-`goto_street` → Bin 22 `location_state=moving_to_pickup`
  → Web-App zeigt „unterwegs" (nicht mehr „zuhause").
- **End-to-End (Demo):** `goto_street` (Web-App oder Touchpanel) → Tonne wartet an der
  Straße = **scharf** → Deckel öffnen → **Buzzer + `unauthorized_open` im Leitstand**.
  Sim-Truck erreicht Bin 22 (≤10 m) = **entschärft** → Deckel öffnen → kein Alarm.
  Zuhause: Deckel öffnen → kein Alarm.

## 8. Nicht im Scope

- Kein echter Deckel-Sensor (bleibt Füllstand-Heuristik).
- Kein physischer Schließmechanismus / Verriegelung.
- Kein Retry/Queue der Meldung bei Offline (Buzzer reicht lokal).
- Kein Auto-Dispatch der **physischen** Tonne 22 durch den Sim (bleibt manuell).

## 9. Getroffene Entscheidungen

- Erkennung **beim Öffnen** (sofort), nicht beim Schließen.
- Klassifizierung: **scharf = außer zuhause**; **entschärft = zuhause ODER Truck aktiv
  am Leeren (≤10 m)**.
- Geofence: **vorhandenen `truck_simulator`/`ARRIVAL_THRESHOLD_M=10 m` wiederverwenden**.
- Alarm = **Buzzer (lokal, sofort) + `unauthorized_open`-SecurityEvent** (reuse Meldungs-Infra).
- **Telemetry-Fix** für Touchpanel-Dispatch gehört mit in den Slice.
