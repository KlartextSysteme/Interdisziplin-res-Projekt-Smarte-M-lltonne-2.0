"""
Simulates the collection vehicle along the OSRM-computed route geometry.

Behaviour:
  1. Poll GET /routes/latest — if present and not completed, load it
  2. Walk along route.geometry.coordinates (real street points) at SPEED_MPS
  3. When within ARRIVAL_THRESHOLD_M of a waypoint bin, collect its fill volume
  4. If the truck would exceed capacity, return to depot, unload, then resume
  5. Continue until end of geometry
  6. POST /routes/{id}/complete, idle at depot until next route

Sim-speed: each tick polls GET /sim/speed. When speedup > 1, meters-per-tick
scales linearly (the inner loop advances through multiple geometry segments
per wall-clock second) while the tick interval itself stays steady — that keeps
the visual smooth up to 50×.

Run: python mock_truck.py
"""
import asyncio
import math
import httpx

BASE_URL = "http://localhost:8000"
SPEED_MPS = 8.0              # ~29 km/h
TICK_S = 1.0                 # position update interval
ARRIVAL_THRESHOLD_M = 35.0   # distance to bin to trigger "arrival"
EMPTY_PAUSE_S = 1.5          # how long the truck stops to empty a bin (at 1×)
TRUCK_CAPACITY_UNITS = 600.0 # one 100% bin contributes 100 units; 600 ≈ six full bins
UNLOAD_PAUSE_S = 2.5         # depot unloading pause at 1×


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lng1 = a
    lat2, lng2 = b
    dlat = (lat2 - lat1) * 111_000
    dlng = (lng2 - lng1) * 71_000
    return math.hypot(dlat, dlng)


async def get_sim_state(client: httpx.AsyncClient) -> tuple[float, bool]:
    """Returns (speed, paused). Defaults to (1.0, False) on error."""
    try:
        r = await client.get(f"{BASE_URL}/sim/speed", timeout=2.0)
        data = r.json()
        return float(data.get("speed", 1.0)), bool(data.get("paused", False))
    except Exception:
        return 1.0, False


async def get_sim_speed(client: httpx.AsyncClient) -> float:
    """Backwards-compat helper, returns just the speed multiplier."""
    speed, _ = await get_sim_state(client)
    return speed


async def post_position(
    client: httpx.AsyncClient,
    pos: tuple[float, float],
    action: str,
    bin_id: int | None,
    load_units: float,
):
    try:
        await client.post(
            f"{BASE_URL}/truck/position",
            json={
                "lat": round(pos[0], 6),
                "lng": round(pos[1], 6),
                "action": action,
                "current_bin_id": bin_id,
                "load_units": round(load_units, 1),
                "capacity_units": TRUCK_CAPACITY_UNITS,
            },
        )
    except Exception as e:
        print(f"[mock_truck] position error: {e}")


async def empty_bin(client: httpx.AsyncClient, bin_id: int) -> int:
    fill_level = await get_bin_fill(client, bin_id)
    try:
        await client.post(
            f"{BASE_URL}/bins/{bin_id}/update",
            json={"fill_level": 0, "status": "emptied"},
        )
        print(f"[mock_truck] bin {bin_id} emptied, collected {fill_level} units")
    except Exception as e:
        print(f"[mock_truck] empty error: {e}")
    return fill_level


async def get_depot(client: httpx.AsyncClient) -> tuple[float, float]:
    try:
        r = await client.get(f"{BASE_URL}/config/public")
        d = r.json()["depot"]
        return (d["lat"], d["lng"])
    except Exception:
        return (51.5700, 8.1020)


async def get_bin_coords(client: httpx.AsyncClient) -> dict[int, tuple[float, float]]:
    resp = await client.get(f"{BASE_URL}/bins")
    return {b["id"]: (b["lat"], b["lng"]) for b in resp.json()}


async def get_bin_fill(client: httpx.AsyncClient, bin_id: int) -> int:
    try:
        resp = await client.get(f"{BASE_URL}/bins/{bin_id}")
        data = resp.json()
        return max(0, min(100, int(data.get("fill_level", 0))))
    except Exception as e:
        print(f"[mock_truck] fill fetch error for bin {bin_id}: {e}")
        return 0


async def get_active_route(client: httpx.AsyncClient) -> dict | None:
    try:
        resp = await client.get(f"{BASE_URL}/routes/latest")
        route = resp.json()
        if route and not route.get("completed") and route.get("waypoints"):
            return route
    except Exception:
        pass
    return None


def advance_with_arrival_check(
    pos: tuple[float, float],
    coords: list[tuple[float, float]],
    seg_index: int,
    budget_m: float,
    waypoints: list[int],
    visited: set[int],
    bin_coords_map: dict[int, tuple[float, float]],
):
    """Walk up to `budget_m` meters through the geometry. STOP early if we touch
    an unvisited bin within ARRIVAL_THRESHOLD_M — Annäherungsprüfung läuft an
    jedem Geometrie-Eckpunkt, damit hohe sim-speeds keine Tonnen überspringen.
    Returns (pos, seg_index, hit_bin_id_or_None)."""
    while budget_m > 0 and seg_index < len(coords) - 1:
        target = coords[seg_index + 1]
        dist = haversine_m(pos, target)
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
        # Proximity check after every segment crossing / partial step
        for bid in waypoints:
            if bid in visited or bid not in bin_coords_map:
                continue
            if haversine_m(pos, bin_coords_map[bid]) <= ARRIVAL_THRESHOLD_M:
                return pos, seg_index, bid
    return pos, seg_index, None


