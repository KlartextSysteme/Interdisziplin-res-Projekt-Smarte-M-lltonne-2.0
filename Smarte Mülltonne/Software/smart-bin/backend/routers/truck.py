from fastapi import APIRouter
from pydantic import BaseModel

import truck_state

router = APIRouter()


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
def command(payload: TruckCommand):
    # TODO: forward command to RPi; for now just update state
    return truck_state.update(action=payload.action)
