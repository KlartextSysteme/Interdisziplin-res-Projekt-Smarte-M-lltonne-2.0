from datetime import datetime, timezone
from math import hypot

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import truck_state
from database import get_db
from models.bin import Bin
from models.event import SecurityEvent

router = APIRouter()

# Radius, innerhalb dessen der Truck als "aktiv am Leeren" gilt und die Tonne
# entschaerft wird. Gleiche Wahrheit wie truck_simulator.ARRIVAL_THRESHOLD_M.
DISARM_RADIUS_M = 10.0


class BinUpdate(BaseModel):
    home_lat: float | None = None
    home_lng: float | None = None
    pickup_lat: float | None = None
    pickup_lng: float | None = None
    current_lat: float | None = None
    current_lng: float | None = None
    fill_level: int | None = None
    battery: int | None = None
    solar_output_w: float | None = None
    is_charging: bool | None = None
    status: str | None = None
    location_state: str | None = None
    movement_state: str | None = None
    lat: float | None = None
    lng: float | None = None


class PicoTelemetry(BaseModel):
    pico_state: str
    fill_level: int | None = None
    battery: int | None = None
    deckel_offen: bool | None = None
    target_destination: str | None = None
    location_state: str | None = None
    line_position: int | None = None
    obstacle_cm: float | None = None


class ProblemReportIn(BaseModel):
    report_type: str             # damage_report | hygiene_report
    source: str = "touchpanel"
    message: str | None = None


