from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

import truck_state
from config import settings

router = APIRouter()

ALLOWED_ACTIONS = {"start", "pause", "stop"}


class TruckPosition(BaseModel):
    lat: float
    lng: float
    action: str | None = None
    current_bin_id: int | None = None
    load_units: float | None = None
    capacity_units: float | None = None


class TruckCommand(BaseModel):
    action: str   # start | pause | stop


@router.get("/status")
def get_status():
    return truck_state.get()


@router.post("/position")
def update_position(payload: TruckPosition):
    return truck_state.update(**payload.model_dump(exclude_none=True))


@router.post("/command")
def command(payload: TruckCommand, x_admin_token: str = Header(default="")):
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    if payload.action not in ALLOWED_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid truck action: {payload.action}")
    # TODO: forward command to RPi; for now just update state
    return truck_state.update(action=payload.action)
