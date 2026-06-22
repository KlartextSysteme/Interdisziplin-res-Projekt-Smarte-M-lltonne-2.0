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
from services.routing import get_route_geometry

logger = logging.getLogger(__name__)

SPEED_MPS = 8.0
BIN_SPEED_MPS = 1.4
TICK_S = 0.25
ARRIVAL_THRESHOLD_M = 10.0
EMPTY_PAUSE_S = 6.0
BIN_READY_BUFFER_S = 2.5
BIN_MAX_WAIT_S = 18.0
# Gemeinsame Wahrheit mit der Routenplanung (config), damit geplante und
# gefahrene Route bei Kapazität/Schwelle nicht auseinanderlaufen.
COLLECT_FILL_THRESHOLD = settings.collect_fill_threshold
TRUCK_CAPACITY_UNITS = settings.truck_capacity_units
UNLOAD_PAUSE_S = 2.5

_bin_move_tasks: dict[int, asyncio.Task] = {}


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
    route = (
        db.query(Route)
        .filter(Route.active == True)
        .order_by(Route.created_at.desc())
        .first()
    )
    if route and not route.completed and route.waypoints:
        return route
    return None


def _bin_coords(db: Session) -> dict[int, tuple[float, float]]:
    return {
        b.id: (
            b.pickup_lat if b.pickup_lat is not None else b.lat,
            b.pickup_lng if b.pickup_lng is not None else b.lng,
        )
        for b in db.query(Bin).all()
    }


def _bin_fill(db: Session, bin_id: int) -> int:
    b = db.query(Bin).filter(Bin.id == bin_id).first()
    if not b:
        return 0
    return _bin_fill_value(b)


def _bin_fill_value(b: Bin) -> int:
    return max(0, min(100, int(b.fill_level or 0)))


def _is_collectable_bin(b: Bin | None) -> bool:
    return bool(b and not b.locked and _bin_fill_value(b) >= COLLECT_FILL_THRESHOLD)


def _empty_bin(db: Session, bin_id: int) -> int:
    b = db.query(Bin).filter(Bin.id == bin_id).first()
    if not b:
        return 0
    collected = _bin_fill_value(b)
    b.fill_level = 0
    b.status = "emptied"
    if b.pickup_lat is not None and b.pickup_lng is not None:
        b.current_lat = b.pickup_lat
        b.current_lng = b.pickup_lng
        b.lat = b.pickup_lat
        b.lng = b.pickup_lng
    b.location_state = "truck"
    b.movement_state = "pickup"
    db.commit()
    logger.info("truck simulator emptied bin %s, collected %s units", bin_id, collected)
    return collected


def _bin_current_coords(b: Bin) -> tuple[float, float]:
    return (
        b.current_lat if b.current_lat is not None else b.lat,
        b.current_lng if b.current_lng is not None else b.lng,
    )


def _bin_target_coords(b: Bin, target: str) -> tuple[float, float] | None:
    if target == "pickup" and b.pickup_lat is not None and b.pickup_lng is not None:
        return b.pickup_lat, b.pickup_lng
    if target == "home" and b.home_lat is not None and b.home_lng is not None:
        return b.home_lat, b.home_lng
    return None


def _set_bin_position(b: Bin, pos: tuple[float, float]):
    lat, lng = pos
    b.current_lat = round(lat, 6)
    b.current_lng = round(lng, 6)
    # Keep legacy lat/lng as the current live marker position.
    b.lat = b.current_lat
    b.lng = b.current_lng


