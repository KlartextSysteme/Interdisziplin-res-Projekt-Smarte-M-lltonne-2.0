import asyncio
import contextlib
import logging
import math

from sqlalchemy.orm import Session

import truck_state
from config import settings
from database import SessionLocal
from models.bin import Bin
from models.route import Route
from routers import sim

logger = logging.getLogger(__name__)

SPEED_MPS = 8.0
TICK_S = 1.0
ARRIVAL_THRESHOLD_M = 35.0
EMPTY_PAUSE_S = 1.5
TRUCK_CAPACITY_UNITS = 600.0
UNLOAD_PAUSE_S = 2.5


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lng1 = a
    lat2, lng2 = b
    dlat = (lat2 - lat1) * 111_000
    dlng = (lng2 - lng1) * 71_000
    return math.hypot(dlat, dlng)


def _sim_state() -> tuple[float, bool]:
    return float(sim._state.get("speed", 1.0)), bool(sim._state.get("paused", False))


def _depot() -> tuple[float, float]:
    return settings.depot_lat, settings.depot_lng


def _post_position(
    pos: tuple[float, float],
    action: str,
    bin_id: int | None,
    load_units: float,
):
    truck_state.update(
        lat=round(pos[0], 6),
        lng=round(pos[1], 6),
        action=action,
        current_bin_id=bin_id,
        load_units=round(load_units, 1),
        capacity_units=TRUCK_CAPACITY_UNITS,
    )


def _latest_active_route(db: Session) -> Route | None:
    route = db.query(Route).order_by(Route.created_at.desc()).first()
    if route and not route.completed and route.waypoints:
        return route
    return None


def _bin_coords(db: Session) -> dict[int, tuple[float, float]]:
    return {b.id: (b.lat, b.lng) for b in db.query(Bin).all()}


def _bin_fill(db: Session, bin_id: int) -> int:
    b = db.query(Bin).filter(Bin.id == bin_id).first()
    if not b:
        return 0
    return max(0, min(100, int(b.fill_level)))


def _empty_bin(db: Session, bin_id: int) -> int:
    b = db.query(Bin).filter(Bin.id == bin_id).first()
    if not b:
        return 0
    collected = max(0, min(100, int(b.fill_level)))
    b.fill_level = 0
    b.status = "emptied"
    db.commit()
    logger.info("truck simulator emptied bin %s, collected %s units", bin_id, collected)
    return collected


def _coords_for_route(route: Route, bin_coords: dict[int, tuple[float, float]]) -> list[tuple[float, float]]:
    geometry = route.geometry
    if geometry and geometry.get("coordinates"):
        return [(lat, lng) for lng, lat in geometry["coordinates"]]
    return [bin_coords[i] for i in route.waypoints if i in bin_coords]


def _advance_with_arrival_check(
    pos: tuple[float, float],
    coords: list[tuple[float, float]],
    seg_index: int,
    budget_m: float,
    waypoints: list[int],
    visited: set[int],
    bin_coords: dict[int, tuple[float, float]],
) -> tuple[tuple[float, float], int, int | None]:
    while budget_m > 0 and seg_index < len(coords) - 1:
        target = coords[seg_index + 1]
        dist = _haversine_m(pos, target)
        if dist <= budget_m:
            pos = target
            budget_m -= dist
            seg_index += 1
        else:
            ratio = budget_m / dist if dist > 0 else 0
            pos = (
                pos[0] + (target[0] - pos[0]) * ratio,
                pos[1] + (target[1] - pos[1]) * ratio,
            )
            budget_m = 0

        for bid in waypoints:
            if bid in visited or bid not in bin_coords:
                continue
            if _haversine_m(pos, bin_coords[bid]) <= ARRIVAL_THRESHOLD_M:
                return pos, seg_index, bid

    return pos, seg_index, None