async def drive_straight_to(
    client: httpx.AsyncClient,
    pos: tuple[float, float],
    target: tuple[float, float],
    action: str,
    load_units: float,
) -> tuple[float, float]:
    """Simple point-to-point movement for depot unload trips."""
    while haversine_m(pos, target) > 5.0:
        speed, paused = await get_sim_state(client)
        if paused:
            await post_position(client, pos, "paused", None, load_units)
            await asyncio.sleep(0.5)
            continue

        budget_m = SPEED_MPS * TICK_S * speed
        dist = haversine_m(pos, target)
        ratio = min(1.0, budget_m / dist) if dist > 0 else 1.0
        pos = (
            pos[0] + (target[0] - pos[0]) * ratio,
            pos[1] + (target[1] - pos[1]) * ratio,
        )
        await post_position(client, pos, action, None, load_units)
        await asyncio.sleep(TICK_S)
    return target


async def unload_at_depot(
    client: httpx.AsyncClient,
    pos: tuple[float, float],
    depot: tuple[float, float],
    load_units: float,
) -> tuple[tuple[float, float], float]:
    print(f"[mock_truck] capacity reached ({load_units:.1f}/{TRUCK_CAPACITY_UNITS:.0f}), returning to depot")
    pos = await drive_straight_to(client, pos, depot, "returning_full", load_units)

    speed, _ = await get_sim_state(client)
    await post_position(client, pos, "unloading", None, load_units)
    await asyncio.sleep(UNLOAD_PAUSE_S / max(speed, 1.0))

    load_units = 0.0
    await post_position(client, pos, "en_route", None, load_units)
    print("[mock_truck] unloaded at depot, resuming route")
    return pos, load_units


async def drive_route(
    client: httpx.AsyncClient,
    route: dict,
    pos: tuple[float, float],
    load_units: float,
) -> tuple[tuple[float, float], float]:
    """Walk along route.geometry.coordinates. Returns final position and load."""
    route_id = route["id"]
    waypoints: list[int] = route["waypoints"]
    geometry = route.get("geometry")
    depot = await get_depot(client)

    coords: list[tuple[float, float]] = []
    if geometry and geometry.get("coordinates"):
        # GeoJSON uses [lng, lat]; convert to (lat, lng)
        coords = [(lat, lng) for lng, lat in geometry["coordinates"]]
    else:
        # Fallback: straight-line through bin coordinates
        bin_coords = await get_bin_coords(client)
        coords = [bin_coords[i] for i in waypoints if i in bin_coords]

    if len(coords) < 2:
        print(f"[mock_truck] route {route_id} has no usable coordinates")
        return pos, load_units

    print(f"[mock_truck] driving route {route_id}: {len(coords)} geometry points, waypoints {waypoints}")

    bin_coords_map = await get_bin_coords(client)
    visited: set[int] = set()

    seg_index = 0
    pos = coords[0]

    while seg_index < len(coords) - 1:
        speed, paused = await get_sim_state(client)
        if paused:
            # Simulation eingefroren — Position halten, Tick auslassen
            await post_position(client, pos, "paused", None, load_units)
            await asyncio.sleep(0.5)
            continue
        budget_m = SPEED_MPS * TICK_S * speed
        pos, seg_index, hit_bin = advance_with_arrival_check(
            pos, coords, seg_index, budget_m,
            waypoints, visited, bin_coords_map,
        )

        if hit_bin is not None:
            waste_units = await get_bin_fill(client, hit_bin)
            if load_units > 0 and load_units + waste_units > TRUCK_CAPACITY_UNITS:
                pos, load_units = await unload_at_depot(client, pos, depot, load_units)

            await post_position(client, pos, "emptying", hit_bin, load_units)
            collected_units = await empty_bin(client, hit_bin)
            load_units = min(TRUCK_CAPACITY_UNITS, load_units + collected_units)
            visited.add(hit_bin)
            await post_position(client, pos, "en_route", None, load_units)
            await asyncio.sleep(EMPTY_PAUSE_S / max(speed, 1.0))
        else:
            action = "returning" if len(visited) == len(waypoints) else "en_route"
            await post_position(client, pos, action, None, load_units)

        await asyncio.sleep(TICK_S)

    try:
        await client.post(f"{BASE_URL}/routes/{route_id}/complete")
        print(f"[mock_truck] route {route_id} completed")
    except Exception as e:
        print(f"[mock_truck] complete error: {e}")

    if load_units > 0:
        pos, load_units = await unload_at_depot(client, pos, depot, load_units)

    return pos, load_units


async def drive():
    async with httpx.AsyncClient(timeout=10.0) as client:
        depot = await get_depot(client)
        pos = depot
        load_units = 0.0
        await post_position(client, pos, "idle", None, load_units)

        while True:
            route = await get_active_route(client)
            if not route:
                await post_position(client, pos, "idle", None, load_units)
                await asyncio.sleep(3)
                continue

            pos, load_units = await drive_route(client, route, pos, load_units)
            await post_position(client, pos, "idle", None, load_units)


if __name__ == "__main__":
    asyncio.run(drive())
