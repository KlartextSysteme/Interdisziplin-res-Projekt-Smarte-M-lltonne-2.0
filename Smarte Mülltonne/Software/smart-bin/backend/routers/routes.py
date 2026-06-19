"""Route planning: Füllstand-Threshold + stabile Sammelreihenfolge.

Für die Live-Demo ist eine nachvollziehbare Sammelfahrt wichtiger als eine
mathematisch kurze Rundtour, die in engen Clustern Tonnen überspringt und später
wieder zurückkommt. Die Fahrreihenfolge nutzt deshalb deterministisch
Nearest-Neighbour als "Street sweep". 2-opt bleibt als Vergleichswert im Code,
wird aber nicht als Fahrreihenfolge genutzt.

Distanzen für die Heuristik: planar (equirectangular). OSRM liefert danach die
echte Straßen-Geometrie auf der finalen Reihenfolge.
"""
import logging
from math import cos, radians, sqrt

import numpy as np
from fastapi import APIRouter, Depends
from python_tsp.heuristics import solve_tsp_local_search
from python_tsp.exact import solve_tsp_dynamic_programming
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.bin import Bin
from models.route import Route
from services.routing import get_route_geometry

logger = logging.getLogger(__name__)
router = APIRouter()

# Nur Tonnen ab diesem Füllstand werden angefahren — entspricht der Agent-Regel
# „Tonnen < 30 % lohnen sich selten"; 60 % bildet die Abhol-Schwelle.
FILL_THRESHOLD = 60

# Held-Karp DP ist O(n²·2ⁿ). Bei n ≤ 15 läuft das in <1s, ab n=16 wirds zäh.
# Gate so gewählt, dass die Demo nicht hängt, aber bei kleinen Instanzen
# das Optimum als Referenz für 2-opt verifiziert werden kann.
EXACT_TSP_MAX_NODES = 15


# ── Distanz-Helfer ────────────────────────────────────────────────────────────