async def _move_bin_to(bin_id: int, target: str, delay_s: float = 0.0):
    if delay_s > 0:
        elapsed = 0.0
        while elapsed < delay_s:
            speed, paused = _sim_state()
            if not paused:
                elapsed += TICK_S * max(speed, 0.1)
            await asyncio.sleep(TICK_S)

    db = SessionLocal()
    try:
        b = db.query(Bin).filter(Bin.id == bin_id).first()
        if not b:
            return

        start = _bin_current_coords(b)
        end = _bin_target_coords(b, target)
        if not end:
            return

        dist_m = _haversine_m(start, end)
        if dist_m < 1:
            _set_bin_position(b, end)
            b.location_state = "truck" if target == "pickup" else "home"
            b.movement_state = "pickup" if target == "pickup" else "home"
            db.commit()
            return

        b.location_state = "moving_to_pickup" if target == "pickup" else "moving_home"
        b.movement_state = b.location_state
        db.commit()

        travelled_m = 0.0
        while travelled_m < dist_m:
            speed, paused = _sim_state()
            if paused:
                await asyncio.sleep(0.5)
                continue

            travelled_m = min(dist_m, travelled_m + BIN_SPEED_MPS * TICK_S * speed)
            ratio = travelled_m / dist_m
            pos = (
                start[0] + (end[0] - start[0]) * ratio,
                start[1] + (end[1] - start[1]) * ratio,
            )

            b = db.query(Bin).filter(Bin.id == bin_id).first()
            if not b:
                return
            _set_bin_position(b, pos)
            b.location_state = "moving_to_pickup" if target == "pickup" else "moving_home"
            b.movement_state = b.location_state
            db.commit()
            await asyncio.sleep(TICK_S)

        b = db.query(Bin).filter(Bin.id == bin_id).first()
        if not b:
            return
        _set_bin_position(b, end)
        b.location_state = "truck" if target == "pickup" else "home"
        b.movement_state = "pickup" if target == "pickup" else "home"
        db.commit()
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("bin movement failed for bin %s to %s", bin_id, target)
    finally:
        db.close()


def _schedule_bin_move(bin_id: int, target: str, delay_s: float = 0.0) -> asyncio.Task:
    old_task = _bin_move_tasks.get(bin_id)
    if old_task and not old_task.done():
        old_task.cancel()

    task = asyncio.create_task(_move_bin_to(bin_id, target, delay_s=delay_s))
    _bin_move_tasks[bin_id] = task

    def _cleanup(done_task: asyncio.Task, bid: int = bin_id):
        if _bin_move_tasks.get(bid) is done_task:
            _bin_move_tasks.pop(bid, None)

    task.add_done_callback(_cleanup)
    return task


def _route_progress_m(coords: list[tuple[float, float]]) -> list[float]:
    progress = [0.0]
    for index in range(len(coords) - 1):
        progress.append(progress[-1] + _haversine_m(coords[index], coords[index + 1]))
    return progress


def _route_xy_m(
    pos: tuple[float, float],
    origin_lat: float,
) -> tuple[float, float]:
    lat, lng = pos
    lng_m = 111_000 * math.cos(math.radians(origin_lat))
    return lng * lng_m, lat * 111_000


def _project_point_to_route_m(
    point: tuple[float, float],
    coords: list[tuple[float, float]],
    progress: list[float],
    min_progress_m: float = 0.0,
) -> tuple[float, float]:
    if len(coords) < 2:
        return 0.0, 0.0

    origin_lat = sum(lat for lat, _ in coords) / len(coords)
    px, py = _route_xy_m(point, origin_lat)
    best_any: tuple[float, float] | None = None
    best_after_min: tuple[float, float] | None = None

    for index in range(len(coords) - 1):
        ax, ay = _route_xy_m(coords[index], origin_lat)
        bx, by = _route_xy_m(coords[index + 1], origin_lat)
        vx = bx - ax
        vy = by - ay
        seg_len_sq = vx * vx + vy * vy
        if seg_len_sq <= 0:
            continue

        t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / seg_len_sq))
        proj_x = ax + vx * t
        proj_y = ay + vy * t
        off_route_m = math.hypot(px - proj_x, py - proj_y)
        route_m = progress[index] + (progress[index + 1] - progress[index]) * t
        candidate = (off_route_m, route_m)

        if best_any is None or candidate[0] < best_any[0]:
            best_any = candidate
        if route_m >= min_progress_m and (
            best_after_min is None or candidate[0] < best_after_min[0]
        ):
            best_after_min = candidate

    best = best_after_min or best_any
    if best is None:
        return 0.0, 0.0
    off_route_m, route_m = best
    return route_m, off_route_m


def _truck_arrival_eta_s(
    route_m: float,
    off_route_m: float,
    previous_stops: int,
) -> float:
    return (route_m / SPEED_MPS) + previous_stops * EMPTY_PAUSE_S


