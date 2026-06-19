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
def plan_route() -> str:
    """Plant die nächste Abholroute. Filtert Tonnen ab 60 % Füllstand, überspringt gesperrte.
    Optimiert die Reihenfolge per 2-opt TSP-Heuristik (Baseline: Nearest-Neighbour).
    Nutzt OSRM für echte Straßen-Routen. Gibt waypoints, distance_m, duration_s und
    nn_distance_m / optimized_distance_m für den Optimierungs-Vergleich zurück."""
    resp = httpx.post(f"{BASE_URL}/routes/plan", timeout=30)
    resp.raise_for_status()
    route = resp.json()
    return json.dumps({
        "route_id": route["id"],
        "waypoints": route["waypoints"],
        "distance_m": route["distance_m"],
        "duration_s": route.get("duration_s"),
        "nn_distance_m": route.get("nn_distance_m"),
        "optimized_distance_m": route.get("optimized_distance_m"),
        "exact_distance_m": route.get("exact_distance_m"),
    }, ensure_ascii=False)


@tool
def dispatch_truck() -> str:
    """Komplette Einsatzplanung: plant eine Route UND startet das Fahrzeug.
    Für Anfragen wie 'starte die Abholung' oder 'los, fahr los'."""
    plan = httpx.post(f"{BASE_URL}/routes/plan", timeout=30).json()
    httpx.post(f"{BASE_URL}/truck/command", json={"action": "start"}, timeout=10)
    km = plan["distance_m"] / 1000
    mins = round((plan.get("duration_s") or 0) / 60)
    return (
        f"Route {plan['id']} geplant und Fahrzeug gestartet. "
        f"{len(plan['waypoints'])} Tonnen, {km:.1f} km, ca. {mins} Minuten."
    )


@tool
def send_command(action: str) -> str:
    """Fahrzeug steuern. action: start | pause | stop."""
    resp = httpx.post(f"{BASE_URL}/truck/command", json={"action": action}, timeout=10)
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
