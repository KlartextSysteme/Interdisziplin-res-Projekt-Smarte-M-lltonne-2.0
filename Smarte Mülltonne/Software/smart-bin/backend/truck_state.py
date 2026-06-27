"""In-memory truck state — replaced by RPi telemetry in production."""
from datetime import datetime, timezone

_state: dict = {
    "lat": None,
    "lng": None,
    "action": "idle",        # idle | en_route | pause | returning
    "current_bin_id": None,  # bin currently being approached
    "load_units": 0.0,
    "capacity_units": 600.0,
    "load_percent": 0,
    "route_progress": None,  # 0..1 = exakte Position des Wagens entlang der Route
    "updated_at": None,
}


def get() -> dict:
    return dict(_state)


def update(**fields) -> dict:
    _state.update(fields)
    capacity = float(_state.get("capacity_units") or 0)
    load = float(_state.get("load_units") or 0)
    _state["load_percent"] = int(round((load / capacity) * 100)) if capacity > 0 else 0
    _state["updated_at"] = datetime.now(timezone.utc).isoformat()
    return dict(_state)
