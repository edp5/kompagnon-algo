"""
Multi-criteria matching engine for Kompagnon.

Scores every (companion, passenger) pair across three dimensions:
  1. Geographic proximity  (Haversine distance)
  2. Temporal compatibility (departure-time difference)
  3. Textual address match  (case-insensitive fallback)

Configuration is read from environment variables via ``config.py``.
"""
import math
import logging
from datetime import datetime
from typing import List, Dict, Any, Union

from src.algorithm.config import (
    MAX_DISTANCE_KM,
    PERFECT_DISTANCE_KM,
    TIME_TOLERANCE_MINUTES,
    MIN_MATCH_SCORE,
    WEIGHT_GEO,
    WEIGHT_TIME,
    WEIGHT_ADDRESS,
)

logger = logging.getLogger(__name__)

# Earth's mean radius in kilometres (WGS-84).
_EARTH_RADIUS_KM = 6_371.0

# Approximate km per degree of latitude (constant everywhere on Earth).
_KM_PER_DEG_LAT = 111.0


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def haversine_distance(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
) -> float:
    """
    Return the great-circle distance in **km** between two points
    given as (latitude, longitude) in **degrees**.
    """
    lat1, lon1, lat2, lon2 = (math.radians(v) for v in (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _bounding_box_filter(
    target: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    max_km: float,
) -> List[Dict[str, Any]]:
    """
    Return only the candidates whose **departure** point falls inside a square
    bounding box of side ``2 × max_km`` centred on the target departure point.

    This is a cheap O(n) pre-filter that uses simple degree arithmetic instead
    of Haversine, eliminating obviously distant candidates before the expensive
    scoring loop. A bounding box is always a superset of the Haversine circle,
    so no valid match is ever discarded here.

    Formula::

        Δlat = max_km / 111.0
        Δlon = max_km / (111.0 × cos(lat_rad))
    """
    t_lat = float(target["departureLat"])
    t_lon = float(target["departureLon"])

    delta_lat = max_km / _KM_PER_DEG_LAT
    # Guard against equatorial cos(lat) = 0; clamp to small positive value.
    cos_lat = math.cos(math.radians(t_lat)) or 1e-9
    delta_lon = max_km / (_KM_PER_DEG_LAT * cos_lat)

    lat_min, lat_max = t_lat - delta_lat, t_lat + delta_lat
    lon_min, lon_max = t_lon - delta_lon, t_lon + delta_lon

    return [
        c for c in candidates
        if lat_min <= float(c["departureLat"]) <= lat_max
        and lon_min <= float(c["departureLon"]) <= lon_max
    ]


# ---------------------------------------------------------------------------
# Per-dimension scorers  (each returns a float in [0.0, 1.0])
# ---------------------------------------------------------------------------

def _geo_score(
    companion: Dict[str, Any],
    passenger: Dict[str, Any],
) -> float:
    """
    Geographic proximity score (average of departure + arrival distances).

    Returns 1.0 when both distances ≤ PERFECT_DISTANCE_KM,
    linearly decreasing to 0.0 at MAX_DISTANCE_KM.
    Returns 0.0 immediately if *either* distance > MAX_DISTANCE_KM.
    """
    dep_dist = haversine_distance(
        float(companion["departureLat"]), float(companion["departureLon"]),
        float(passenger["departureLat"]), float(passenger["departureLon"]),
    )
    arr_dist = haversine_distance(
        float(companion["arrivalLat"]), float(companion["arrivalLon"]),
        float(passenger["arrivalLat"]), float(passenger["arrivalLon"]),
    )

    # Hard cut-off — if either point is too far, no match.
    if dep_dist > MAX_DISTANCE_KM or arr_dist > MAX_DISTANCE_KM:
        return 0.0

    def _distance_to_score(dist: float) -> float:
        if dist <= PERFECT_DISTANCE_KM:
            return 1.0
        # Linear decay from 1.0 → 0.0 between PERFECT and MAX distance.
        return max(0.0, 1.0 - (dist - PERFECT_DISTANCE_KM) / (MAX_DISTANCE_KM - PERFECT_DISTANCE_KM))

    return (_distance_to_score(dep_dist) + _distance_to_score(arr_dist)) / 2.0


def _time_score(
    companion: Dict[str, Any],
    passenger: Dict[str, Any],
) -> float:
    """
    Temporal compatibility score based on departure-time difference.

    Returns 1.0 for identical departure times, linearly decreasing to 0.0
    at TIME_TOLERANCE_MINUTES.  Returns 0.0 if difference > tolerance.
    """
    c_dep: Union[datetime, None] = companion.get("departureTime")
    p_dep: Union[datetime, None] = passenger.get("departureTime")

    if c_dep is None or p_dep is None:
        # If either side has no departure time, we can't score → neutral 0.
        return 0.0

    diff_minutes = abs((c_dep - p_dep).total_seconds()) / 60.0

    if diff_minutes > TIME_TOLERANCE_MINUTES:
        return 0.0
    if TIME_TOLERANCE_MINUTES == 0:
        return 1.0
    return 1.0 - diff_minutes / TIME_TOLERANCE_MINUTES


def _address_score(
    companion: Dict[str, Any],
    passenger: Dict[str, Any],
) -> float:
    """
    Textual address match score (case-insensitive, stripped).

    Returns 1.0 if **both** departure and arrival addresses match,
    0.5 if only one matches, 0.0 otherwise.
    """
    dep_match = (
        (companion.get("departureAddress") or "").strip().lower()
        == (passenger.get("departureAddress") or "").strip().lower()
    )
    arr_match = (
        (companion.get("arrivalAddress") or "").strip().lower()
        == (passenger.get("arrivalAddress") or "").strip().lower()
    )

    if dep_match and arr_match:
        return 1.0
    if dep_match or arr_match:
        return 0.5
    return 0.0


# ---------------------------------------------------------------------------
# Combined scorer
# ---------------------------------------------------------------------------

def compute_match_score(
    companion: Dict[str, Any],
    passenger: Dict[str, Any],
) -> float:
    """
    Weighted combination of all sub-scores.

    ``score = WEIGHT_GEO * geo + WEIGHT_TIME * time + WEIGHT_ADDRESS * address``
    """
    geo = _geo_score(companion, passenger)
    time = _time_score(companion, passenger)
    address = _address_score(companion, passenger)

    score = WEIGHT_GEO * geo + WEIGHT_TIME * time + WEIGHT_ADDRESS * address

    logger.debug(
        f"Score C{companion['id']}↔P{passenger['id']}: "
        f"geo={geo:.2f} time={time:.2f} addr={address:.2f} → total={score:.2f}"
    )
    return score


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_matches(
    companions: List[Dict[str, Any]],
    passengers: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Find matches between passengers and companions using multi-criteria scoring.

    Each journey dict is expected to contain at least:
        id, departureAddress, arrivalAddress,
        departureLat, departureLon, arrivalLat, arrivalLon,
        departureTime

    A bounding box pre-filter (cheap O(n) degree arithmetic) is applied for
    each passenger before the Haversine scoring loop, discarding companions
    that are obviously too far without computing any trigonometry.

    Returns a list of dicts with keys:
        ``companion_journey_id``, ``passenger_journey_id``, ``score``
    sorted by descending score (best matches first).
    """
    matches: List[Dict[str, Any]] = []
    logger.info(
        f"Starting matching process for {len(passengers)} passenger(s) "
        f"and {len(companions)} companion(s).  "
        f"[max_dist={MAX_DISTANCE_KM}km, tolerance={TIME_TOLERANCE_MINUTES}min, "
        f"min_score={MIN_MATCH_SCORE}]"
    )

    for passenger in passengers:
        # Pre-filter: keep only companions within the bounding box around
        # this passenger's departure point — no Haversine needed here.
        nearby_companions = _bounding_box_filter(passenger, companions, MAX_DISTANCE_KM)
        logger.debug(
            f"Passenger {passenger['id']}: bounding-box pre-filter kept "
            f"{len(nearby_companions)}/{len(companions)} companion(s)."
        )

        for companion in nearby_companions:
            score = compute_match_score(companion, passenger)
            if score >= MIN_MATCH_SCORE:
                logger.info(
                    f"Match found (score={score:.2f}): "
                    f"Passenger Journey {passenger['id']} ↔ Companion Journey {companion['id']}"
                )
                matches.append({
                    "passenger_journey_id": passenger["id"],
                    "companion_journey_id": companion["id"],
                    "score": round(score, 4),
                })

    # Best matches first.
    matches.sort(key=lambda m: m["score"], reverse=True)

    logger.info(f"Matching process completed. Found {len(matches)} match(es).")
    return matches
