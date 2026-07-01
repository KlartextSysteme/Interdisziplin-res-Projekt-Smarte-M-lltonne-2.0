from __future__ import annotations

import random
import time
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import truck_state
from config import settings
from database import get_db
from models.bin import Bin
from models.command import Command
from models.event import SecurityEvent
from models.route import Route
from routers import sim

router = APIRouter()

DemoProfile = Literal["realistic_shift", "hardware_focus", "high_load", "quiet_day", "random"]


class DemoResetRequest(BaseModel):
    profile: DemoProfile = Field("realistic_shift", description="Demo scenario to apply")
    seed: int | None = Field(None, description="Optional seed for reproducible random values")
    fh_bin_id: int = Field(22, description="Hardware/FH campus bin id")
    clear_history: bool = True
    include_alerts: bool = True
    sim_speed: float = 1.0
    sim_paused: bool = False


class DemoStatus(BaseModel):
    profile: str | None = None
    seed: int | None = None
    bins_total: int
    collectable_bins: int
    critical_bins: int
    locked_bins: int
    open_alerts: int
    pending_commands: int
    routes: int
    fh_bin_id: int
    fh_fill_level: int | None
    sim_speed: float
    sim_paused: bool
    truck_action: str | None


def _clamp_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))


def _home_coords(b: Bin) -> tuple[float | None, float | None]:
    return (
        b.home_lat if b.home_lat is not None else b.lat,
        b.home_lng if b.home_lng is not None else b.lng,
    )


def _profile_fill(profile: DemoProfile, b: Bin, index: int, rng: random.Random, fh_bin_id: int) -> int:
    if profile == "hardware_focus":
        if b.id == fh_bin_id:
            return rng.randint(84, 92)
        if b.id in {3, 18, 25, 30, 35}:
            return rng.randint(62, 78)
        return rng.randint(12, 55)

    if profile == "high_load":
        if b.id == fh_bin_id:
            return rng.randint(88, 96)
        return rng.randint(58, 98)

    if profile == "quiet_day":
        if b.id == fh_bin_id:
            return rng.randint(50, 64)
        if index % 9 == 0:
            return rng.randint(55, 68)
        return rng.randint(8, 49)

    if profile == "random":
        return rng.randint(0, 100)

    # realistic_shift: a plausible start-of-shift mix with a few urgent stops.
    if b.id == fh_bin_id:
        return rng.randint(82, 90)
    if b.id in {9, 18, 26, 30, 35}:
        return rng.randint(84, 97)
    roll = rng.random()
    if roll < 0.22:
        return rng.randint(80, 95)
    if roll < 0.48:
        return rng.randint(60, 79)
    return rng.randint(14, 58)


def _profile_battery(profile: DemoProfile, b: Bin, index: int, rng: random.Random, fh_bin_id: int) -> int:
    if profile == "quiet_day":
        return rng.randint(62, 98)
    if profile == "high_load" and index % 11 == 0:
        return rng.randint(16, 29)
    if profile == "hardware_focus" and b.id == fh_bin_id:
        return rng.randint(58, 76)
    if profile == "realistic_shift" and b.id in {8, 19, 32}:
        return rng.randint(18, 34)
    return rng.randint(42, 96)


def _solar_output(battery: int, rng: random.Random) -> tuple[float, bool]:
    is_charging = battery >= 35 and rng.random() > 0.18
    if not is_charging:
        return 0.0, False
    return round(rng.uniform(4.2, 12.5), 1), True


def _reset_bin(b: Bin, *, fill_level: int, battery: int, now: datetime, rng: random.Random) -> None:
    home_lat, home_lng = _home_coords(b)
    solar_output_w, is_charging = _solar_output(battery, rng)

    b.fill_level = _clamp_int(fill_level, 0, 100)
    b.battery = _clamp_int(battery, 0, 100)
    b.solar_output_w = solar_output_w
    b.is_charging = is_charging
    b.locked = False
    b.status = "idle"
    b.location_state = "home"
    b.movement_state = "home"
    b.current_lat = home_lat
    b.current_lng = home_lng
    if home_lat is not None and home_lng is not None:
        b.lat = home_lat
        b.lng = home_lng
    b.last_seen = now


def _seed_alerts(profile: DemoProfile, db: Session, bins: list[Bin], fh_bin_id: int, now: datetime) -> int:
    if profile not in {"realistic_shift", "high_load"}:
        return 0

    candidates = [b for b in bins if b.id != fh_bin_id]
    alert_bins = []
    if candidates:
        alert_bins.append(candidates[len(candidates) // 3])
    if profile == "high_load" and len(candidates) > 3:
        alert_bins.append(candidates[-4])

    event_types = ["hygiene_report", "tamper"]
    for idx, b in enumerate(alert_bins):
        db.add(SecurityEvent(bin_id=b.id, event_type=event_types[idx % len(event_types)], timestamp=now))
    return len(alert_bins)


def _summary(db: Session, *, profile: str | None, seed: int | None, fh_bin_id: int) -> DemoStatus:
    bins = db.query(Bin).all()
    fh = next((b for b in bins if b.id == fh_bin_id), None)
    sim_state = sim.get_speed()
    truck = truck_state.get()
    return DemoStatus(
        profile=profile,
        seed=seed,
        bins_total=len(bins),
        collectable_bins=sum(1 for b in bins if not b.locked and b.fill_level >= settings.collect_fill_threshold),
        critical_bins=sum(1 for b in bins if not b.locked and b.fill_level >= 80),
        locked_bins=sum(1 for b in bins if b.locked),
        open_alerts=db.query(SecurityEvent).filter(SecurityEvent.resolved == False).count(),
        pending_commands=db.query(Command).filter(Command.ack_at == None).count(),
        routes=db.query(Route).count(),
        fh_bin_id=fh_bin_id,
        fh_fill_level=fh.fill_level if fh else None,
        sim_speed=float(sim_state["speed"]),
        sim_paused=bool(sim_state["paused"]),
        truck_action=truck.get("action"),
    )


@router.get("/status", response_model=DemoStatus)
def get_demo_status(db: Session = Depends(get_db)):
    return _summary(db, profile=None, seed=None, fh_bin_id=22)


@router.post("/reset", response_model=DemoStatus)
def reset_demo(payload: DemoResetRequest, x_admin_token: str = Header(default=""), db: Session = Depends(get_db)):
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    seed = payload.seed if payload.seed is not None else int(time.time())
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)

    if payload.clear_history:
        db.query(Route).delete()
        db.query(Command).delete()
        db.query(SecurityEvent).delete()

    bins = db.query(Bin).order_by(Bin.id).all()
    for index, b in enumerate(bins):
        fill = _profile_fill(payload.profile, b, index, rng, payload.fh_bin_id)
        battery = _profile_battery(payload.profile, b, index, rng, payload.fh_bin_id)
        _reset_bin(b, fill_level=fill, battery=battery, now=now, rng=rng)

    if payload.include_alerts:
        _seed_alerts(payload.profile, db, bins, payload.fh_bin_id, now)

    sim.set_state(speed=payload.sim_speed, paused=payload.sim_paused)
    truck_state.update(
        lat=settings.depot_lat,
        lng=settings.depot_lng,
        action="idle",
        current_bin_id=None,
        load_units=0.0,
        capacity_units=settings.truck_capacity_units,
    )

    db.commit()
    return _summary(db, profile=payload.profile, seed=seed, fh_bin_id=payload.fh_bin_id)