def _schedule_route_bins_to_pickup(
    db: Session,
    waypoints: list[int],
    stop_progress_by_bin: dict[int, float],
) -> dict[int, float]:
    if not waypoints:
        return {}

    bins = {
        b.id: b
        for b in db.query(Bin).filter(Bin.id.in_(waypoints)).all()
    }

    for index, bin_id in enumerate(waypoints):
        b = bins.get(bin_id)
        route_m = stop_progress_by_bin.get(bin_id)
        if route_m is None or not _is_collectable_bin(b):
            continue

        truck_eta_s = _truck_arrival_eta_s(route_m, 0.0, index)
        target = _bin_target_coords(b, "pickup")
        if not target:
            continue

        bin_travel_s = _haversine_m(_bin_current_coords(b), target) / BIN_SPEED_MPS
        delay_s = max(0.0, truck_eta_s - bin_travel_s - BIN_READY_BUFFER_S)
        _schedule_bin_move(bin_id, "pickup", delay_s=delay_s)
        logger.info(
            "scheduled bin %s to pickup in %.1fs (truck eta %.1fs, bin travel %.1fs)",
            bin_id,
            delay_s,
            truck_eta_s,
            bin_travel_s,
        )

    return stop_progress_by_bin


def _collectable_route_waypoints(db: Session, waypoints: list[int]) -> tuple[list[int], list[int]]:
    if not waypoints:
        return [], []

    bins = {
        b.id: b
        for b in db.query(Bin).filter(Bin.id.in_(waypoints)).all()
    }
    collectable: list[int] = []
    skipped: list[int] = []
    for bin_id in waypoints:
        if _is_collectable_bin(bins.get(bin_id)):
            collectable.append(bin_id)
        else:
            skipped.append(bin_id)
    return collectable, skipped


def _send_skipped_bins_home(db: Session, bin_ids: list[int]):
    if not bin_ids:
        return

    for b in db.query(Bin).filter(Bin.id.in_(bin_ids)).all():
        if _is_collectable_bin(b):
            continue
        if b.location_state == "home" and b.movement_state == "home":
            continue
        if _bin_target_coords(b, "home"):
            _schedule_bin_move(b.id, "home")


def _next_unvisited_waypoint(waypoints: list[int], visited: set[int]) -> int | None:
    for bin_id in waypoints:
        if bin_id not in visited:
            return bin_id
    return None


def _position_at_route_progress(
    coords: list[tuple[float, float]],
    progress: list[float],
    target_m: float,
) -> tuple[tuple[float, float], int]:
    if not coords:
        return (0.0, 0.0), 0
    if len(coords) == 1 or not progress:
        return coords[0], 0
    if target_m <= 0:
        return coords[0], 0
    if target_m >= progress[-1]:
        return coords[-1], len(coords) - 1

    for index in range(len(coords) - 1):
        start_m = progress[index]
        end_m = progress[index + 1]
        if target_m > end_m:
            continue

        seg_len = max(end_m - start_m, 0.0)
        ratio = (target_m - start_m) / seg_len if seg_len > 0 else 0.0
        return (
            (
                coords[index][0] + (coords[index + 1][0] - coords[index][0]) * ratio,
                coords[index][1] + (coords[index + 1][1] - coords[index][1]) * ratio,
            ),
            index,
        )

    return coords[-1], len(coords) - 1


def _advance_with_planned_stop(
    pos: tuple[float, float],
    coords: list[tuple[float, float]],
    progress: list[float],
    seg_index: int,
    route_progress_m: float,
    budget_m: float,
    stop_progress_m: float | None,
) -> tuple[tuple[float, float], int, float, bool]:
    if len(coords) < 2:
        return pos, seg_index, route_progress_m, False

    target_progress_m = min(progress[-1], route_progress_m + budget_m)
    if stop_progress_m is not None:
        if stop_progress_m <= route_progress_m + 0.5:
            return pos, seg_index, route_progress_m, True
        if stop_progress_m <= target_progress_m:
            stop_pos, stop_seg_index = _position_at_route_progress(
                coords,
                progress,
                stop_progress_m,
            )
            return stop_pos, stop_seg_index, stop_progress_m, True

    next_pos, next_seg_index = _position_at_route_progress(
        coords,
        progress,
        target_progress_m,
    )
    return next_pos, next_seg_index, target_progress_m, False


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


