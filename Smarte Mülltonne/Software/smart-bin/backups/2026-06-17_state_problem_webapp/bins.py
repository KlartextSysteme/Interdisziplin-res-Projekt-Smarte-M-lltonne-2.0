from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.bin import Bin

router = APIRouter()


class BinUpdate(BaseModel):
    fill_level: int | None = None
    battery: int | None = None
    solar_output_w: float | None = None
    is_charging: bool | None = None
    status: str | None = None
    lat: float | None = None
    lng: float | None = None


class PicoTelemetry(BaseModel):
    pico_state: str
    fill_level: int | None = None
    battery: int | None = None
    deckel_offen: bool | None = None
    target_destination: str | None = None
    line_position: int | None = None
    obstacle_cm: float | None = None


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

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(b, field, value)
    b.last_seen = datetime.now(timezone.utc)

    db.commit()
    db.refresh(b)
    return b


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
