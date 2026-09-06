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
from datetime import datetime, timezone
from math import cos, radians, sqrt

import numpy as np
from fastapi import APIRouter, Depends
from python_tsp.heuristics import solve_tsp_local_search
from python_tsp.exact import solve_tsp_dynamic_programming
from sqlalchemy.orm import Session

import truck_state
from config import settings
from database import get_db
from models.bin import Bin
from models.route import Route
from services.routing import get_route_geometry

logger = logging.getLogger(__name__)
router = APIRouter()

# Nur Tonnen ab diesem Füllstand werden angefahren — gemeinsame Wahrheit mit dem
# Simulator (config), damit Planung und Fahrt dieselbe Schwelle nutzen.
FILL_THRESHOLD = settings.collect_fill_threshold

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


def _bin_units(b: Bin) -> int:
    """Beladung einer Tonne in Einheiten — 1 % Füllung ≈ 1 Einheit, konsistent
    zur Entleerungslogik im Simulator (eingesammelter fill_level → load_units)."""
    return max(0, min(100, int(b.fill_level or 0)))


def _capacity_cutoff(ordered_bins: list[Bin], capacity_units: float) -> tuple[list[Bin], int]:
    """Schneidet die Fahrreihenfolge an der Wagenkapazität ab.

    Geht die Tonnen in Fahrreihenfolge durch und nimmt sie auf, solange die
    kumulierte Beladung die Kapazität nicht überschreitet. Sobald die nächste
    Tonne nicht mehr passt, endet die Fahrt (Rest bleibt für die nächste Planung).
    Mindestens eine Tonne wird aufgenommen, damit nie eine leere Fahrt entsteht.

    Returns (tonnen_in_dieser_fahrt, geladene_einheiten).
    """
    kept: list[Bin] = []
    load = 0
    for b in ordered_bins:
        units = _bin_units(b)
        if kept and load + units > capacity_units:
            break
        kept.append(b)
        load += units
    return kept, load