async def _route_coords_between(
    start: tuple[float, float],
    target: tuple[float, float],
) -> list[tuple[float, float]]:
    result = await get_route_geometry([start, target])
    geometry = result.get("geometry")
    if not geometry or not geometry.get("coordinates"):
        return [start, target]

    coords = [(lat, lng) for lng, lat in geometry["coordinates"]]
    if len(coords) < 2:
        return [start, target]

    # OSRM may snap start/end to the nearest road. Keep simulator state exact at
    # the handoff points, then follow the returned street geometry in between.
    coords[0] = start
    coords[-1] = target
    return coords


async def _coords_for_waypoint_legs(
    start: tuple[float, float],
    waypoints: list[int],
    bin_coords: dict[int, tuple[float, float]],
) -> tuple[list[tuple[float, float]], dict[int, float]]:
    targets = [bin_coords[bin_id] for bin_id in waypoints if bin_id in bin_coords]
    pickup_points = [start] + targets
    if len(pickup_points) < 2:
        return [start], {}

    result = await get_route_geometry(pickup_points)
    legs = result.get("legs") or []
    coords: list[tuple[float, float]] = [start]
    stop_progress_by_bin: dict[int, float] = {}
    total_m = 0.0

    usable_waypoints = [bin_id for bin_id in waypoints if bin_id in bin_coords]
    for index in range(len(pickup_points) - 1):
        target = pickup_points[index + 1]
        leg = legs[index] if index < len(legs) else {}
        geometry = leg.get("geometry") if isinstance(leg, dict) else None
        leg_coords = (
            [(lat, lng) for lng, lat in geometry["coordinates"]]
            if geometry and geometry.get("coordinates")
            else [coords[-1], target]
        )
        if len(leg_coords) < 2:
            leg_coords = [coords[-1], target]

        leg_coords[0] = coords[-1]
        leg_coords[-1] = target
        for point in leg_coords[1:]:
            total_m += _haversine_m(coords[-1], point)
            coords.append(point)

        if index < len(usable_waypoints):
            stop_progress_by_bin[usable_waypoints[index]] = total_m

    # The depot return should not inherit the pickup shortcut logic. Calculate it
    # as its own best street route from the final pickup position back to depot.
    depot = _depot()
    if _haversine_m(coords[-1], depot) > 2:
        return_coords = await _route_coords_between(coords[-1], depot)
        for point in return_coords[1:]:
            total_m += _haversine_m(coords[-1], point)
            coords.append(point)

    return coords, stop_progress_by_bin


async def _drive_geometry(
    pos: tuple[float, float],
    coords: list[tuple[float, float]],
    action: str,
    load_units: float,
) -> tuple[float, float]:
    if len(coords) < 2:
        return pos

    seg_index = 0
    while seg_index < len(coords) - 1:
        speed, paused = _sim_state()
        if paused:
            _post_position(pos, "paused", None, load_units)
            await asyncio.sleep(0.5)
            continue

        budget_m = SPEED_MPS * TICK_S * speed
        pos, seg_index, _ = _advance_with_arrival_check(
            pos,
            coords,
            seg_index,
            budget_m,
            [],
            set(),
            {},
        )
        _post_position(pos, action, None, load_units)
        await asyncio.sleep(TICK_S)
    return coords[-1]


async def _drive_to(
    pos: tuple[float, float],
    target: tuple[float, float],
    action: str,
    load_units: float,
) -> tuple[float, float]:
    coords = await _route_coords_between(pos, target)
    return await _drive_geometry(pos, coords, action, load_units)


async def _hold_position(
    pos: tuple[float, float],
    action: str,
    bin_id: int | None,
    load_units: float,
    duration_s: float,
):
    elapsed = 0.0
    while elapsed < duration_s:
        speed, paused = _sim_state()
        if paused:
            _post_position(pos, "paused", bin_id, load_units)
            await asyncio.sleep(0.5)
            continue

        _post_position(pos, action, bin_id, load_units)
        elapsed += TICK_S * max(speed, 0.1)
        await asyncio.sleep(TICK_S)


