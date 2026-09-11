import json
import os
import httpx
from langchain_core.tools import tool

BASE_URL = os.getenv("AGENT_BASE_URL") or f"http://127.0.0.1:{os.getenv('PORT', '8000')}"


def _bin_status_label(status: str, locked: bool = False) -> str:
    if locked:
        return "Gesperrt"
    return {
        "idle": "Bereit",
        "en_route": "Unterwegs",
        "emptied": "Geleert",
        "locked": "Gesperrt",
    }.get(status, status)


def _security_event_label(event_type: str) -> str:
    return {
        "tamper": "Manipulationsalarm",
        "theft_attempt": "Diebstahlversuch",
        "unauthorized_open": "Unbefugtes Öffnen",
        "damage_report": "Beschädigung gemeldet",
        "hygiene_report": "Hygieneproblem gemeldet",
    }.get(event_type, event_type)


def _location_state_label(location_state: str | None) -> str:
    return {
        "home": "Am Haus",
        "truck": "Abholposition",
        "moving_to_pickup": "Fährt zur Abholposition",
        "moving_home": "Fährt nach Hause",
        "docking": "Dockingstation",
        "unknown": "Position unbekannt",
    }.get(location_state or "unknown", location_state or "Position unbekannt")


def _admin_headers() -> dict[str, str]:
    return {"X-Admin-Token": os.getenv("ADMIN_TOKEN", "changeme")}


def _focus_to_label(focus: str) -> str | None:
    """Mappt eine natürlichsprachliche Schwerpunkt-Angabe auf das variant_label
    eines Routen-Kandidaten. None → keine Vorgabe (System-Default)."""
    f = (focus or "").lower()
    if not f:
        return None
    if any(k in f for k in ("dring", "voll", "überlauf", "ueberlauf", "urgent")):
        return "Dringendste zuerst"
    if any(k in f for k in ("viel", "meist", "durchsatz", "anzahl", "maximal")):
        return "Meiste Tonnen"
    if any(k in f for k in ("kurz", "strecke", "sprit", "schnell", "distanz", "weg", "nah")):
        return "Kürzeste Strecke"
    return None


def _plan_and_select(focus: str) -> tuple[dict | None, list[dict]]:
    """Plant die Route (liefert drei Schwerpunkt-Kandidaten), wählt den
    gewünschten Schwerpunkt aus und schaltet ihn aktiv (der Wagen fährt ihn).
    Ohne Vorgabe bleibt die System-Empfehlung aktiv."""
    resp = httpx.post(f"{BASE_URL}/routes/plan", timeout=30)
    resp.raise_for_status()
    data = resp.json()
    candidates = [c for c in (data if isinstance(data, list) else [data]) if c.get("waypoints")]
    if not candidates:
        return None, []

    label = _focus_to_label(focus)
    chosen = None
    if label:
        chosen = next((c for c in candidates if c.get("variant_label") == label), None)
        if chosen and not chosen.get("active"):
            httpx.post(f"{BASE_URL}/routes/{chosen['id']}/activate", timeout=10)
    if chosen is None:
        chosen = next((c for c in candidates if c.get("is_default")), candidates[0])
    return chosen, candidates