def _planar_dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Equirectangular approximation in *Grad*, ausreichend für <10 km Cluster.
    Wir behalten Grad statt Meter, weil 2-opt nur relative Distanzen vergleicht.
    Für die Badge-Anzeige rechnen wir am Ende auf Meter um."""
    lat1, lng1 = a
    lat2, lng2 = b
    mean_lat = radians((lat1 + lat2) / 2)
    dx = (lng2 - lng1) * cos(mean_lat)
    dy = lat2 - lat1
    return sqrt(dx * dx + dy * dy)


def _planar_to_meters(d_deg: float) -> int:
    """1° latitude ≈ 111 km — grobe Konvertierung für Anzeige-Zwecke."""
    return int(d_deg * 111_000)


def _tour_length(coords: list[tuple[float, float]], perm: list[int]) -> float:
    """Closed-tour length in plain planar units (Grad)."""
    total = 0.0
    for i in range(len(perm)):
        a = coords[perm[i]]
        b = coords[perm[(i + 1) % len(perm)]]
        total += _planar_dist(a, b)
    return total


def _build_distance_matrix(coords: list[tuple[float, float]]) -> np.ndarray:
    n = len(coords)
    m = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(i + 1, n):
            d = _planar_dist(coords[i], coords[j])
            m[i, j] = d
            m[j, i] = d
    return m


def _pickup_coords(b: Bin) -> tuple[float, float]:
    return (
        b.pickup_lat if b.pickup_lat is not None else b.lat,
        b.pickup_lng if b.pickup_lng is not None else b.lng,
    )


# ── Heuristiken ───────────────────────────────────────────────────────────────

def _nearest_neighbor_perm(matrix: np.ndarray) -> list[int]:
    """Greedy: starte am Knoten 0 (Depot), nimm immer den nächsten Unvisitierten.
    Liefert eine geschlossene Tour-Permutation, beginnend mit 0."""
    n = matrix.shape[0]
    perm = [0]
    visited = {0}
    while len(perm) < n:
        last = perm[-1]
        nxt = min(
            (j for j in range(n) if j not in visited),
            key=lambda j: matrix[last, j],
        )
        perm.append(nxt)
        visited.add(nxt)
    return perm


def _two_opt_perm(matrix: np.ndarray, seed_perm: list[int]) -> tuple[list[int], float]:
    """2-opt local search via python-tsp. Seeded mit NN-Lösung — schnellere
    Konvergenz und garantiert ≤ NN-Distanz."""
    perm, dist = solve_tsp_local_search(
        matrix,
        x0=seed_perm,
        perturbation_scheme="ps3",  # 2-opt swap
    )
    # Tour starting at depot (node 0)
    if perm[0] != 0:
        idx = perm.index(0)
        perm = perm[idx:] + perm[:idx]
    return perm, float(dist)


def _exact_perm(matrix: np.ndarray) -> tuple[list[int], float]:
    """Held-Karp exact DP via python-tsp. Nur für n ≤ 15 (Aufrufer prüft).
    Liefert garantiertes Optimum als Referenz für die 2-opt-Heuristik."""
    perm, dist = solve_tsp_dynamic_programming(matrix)
    if perm[0] != 0:
        idx = perm.index(0)
        perm = perm[idx:] + perm[:idx]
    return perm, float(dist)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/plan")
async def plan_route(db: Session = Depends(get_db)):
    """Plant eine Route: Füllstand-Threshold + 2-opt TSP-Heuristik.

    Ablauf:
      1. Tonnen mit fill_level >= FILL_THRESHOLD und nicht gesperrt
      2. Distanzmatrix (planar)
      3. NN als Baseline → Distanz für Badge merken
      4. 2-opt seeded mit NN → finale Reihenfolge
      5. OSRM ruft echte Straßen-Geometrie auf der 2-opt-Order ab
    """
    bins = (
        db.query(Bin)
        .filter(Bin.locked == False, Bin.fill_level >= FILL_THRESHOLD)
        .all()
    )

    depot = (settings.depot_lat, settings.depot_lng)

    if not bins:
        route = Route(waypoints=[], distance_m=0, duration_s=0, geometry=None)
        db.add(route)
        db.commit()
        db.refresh(route)
        return route

    # Knoten 0 = Depot, Knoten 1..n = Tonnen (in DB-Reihenfolge)
    coords = [depot] + [_pickup_coords(b) for b in bins]
    matrix = _build_distance_matrix(coords)

    # 1) NN als Baseline
    nn_perm = _nearest_neighbor_perm(matrix)
    nn_len = _tour_length(coords, nn_perm)

    # 2) 2-opt, seeded mit NN
    if len(bins) >= 3:
        opt_perm, opt_len = _two_opt_perm(matrix, nn_perm)
    else:
        # 1–2 Tonnen: NN ist schon optimal
        opt_perm, opt_len = nn_perm, nn_len

    nn_m = _planar_to_meters(nn_len)
    opt_m = _planar_to_meters(opt_len)
    saved_pct = round((1 - opt_len / nn_len) * 100, 1) if nn_len > 0 else 0.0

    # 3) Held-Karp exakte Lösung als Referenz (nur für kleine Instanzen)
    exact_m: int | None = None
    if len(coords) <= EXACT_TSP_MAX_NODES + 1:  # +1 für Depot-Knoten
        try:
            _, exact_len = _exact_perm(matrix)
            exact_m = _planar_to_meters(exact_len)
            gap_pct = round((opt_len / exact_len - 1) * 100, 2) if exact_len > 0 else 0.0
            logger.info(
                "TSP comparison (n=%d): NN=%dm, 2-opt=%dm, exact=%dm, "
                "saved=%.1f%%, 2-opt-gap=%.2f%%",
                len(bins), nn_m, opt_m, exact_m, saved_pct, gap_pct,
            )
        except Exception as e:
            logger.warning("Held-Karp DP failed: %s", e)
    else:
        logger.info(
            "TSP comparison (n=%d, DP skipped): NN=%dm, 2-opt=%dm, saved=%.1f%%",
            len(bins), nn_m, opt_m, saved_pct,
        )

    # Reorder bins by NN permutation (Knoten 0 = Depot überspringen). Das wirkt
    # im Leitstand deutlich plausibler als 2-opt-Sprünge über nahe Cluster.
    ordered_bins = [bins[i - 1] for i in nn_perm[1:]]

    # OSRM für echte Straßen-Geometrie (depot → bins → depot)
    osrm_coords = [depot] + [_pickup_coords(b) for b in ordered_bins] + [depot]
    result = await get_route_geometry(osrm_coords)

    route = Route(
        waypoints=[b.id for b in ordered_bins],
        distance_m=result["distance_m"],          # OSRM, real streets
        duration_s=result["duration_s"],
        geometry=result["geometry"],
        nn_distance_m=nn_m,                        # planar baseline
        optimized_distance_m=nn_m,                 # active street-sweep route
        exact_distance_m=exact_m,                  # planar Held-Karp (nullable)
        llm_reasoning=None,
    )
    db.add(route)
    db.commit()
    db.refresh(route)
    return route


@router.get("/latest")
def get_latest_route(db: Session = Depends(get_db)):
    return (
        db.query(Route)
        .filter(Route.completed == False)
        .order_by(Route.created_at.desc())
        .first()
    )


@router.post("/{route_id}/complete")
def complete_route(route_id: int, db: Session = Depends(get_db)):
    route = db.query(Route).filter(Route.id == route_id).first()
    if route:
        route.completed = True
        db.commit()
    return route