async def _wait_for_bin_at_pickup(
    bin_id: int,
    pos: tuple[float, float],
    load_units: float,
):
    elapsed = 0.0
    while elapsed < BIN_MAX_WAIT_S:
        db = SessionLocal()
        try:
            b = db.query(Bin).filter(Bin.id == bin_id).first()
            if not b:
                return
            if not _is_collectable_bin(b):
                return

            target = _bin_target_coords(b, "pickup")
            if not target:
                return

            is_ready = (
                b.location_state == "truck"
                or b.movement_state == "pickup"
                or _haversine_m(_bin_current_coords(b), target) < 2.0
            )
            if is_ready:
                return
        finally:
            db.close()

        speed, paused = _sim_state()
        if paused:
            _post_position(pos, "paused", bin_id, load_units)
            await asyncio.sleep(0.5)
            continue

        _post_position(pos, "emptying", bin_id, load_units)
        elapsed += TICK_S * max(speed, 0.1)
        await asyncio.sleep(TICK_S)


async def _unload_at_depot(
    pos: tuple[float, float],
    load_units: float,
    resume_pos: tuple[float, float] | None = None,
) -> tuple[tuple[float, float], float]:
    depot = _depot()
    if _haversine_m(pos, depot) > 5:
        pos = await _drive_to(pos, depot, "returning_full", load_units)
    _post_position(pos, "unloading", None, load_units)
    await _hold_position(pos, "unloading", None, load_units, UNLOAD_PAUSE_S)
    load_units = 0.0
    _post_position(pos, "en_route", None, load_units)

    if resume_pos is not None:
        pos = await _drive_to(pos, resume_pos, "returning", load_units)

    return pos, load_units


async def _drive_route(route_id: int, pos: tuple[float, float], load_units: float) -> tuple[tuple[float, float], float]:
    db = SessionLocal()
    try:
        route = db.query(Route).filter(Route.id == route_id).first()
        if not route or route.completed or not route.waypoints:
            return pos, load_units

        bin_coords = _bin_coords(db)
        waypoints, skipped_waypoints = _collectable_route_waypoints(db, list(route.waypoints))
        if skipped_waypoints:
            logger.info(
                "truck simulator skipped %s non-collectable route bins: %s",
                len(skipped_waypoints),
                skipped_waypoints,
            )
            _send_skipped_bins_home(db, skipped_waypoints)
            route.waypoints = waypoints
            db.commit()

        if not waypoints:
            route.completed = True
            route.geometry = None
            route.distance_m = 0
            route.duration_s = 0
            db.commit()
            logger.info("truck simulator completed route %s: no collectable bins left", route.id)
            return pos, load_units

        coords, stop_progress_by_bin = await _coords_for_waypoint_legs(pos, waypoints, bin_coords)
        if len(coords) < 2:
            logger.warning("truck simulator route %s has no usable coordinates", route.id)
            return pos, load_units

        logger.info("truck simulator driving route %s with %s geometry points", route.id, len(coords))
        route_progress = _route_progress_m(coords)
        route.geometry = {
            "type": "LineString",
            "coordinates": [[lng, lat] for lat, lng in coords],
        }
        route.distance_m = int(route_progress[-1])
        route.duration_s = int(route.distance_m / SPEED_MPS)
        db.commit()
        _schedule_route_bins_to_pickup(db, waypoints, stop_progress_by_bin)
        visited: set[int] = set()
        seg_index = 0
        route_progress_m = 0.0
        pos = coords[0]

        while seg_index < len(coords) - 1:
            speed, paused = _sim_state()
            if paused:
                _post_position(pos, "paused", None, load_units)
                await asyncio.sleep(0.5)
                continue

            # Wurde währenddessen ein anderer Kandidat aktiviert? Dann diese Fahrt
            # abbrechen — der Haupt-Loop übernimmt die neue aktive Route.
            if not db.query(Route.active).filter(Route.id == route_id).scalar():
                logger.info("truck simulator route %s superseded → switching", route_id)
                _post_position(pos, "en_route", None, load_units)
                return pos, load_units

            budget_m = SPEED_MPS * TICK_S * speed
            next_bin = _next_unvisited_waypoint(waypoints, visited)
            next_stop_m = stop_progress_by_bin.get(next_bin) if next_bin is not None else None
            pos, seg_index, route_progress_m, reached_stop = _advance_with_planned_stop(
                pos,
                coords,
                route_progress,
                seg_index,
                route_progress_m,
                budget_m,
                next_stop_m,
            )
            hit_bin = next_bin if reached_stop else None

            if hit_bin is not None:
                pos = bin_coords.get(hit_bin, pos)
                await _wait_for_bin_at_pickup(hit_bin, pos, load_units)
                db.expire_all()
                hit = db.query(Bin).filter(Bin.id == hit_bin).first()
                if not _is_collectable_bin(hit):
                    logger.info("truck simulator skipped non-collectable bin %s at pickup", hit_bin)
                    visited.add(hit_bin)
                    _schedule_bin_move(hit_bin, "home")
                    _post_position(pos, "en_route", None, load_units)
                    await asyncio.sleep(TICK_S)
                    continue

                waste_units = _bin_fill_value(hit)
                if load_units > 0 and load_units + waste_units > TRUCK_CAPACITY_UNITS:
                    pos, load_units = await _unload_at_depot(pos, load_units, resume_pos=pos)

                _post_position(pos, "emptying", hit_bin, load_units)
                await _hold_position(pos, "emptying", hit_bin, load_units, EMPTY_PAUSE_S)
                collected_units = _empty_bin(db, hit_bin)
                load_units = min(TRUCK_CAPACITY_UNITS, load_units + collected_units)
                visited.add(hit_bin)
                _schedule_bin_move(hit_bin, "home", delay_s=2.0)
                _post_position(pos, "en_route", None, load_units)
            else:
                action = "returning" if len(visited) == len(waypoints) else "en_route"
                _post_position(pos, action, None, load_units)

            await asyncio.sleep(TICK_S)

        route.completed = True
        route.active = False
        db.commit()

        if load_units > 0:
            pos, load_units = await _unload_at_depot(pos, load_units)

        logger.info("truck simulator route %s completed", route.id)
        return pos, load_units
    finally:
        db.close()