async def _build_candidate(
    depot: tuple[float, float],
    ordered_bins: list[Bin],
    capacity: float,
    variant_label: str,
    plan_group: str,
    nn_m: int,
    exact_m: int | None,
) -> Route:
    """Baut aus einer Fahrreihenfolge einen Routen-Kandidaten: Kapazität
    abschneiden, OSRM-Geometrie holen, Kennzahlen setzen. Noch nicht aktiv."""
    kept, load_units = _capacity_cutoff(ordered_bins, capacity)
    osrm_coords = [depot] + [_pickup_coords(b) for b in kept] + [depot]
    result = await get_route_geometry(osrm_coords)
    return Route(
        waypoints=[b.id for b in kept],
        distance_m=result["distance_m"],
        duration_s=result["duration_s"],
        geometry=result["geometry"],
        nn_distance_m=nn_m,
        optimized_distance_m=nn_m,
        exact_distance_m=exact_m,
        load_units=load_units,
        capacity_units=int(capacity),
        variant_label=variant_label,
        plan_group=plan_group,
        active=False,
        is_default=False,
        llm_reasoning=None,
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
    """Plant mehrere kapazitätsbegrenzte Kandidaten (Default = active + is_default).
    Startet den Truck NICHT — das macht erst /routes/start (Disponent-Flow)."""
    return await generate_route_candidates(db)


@router.post("/start")
def start_route():
    """Truck entsenden: spawnt am Depot und faehrt die aktive/gewaehlte Route."""
    truck_state.set_dispatched(True)
    return {"dispatched": True}


@router.post("/stop")
def stop_route():
    """Truck stoppen: dispatched aus + despawnen (verschwindet von der Karte)."""
    truck_state.set_dispatched(False)
    truck_state.despawn()
    return {"dispatched": False}


async def generate_route_candidates(db: Session) -> list[Route]:
    """Erzeugt Routen-Kandidaten (Sweep / Optimiert / Volle zuerst), schneidet
    sie an der Wagenkapazität ab, deaktiviert die bisher aktive Route und macht
    den Default aktiv. Genutzt vom /plan-Endpunkt UND vom Auto-Replan des
    Simulators (nächster Trip, nachdem der Wagen am Depot entleert hat).
    """
    bins = (
        db.query(Bin)
        .filter(Bin.locked == False, Bin.fill_level >= FILL_THRESHOLD)
        .all()
    )

    depot = (settings.depot_lat, settings.depot_lng)

    if not bins:
        db.query(Route).filter(Route.active == True).update({Route.active: False})
        route = Route(
            waypoints=[], distance_m=0, duration_s=0, geometry=None,
            active=True, is_default=True,
            plan_group=datetime.now(timezone.utc).isoformat(),
        )
        db.add(route)
        db.commit()
        db.refresh(route)
        return [route]

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

    # Drei Kandidaten nach betrieblichem *Ziel* (nicht nach Algorithmus-Name),
    # damit die Auswahl für den Bediener eine echte, verständliche Entscheidung ist:
    #   Kürzeste Strecke   → 2-opt-Reihenfolge, geografisch kürzeste Tour
    #                        (wenig Sprit/Zeit) → System-Default.
    #   Dringendste zuerst → vollste Tonnen zuerst (Überlauf-Risiko minimieren).
    #   Meiste Tonnen      → kleinste Füllstände zuerst, dadurch passen mehr Tonnen
    #                        in die Kapazität (max. Durchsatz, dafür längere Tour).
    capacity = settings.truck_capacity_units
    orderings: list[tuple[str, list[Bin]]] = [
        ("Kürzeste Strecke", [bins[i - 1] for i in opt_perm[1:]]),
        ("Dringendste zuerst", sorted(bins, key=_bin_units, reverse=True)),
        ("Meiste Tonnen", sorted(bins, key=_bin_units)),
    ]

    plan_group = datetime.now(timezone.utc).isoformat()

    # Bestehende aktive Route deaktivieren — der Simulator bricht ihre Fahrt ab
    # und übernimmt die neu gewählte/Default-Route.
    db.query(Route).filter(Route.active == True).update({Route.active: False})
    db.commit()

    candidates: list[Route] = []
    seen: set[tuple[int, ...]] = set()
    for label, ordered in orderings:
        cand = await _build_candidate(depot, ordered, capacity, label, plan_group, nn_m, exact_m)
        key = tuple(cand.waypoints)
        if not cand.waypoints or key in seen:
            continue
        seen.add(key)
        candidates.append(cand)

    # Default = "Kürzeste Strecke" (System-Empfehlung), wird sofort aktiv → der
    # Truck fährt autonom los; der Bediener kann optional ein anderes Ziel wählen.
    default = next(
        (c for c in candidates if c.variant_label == "Kürzeste Strecke"),
        min(candidates, key=lambda c: c.distance_m),
    )
    default.is_default = True
    default.active = True
    for c in candidates:
        db.add(c)
    db.commit()
    for c in candidates:
        db.refresh(c)

    logger.info(
        "Plan: %d Kandidaten (Default=%s, %d/%d Tonnen, %d/%d units)",
        len(candidates), default.variant_label, len(default.waypoints), len(bins),
        default.load_units, int(capacity),
    )
    candidates.sort(key=lambda c: (not c.is_default, c.distance_m))
    return candidates


@router.get("/latest")
def get_latest_route(db: Session = Depends(get_db)):
    """Die aktuell aktive (gefahrene) Route."""
    return (
        db.query(Route)
        .filter(Route.active == True, Route.completed == False)
        .order_by(Route.created_at.desc())
        .first()
    )


@router.get("/candidates")
def get_candidates(db: Session = Depends(get_db)):
    """Die Vorschläge der letzten Planung (zur Auswahl im Leitstand)."""
    latest = (
        db.query(Route)
        .filter(Route.plan_group.isnot(None))
        .order_by(Route.created_at.desc())
        .first()
    )
    if not latest or not latest.plan_group:
        return []
    cands = db.query(Route).filter(Route.plan_group == latest.plan_group).all()
    cands.sort(key=lambda c: (not c.is_default, c.distance_m))
    return cands


@router.post("/{route_id}/activate")
def activate_route(route_id: int, db: Session = Depends(get_db)):
    """Bediener wählt einen Kandidaten → wird die aktive (gefahrene) Route."""
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        return None
    db.query(Route).filter(Route.active == True).update({Route.active: False})
    route.active = True
    route.completed = False
    db.commit()
    db.refresh(route)
    return route


@router.post("/{route_id}/complete")
def complete_route(route_id: int, db: Session = Depends(get_db)):
    route = db.query(Route).filter(Route.id == route_id).first()
    if route:
        route.completed = True
        db.commit()
    return route