@tool
def get_bins() -> str:
    """Alle Tonnen mit Füllstand, Akku und Sicherheitsstatus."""
    resp = httpx.get(f"{BASE_URL}/bins", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return "Keine Tonnen registriert."
    cleaned = [
        {
            "id": b["id"],
            "name": b["name"],
            "adresse": b["address"],
            "fuellstand_prozent": b["fill_level"],
            "akku_prozent": b["battery"],
            "status": _bin_status_label(b["status"], b["locked"]),
            "position": _location_state_label(b.get("location_state")),
            "gesperrt": b["locked"],
        }
        for b in data
    ]
    return json.dumps(cleaned, ensure_ascii=False)


@tool
def plan_route(focus: str = "") -> str:
    """Plant die nächste Abholroute (Tonnen ab 60 % Füllstand, gesperrte ausgenommen)
    und liefert drei Schwerpunkt-Varianten. Der Wagen fährt automatisch die gewählte.

    focus (optional) wählt den Schwerpunkt:
      - "kurze strecke" → kürzeste Fahrt, wenig Sprit/Zeit (Standard/Empfehlung)
      - "dringende"     → vollste Tonnen zuerst (Überlauf vermeiden)
      - "viele tonnen"  → möglichst viele Tonnen pro Fahrt (max. Durchsatz)
    Ohne focus wird die Empfehlung (kürzeste Strecke) aktiv. Der Wagen sammelt
    unterwegs ohnehin jede volle Tonne mit, an der er vorbeikommt — der Schwerpunkt
    bestimmt v. a., welche Tonnen/Gegend zuerst angefahren werden."""
    chosen, candidates = _plan_and_select(focus)
    if not chosen:
        return json.dumps({"message": "Keine vollen Tonnen — keine Route nötig."}, ensure_ascii=False)
    return json.dumps({
        "gewaehlter_schwerpunkt": chosen.get("variant_label"),
        "route_id": chosen["id"],
        "tonnen": len(chosen.get("waypoints", [])),
        "distance_m": chosen.get("distance_m"),
        "duration_s": chosen.get("duration_s"),
        "auslastung_prozent": (
            round(100 * (chosen.get("load_units") or 0) / chosen["capacity_units"])
            if chosen.get("capacity_units") else None
        ),
        "alternativen": [
            {
                "schwerpunkt": c.get("variant_label"),
                "tonnen": len(c.get("waypoints", [])),
                "km": round((c.get("distance_m") or 0) / 1000, 1),
            }
            for c in candidates
        ],
    }, ensure_ascii=False)


@tool
def dispatch_truck(focus: str = "") -> str:
    """Komplette Einsatzplanung: plant eine Route mit optionalem Schwerpunkt UND
    startet das Fahrzeug. focus wie bei plan_route ("kurze strecke" | "dringende"
    | "viele tonnen"). Für Anfragen wie 'starte die Abholung' oder 'los, fahr los'."""
    chosen, _ = _plan_and_select(focus)
    if not chosen:
        return "Keine vollen Tonnen — keine Abholung nötig."
    httpx.post(f"{BASE_URL}/truck/command", json={"action": "start"}, headers=_admin_headers(), timeout=10)
    km = (chosen.get("distance_m") or 0) / 1000
    mins = round((chosen.get("duration_s") or 0) / 60)
    return (
        f"Route {chosen['id']} geplant (Schwerpunkt: {chosen.get('variant_label')}) und "
        f"Fahrzeug gestartet. {len(chosen['waypoints'])} Tonnen, {km:.1f} km, ca. {mins} Minuten."
    )


@tool
def send_command(action: str) -> str:
    """Fahrzeug steuern. action: start | pause | stop."""
    resp = httpx.post(f"{BASE_URL}/truck/command", json={"action": action}, headers=_admin_headers(), timeout=10)
    return resp.text


@tool
def lock_bin(bin_id: int, reason: str) -> str:
    """Sperrt eine Tonne bei Sicherheitsvorfall. Motor wird via Command-Queue deaktiviert."""
    resp = httpx.post(
        f"{BASE_URL}/security/{bin_id}/lock",
        headers=_admin_headers(),
        timeout=10,
    )
    return f"Tonne {bin_id} gesperrt: {reason} → HTTP {resp.status_code}"


@tool
def unlock_bin(bin_id: int) -> str:
    """Entsperrt eine zuvor gesperrte Tonne nach Überprüfung."""
    resp = httpx.post(
        f"{BASE_URL}/security/{bin_id}/unlock",
        headers=_admin_headers(),
        timeout=10,
    )
    return f"Tonne {bin_id} entsperrt → HTTP {resp.status_code}"


@tool
def empty_bin_manual(bin_id: int) -> str:
    """Setzt den Füllstand einer Tonne auf 0 — für manuelle Korrekturen oder Tests."""
    resp = httpx.post(
        f"{BASE_URL}/bins/{bin_id}/update",
        json={"fill_level": 0, "status": "emptied"},
        timeout=10,
    )
    return f"Tonne {bin_id} manuell geleert → HTTP {resp.status_code}"


@tool
def get_security_events() -> str:
    """Aktuelle, nicht quittierte Sicherheits- und Problem-Meldungen."""
    resp = httpx.get(f"{BASE_URL}/security/events", timeout=10)
    resp.raise_for_status()
    events = resp.json()
    if not events:
        return "Keine offenen Meldungen."
    cleaned = [
        {
            "id": e["id"],
            "tonne_id": e["bin_id"],
            "meldung": _security_event_label(e["event_type"]),
            "zeitpunkt": e["timestamp"],
            "quittiert": e.get("resolved", False),
        }
        for e in events
    ]
    return json.dumps(cleaned, ensure_ascii=False)


@tool
def get_energy_status() -> str:
    """Akkustände aller Tonnen."""
    resp = httpx.get(f"{BASE_URL}/energy", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return "Keine Akkudaten verfügbar."
    cleaned = [
        {
            "tonne_id": e["bin_id"],
            "name": e["name"],
            "akku_prozent": e["battery"],
        }
        for e in data
    ]
    return json.dumps(cleaned, ensure_ascii=False)


ALL_TOOLS = [
    get_bins,
    plan_route,
    dispatch_truck,
    send_command,
    lock_bin,
    unlock_bin,
    empty_bin_manual,
    get_security_events,
    get_energy_status,
]
