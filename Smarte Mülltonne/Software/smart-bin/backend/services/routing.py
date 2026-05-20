"""OSRM routing client — fetches real street geometry between coordinates.

OSRM public demo: https://router.project-osrm.org
API docs: http://project-osrm.org/docs/v5.24.0/api/#route-service

Important: OSRM expects `lng,lat` order (not lat,lng) in the URL path.
"""
import logging
import math
from typing import TypedDict

import httpx

from config import settings

logger = logging.getLogger(__name__)


class RouteResult(TypedDict):
    geometry: dict | None       # GeoJSON LineString {type, coordinates: [[lng,lat],...]}
    distance_m: int
    duration_s: int
    source: str                 # "osrm" | "fallback"


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lng1 = a
    lat2, lng2 = b
    dlat = (lat2 - lat1) * 111_000
    dlng = (lng2 - lng1) * 71_000
    return math.hypot(dlat, dlng)


def _fallback(coords: list[tuple[float, float]]) -> RouteResult:
    """Straight-line fallback when OSRM is unreachable."""
    total = sum(_haversine_m(coords[i], coords[i + 1]) for i in range(len(coords) - 1))
    return {
        "geometry": {
            "type": "LineString",
            "coordinates": [[lng, lat] for lat, lng in coords],
        },
        "distance_m": int(total),
        "duration_s": int(total / 8.0),   # assume 8 m/s (~29 km/h) average speed
        "source": "fallback",
    }


async def get_route_geometry(coords: list[tuple[float, float]]) -> RouteResult:
    """Fetch real street-level routing for a list of `(lat, lng)` waypoints.

    Returns GeoJSON LineString in `geometry` plus total `distance_m` and `duration_s`.
    Falls back to straight-line polyline if OSRM is unreachable.
    """
    if len(coords) < 2:
        raise ValueError("Need at least two coordinates to build a route")

    # OSRM wants lng,lat;lng,lat;...
    path_coords = ";".join(f"{lng},{lat}" for lat, lng in coords)
    url = f"{settings.osrm_base_url}/route/v1/driving/{path_coords}"
    params = {"overview": "full", "geometries": "geojson", "steps": "false"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            logger.warning("OSRM returned no route: %s", data.get("code"))
            return _fallback(coords)

        route = data["routes"][0]
        return {
            "geometry": route["geometry"],
            "distance_m": int(route["distance"]),
            "duration_s": int(route["duration"]),
            "source": "osrm",
        }
    except (httpx.HTTPError, ValueError, KeyError) as e:
        logger.warning("OSRM request failed, falling back to straight-line: %s", e)
        return _fallback(coords)