async def _drive_to(
    pos: tuple[float, float],
    target: tuple[float, float],
    action: str,
    load_units: float,
) -> tuple[float, float]:
    while _haversine_m(pos, target) > 5.0:
        speed, paused = _sim_state()
        if paused:
            _post_position(pos, "paused", None, load_units)
            await asyncio.sleep(0.5)
            continue

        budget_m = SPEED_MPS * TICK_S * speed
        dist = _haversine_m(pos, target)
        ratio = min(1.0, budget_m / dist) if dist > 0 else 1.0
        pos = (
            pos[0] + (target[0] - pos[0]) * ratio,
            pos[1] + (target[1] - pos[1]) * ratio,
        )
        _post_position(pos, action, None, load_units)
        await asyncio.sleep(TICK_S)
    return target


async def _unload_at_depot(
    pos: tuple[float, float],
    load_units: float,
) -> tuple[tuple[float, float], float]:
    depot = _depot()
    pos = await _drive_to(pos, depot, "returning_full", load_units)
    speed, _ = _sim_state()
    _post_position(pos, "unloading", None, load_units)
    await asyncio.sleep(UNLOAD_PAUSE_S / max(speed, 1.0))
    load_units = 0.0
    _post_position(pos, "en_route", None, load_units)
    return pos, load_units


async def _drive_route(route_id: int, pos: tuple[float, float], load_units: float) -> tuple[tuple[float, float], float]:
    db = SessionLocal()
    try:
        route = db.query(Route).filter(Route.id == route_id).first()
        if not route or route.completed or not route.waypoints:
            return pos, load_units

        bin_coords = _bin_coords(db)
        coords = _coords_for_route(route, bin_coords)
        if len(coords) < 2:
            logger.warning("truck simulator route %s has no usable coordinates", route.id)
            return pos, load_units

        logger.info("truck simulator driving route %s with %s geometry points", route.id, len(coords))
        waypoints = list(route.waypoints)
        visited: set[int] = set()
        seg_index = 0
        pos = coords[0]

        while seg_index < len(coords) - 1:
            speed, paused = _sim_state()
            if paused:
                _post_position(pos, "paused", None, load_units)
                await asyncio.sleep(0.5)
                continue

            budget_m = SPEED_MPS * TICK_S * speed
            pos, seg_index, hit_bin = _advance_with_arrival_check(
                pos,
                coords,
                seg_index,
                budget_m,
                waypoints,
                visited,
                bin_coords,
            )

            if hit_bin is not None:
                waste_units = _bin_fill(db, hit_bin)
                if load_units > 0 and load_units + waste_units > TRUCK_CAPACITY_UNITS:
                    pos, load_units = await _unload_at_depot(pos, load_units)

                _post_position(pos, "emptying", hit_bin, load_units)
                collected_units = _empty_bin(db, hit_bin)
                load_units = min(TRUCK_CAPACITY_UNITS, load_units + collected_units)
                visited.add(hit_bin)
                _post_position(pos, "en_route", None, load_units)
                await asyncio.sleep(EMPTY_PAUSE_S / max(speed, 1.0))
            else:
                action = "returning" if len(visited) == len(waypoints) else "en_route"
                _post_position(pos, action, None, load_units)

            await asyncio.sleep(TICK_S)

        route.completed = True
        db.commit()

        if load_units > 0:
            pos, load_units = await _unload_at_depot(pos, load_units)

        logger.info("truck simulator route %s completed", route.id)
        return pos, load_units
    finally:
        db.close()


async def run_truck_simulator():
    pos = _depot()
    load_units = 0.0
    _post_position(pos, "idle", None, load_units)
    logger.info("truck simulator started at depot")

    while True:
        db = SessionLocal()
        try:
            route = _latest_active_route(db)
            route_id = route.id if route else None
        finally:
            db.close()

        if route_id is None:
            _post_position(pos, "idle", None, load_units)
            await asyncio.sleep(3)
            continue

        pos, load_units = await _drive_route(route_id, pos, load_units)
        _post_position(pos, "idle", None, load_units)


def start_truck_simulator() -> asyncio.Task:
    task = asyncio.create_task(run_truck_simulator())
    return task


async def stop_truck_simulator(task: asyncio.Task | None):
    if task is None:
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
