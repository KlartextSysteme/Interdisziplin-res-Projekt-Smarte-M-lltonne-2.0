"""Demo-Simulation-Controls: globaler Zeit-Multiplikator und Pause-Schalter.

Alle Simulator-Prozesse (mock_truck, mock_bins, mock_energy) pollen Speed und
Pause-State und skalieren ihre Tick-Raten entsprechend. So kann man während
der Demo live zwischen Echtzeit (1×) und Zeitraffer (bis 20×) umschalten oder
die komplette Simulation einfrieren.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

# In-Memory-State — reicht für Demo (kein Multi-Node-Deploy).
_state: dict = {"speed": 1.0, "paused": False}

MIN_SPEED = 0.5
MAX_SPEED = 20.0


class SimUpdate(BaseModel):
    speed: float | None = Field(None, description="Simulation speed multiplier (0.5 … 20)")
    paused: bool | None = Field(None, description="Globale Pause für alle Simulatoren")


def set_state(*, speed: float | None = None, paused: bool | None = None):
    if speed is not None:
        if not (MIN_SPEED <= speed <= MAX_SPEED):
            raise HTTPException(400, f"speed must be in [{MIN_SPEED}, {MAX_SPEED}]")
        _state["speed"] = float(speed)
    if paused is not None:
        _state["paused"] = bool(paused)
    return dict(_state)


@router.get("/speed")
def get_speed():
    return {
        "speed": _state["speed"],
        "paused": _state["paused"],
        "min": MIN_SPEED,
        "max": MAX_SPEED,
    }


@router.put("/speed")
def set_sim(body: SimUpdate):
    set_state(speed=body.speed, paused=body.paused)
    return {"speed": _state["speed"], "paused": _state["paused"]}