def _normalize_location_state(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    aliases = {
        "home": "home",
        "haus": "home",
        "street": "truck",
        "abholung": "truck",
        "collection": "truck",
        "pickup": "truck",
        "abholposition": "truck",
        "truck": "truck",
        "müllwagen": "truck",
        "muellwagen": "truck",
        "moving_to_pickup": "moving_to_pickup",
        "zur_abholposition": "moving_to_pickup",
        "moving_home": "moving_home",
        "nach_hause": "moving_home",
        "dock": "docking",
        "docking": "docking",
        "unknown": "unknown",
    }
    return aliases.get(normalized, normalized)


def _coords_for_location(b: Bin, location_state: str) -> tuple[float, float] | None:
    if location_state == "home" and b.home_lat is not None and b.home_lng is not None:
        return b.home_lat, b.home_lng
    if location_state == "truck" and b.pickup_lat is not None and b.pickup_lng is not None:
        return b.pickup_lat, b.pickup_lng
    return None


def _snap_to_location(b: Bin, location_state: str):
    coords = _coords_for_location(b, location_state)
    if not coords:
        return
    b.current_lat, b.current_lng = coords
    b.lat, b.lng = coords
    b.movement_state = "pickup" if location_state == "truck" else location_state


PICO_STATE_TO_BIN_STATUS = {
    "STANDBY": "idle",
    "FULL": "idle",
    "LINE_FOLLOWING": "en_route",
    "LINE_LOST": "en_route",
    "OBSTACLE": "en_route",
    "ARRIVED": "en_route",
    "WAIT_AT_STREET": "idle",
    "EMPTIED": "emptied",
    "USER_PAUSED": "idle",
    "MANUAL_GOTO_STREET_REQUEST": "idle",
    "MANUAL_RETURN_HOME_REQUEST": "idle",
}

# Pico-Zustand -> location_state. Damit eine (auch am Touchpanel ausgeloeste)
# Fahrt die Web-App/den Backend-Zustand sofort konsistent ueberschreibt, statt
# erst bei ARRIVED. LINE_FOLLOWING/ARRIVED bleiben absichtlich unberuehrt
# (Richtung ergibt sich aus dem vorangehenden MANUAL_*_REQUEST bzw. ARRIVED-Target).
PICO_STATE_TO_LOCATION = {
    "MANUAL_GOTO_STREET_REQUEST": "moving_to_pickup",
    "MANUAL_RETURN_HOME_REQUEST": "moving_home",
    "WAIT_AT_STREET": "truck",
    "STANDBY": "home",
}


@router.get("")
def get_all_bins(db: Session = Depends(get_db)):
    return db.query(Bin).all()


@router.get("/{bin_id}")
def get_bin(bin_id: int, db: Session = Depends(get_db)):
    b = db.query(Bin).filter(Bin.id == bin_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bin not found")
    return b


@router.post("/{bin_id}/update")
def update_bin(bin_id: int, payload: BinUpdate, db: Session = Depends(get_db)):
    b = db.query(Bin).filter(Bin.id == bin_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bin not found")

    data = payload.model_dump(exclude_none=True)
    for field, value in data.items():
        if field == "location_state":
            value = _normalize_location_state(value)
        setattr(b, field, value)

    location_state = _normalize_location_state(data.get("location_state"))
    changed_position = any(
        field in data
        for field in ("lat", "lng", "current_lat", "current_lng")
    )
    if location_state in {"home", "truck"} and not changed_position:
        _snap_to_location(b, location_state)
    b.last_seen = datetime.now(timezone.utc)

    db.commit()
    db.refresh(b)
    return b


@router.post("/{bin_id}/report")
def create_problem_report(bin_id: int, payload: ProblemReportIn, db: Session = Depends(get_db)):
    b = db.query(Bin).filter(Bin.id == bin_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bin not found")

    report_type = payload.report_type.strip().lower()
    allowed = {"damage_report", "hygiene_report"}
    if report_type not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported report_type: {payload.report_type}")

    event = SecurityEvent(
        bin_id=bin_id,
        event_type=report_type,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(event)
    b.last_seen = datetime.now(timezone.utc)
    db.commit()
    db.refresh(event)
    return {
        "ok": True,
        "bin_id": bin_id,
        "event_id": event.id,
        "event_type": event.event_type,
        "source": payload.source,
        "message": payload.message,
    }


@router.post("/{bin_id}/telemetry")
def update_pico_telemetry(bin_id: int, payload: PicoTelemetry, db: Session = Depends(get_db)):
    """Status bridge for the legacy Pico firmware.

    The old Pico reports robot-centric states like LINE_FOLLOWING or WAIT_AT_STREET.
    The fleet dashboard keeps a smaller bin-centric status, so this endpoint maps
    the state and updates optional sensor values when they are present.
    """
    b = db.query(Bin).filter(Bin.id == bin_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bin not found")

    if payload.fill_level is not None:
        b.fill_level = max(0, min(100, payload.fill_level))
    elif payload.pico_state == "FULL":
        b.fill_level = max(b.fill_level, 95)
    elif payload.pico_state == "EMPTIED":
        b.fill_level = 0

    if payload.battery is not None:
        b.battery = max(0, min(100, payload.battery))

    location_state = _normalize_location_state(payload.location_state)
    if not location_state and payload.target_destination:
        location_state = _normalize_location_state(payload.target_destination)
    if not location_state:
        # Fallback: aus dem Pico-Zustand ableiten (Touchpanel-Fahrt konsistent).
        location_state = PICO_STATE_TO_LOCATION.get(payload.pico_state)

    if location_state:
        b.location_state = location_state
        if location_state in {"home", "truck"}:
            _snap_to_location(b, location_state)

    if not b.locked:
        b.status = PICO_STATE_TO_BIN_STATUS.get(payload.pico_state, b.status)

    b.last_seen = datetime.now(timezone.utc)
    db.commit()
    db.refresh(b)
    return {
        "ok": True,
        "bin_id": b.id,
        "pico_state": payload.pico_state,
        "status": b.status,
        "fill_level": b.fill_level,
    }


def _truck_near_bin(b: Bin) -> tuple[bool, float | None]:
    """True, wenn der Truck aktiv am Leeren ist (<= DISARM_RADIUS_M von der Tonne)."""
    truck = truck_state.get()
    tlat, tlng = truck.get("lat"), truck.get("lng")
    blat = b.current_lat if b.current_lat is not None else b.lat
    blng = b.current_lng if b.current_lng is not None else b.lng
    if tlat is None or tlng is None or blat is None or blng is None:
        return False, None
    dist_m = hypot((tlat - blat) * 111_000, (tlng - blng) * 71_000)
    return dist_m <= DISARM_RADIUS_M, dist_m


@router.get("/{bin_id}/arm-state")
def get_arm_state(bin_id: int, db: Session = Depends(get_db)):
    """Security-Geofence: ist der Truck nah genug, um die Tonne zu entschaerfen
    (Leerung)? Die Bridge pollt das und reicht ARM/DISARM an den Pico weiter.
    Der Pico kombiniert es mit seinem eigenen 'zuhause'-Wissen."""
    b = db.query(Bin).filter(Bin.id == bin_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bin not found")
    near, dist_m = _truck_near_bin(b)
    return {
        "bin_id": bin_id,
        "disarmed": near,          # True = Truck am Leeren -> nicht scharf
        "distance_m": round(dist_m, 1) if dist_m is not None else None,
    }