async def _maybe_plan_next_trip(prev_route_id: int):
    """Nach Abschluss einer kapazitätsbegrenzten Fahrt: wenn noch volle Tonnen
    übrig sind, automatisch die nächste Fahrt planen. Beendet die Kette, sobald
    keine sammelbaren Tonnen mehr da sind."""
    db = SessionLocal()
    try:
        prev = db.query(Route).filter(Route.id == prev_route_id).first()
        # Nur weiterplanen, wenn die vorige Route wirklich fertig ist (nicht durch
        # Kandidaten-Auswahl ersetzt wurde).
        if not prev or not prev.completed:
            return
        remaining = sum(1 for b in db.query(Bin).all() if _is_collectable_bin(b))
        if remaining == 0:
            logger.info("truck simulator: keine vollen Tonnen mehr → Trip-Kette beendet")
            return
        # Lazy import vermeidet Import-Zyklus router<->service.
        from routers.routes import generate_route_candidates
        await generate_route_candidates(db)
        logger.info("truck simulator: Auto-Replan, %d Tonnen übrig → nächster Trip", remaining)
    except Exception as e:
        logger.warning("truck simulator auto-replan failed: %s", e)
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

        # Auto-Replan: hat der Wagen die Route abgeschlossen (nicht durch
        # Kandidaten-Auswahl ersetzt) und sind noch volle Tonnen übrig, plane die
        # nächste kapazitätsbegrenzte Fahrt (Mehr-Trip-Kette).
        await _maybe_plan_next_trip(route_id)


def start_truck_simulator() -> asyncio.Task:
    task = asyncio.create_task(run_truck_simulator())
    return task


async def stop_truck_simulator(task: asyncio.Task | None):
    for move_task in list(_bin_move_tasks.values()):
        move_task.cancel()
    if _bin_move_tasks:
        await asyncio.gather(*_bin_move_tasks.values(), return_exceptions=True)
        _bin_move_tasks.clear()
    if task is None:
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
