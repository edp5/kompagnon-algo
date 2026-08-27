"""
Unit tests for the multi-criteria matching algorithm.

Tests cover:
  - Haversine distance calculation
  - Geographic scoring
  - Temporal scoring
  - Address scoring
  - Combined scoring & find_matches behavior
  - Sorting by score
"""
import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from unittest.mock import patch

@pytest.fixture(autouse=True)
def pin_matcher_constants(monkeypatch):
    monkeypatch.setattr("src.algorithm.matcher.MAX_DISTANCE_KM", 5.0)
    monkeypatch.setattr("src.algorithm.matcher.PERFECT_DISTANCE_KM", 0.5)
    monkeypatch.setattr("src.algorithm.matcher.TIME_TOLERANCE_MINUTES", 30)
    monkeypatch.setattr("src.algorithm.matcher.WEIGHT_GEO", 0.40)
    monkeypatch.setattr("src.algorithm.matcher.WEIGHT_TIME", 0.40)
    monkeypatch.setattr("src.algorithm.matcher.WEIGHT_ADDRESS", 0.20)
    monkeypatch.setattr("src.algorithm.matcher.MIN_MATCH_SCORE", 0.5)

from src.algorithm.matcher import (
    find_matches,
    haversine_distance,
    _geo_score,
    _time_score,
    _address_score,
    compute_match_score,
    _bounding_box_filter,
)


# ---------------------------------------------------------------------------
# Helpers — build journey dicts with sensible defaults
# ---------------------------------------------------------------------------

_BASE_TIME = datetime(2024, 5, 1, 10, 0, tzinfo=timezone.utc)

def _companion(
    id=1,
    dep_addr="Paris", arr_addr="Lyon",
    dep_lat=48.8566, dep_lon=2.3522,
    arr_lat=45.7640, arr_lon=4.8357,
    dep_time=_BASE_TIME,
):
    return {
        "id": id,
        "departureAddress": dep_addr,
        "arrivalAddress": arr_addr,
        "departureLat": dep_lat,
        "departureLon": dep_lon,
        "arrivalLat": arr_lat,
        "arrivalLon": arr_lon,
        "departureTime": dep_time,
    }

def _passenger(
    id=10,
    dep_addr="Paris", arr_addr="Lyon",
    dep_lat=48.8566, dep_lon=2.3522,
    arr_lat=45.7640, arr_lon=4.8357,
    dep_time=_BASE_TIME,
):
    return {
        "id": id,
        "departureAddress": dep_addr,
        "arrivalAddress": arr_addr,
        "departureLat": dep_lat,
        "departureLon": dep_lon,
        "arrivalLat": arr_lat,
        "arrivalLon": arr_lon,
        "departureTime": dep_time,
    }


# ---------------------------------------------------------------------------
# Haversine distance
# ---------------------------------------------------------------------------

class TestHaversineDistance:

    def test_same_point_is_zero(self):
        assert haversine_distance(48.8566, 2.3522, 48.8566, 2.3522) == 0.0

    def test_paris_to_lyon(self):
        dist = haversine_distance(48.8566, 2.3522, 45.7640, 4.8357)
        # Real distance ≈ 392 km
        assert 380 < dist < 410

    def test_short_distance(self):
        # Two points ~111 m apart (0.001° latitude ≈ 111 m)
        dist = haversine_distance(48.8566, 2.3522, 48.8576, 2.3522)
        assert dist < 0.2  # < 200 m

    def test_symmetry(self):
        d1 = haversine_distance(48.8566, 2.3522, 45.7640, 4.8357)
        d2 = haversine_distance(45.7640, 4.8357, 48.8566, 2.3522)
        assert abs(d1 - d2) < 1e-9


# ---------------------------------------------------------------------------
# Geo score
# ---------------------------------------------------------------------------

class TestGeoScore:

    def test_identical_coords_gives_1(self):
        c = _companion()
        p = _passenger()
        assert _geo_score(c, p) == 1.0

    def test_too_far_gives_0(self):
        """Paris → Lyon departure coords are ~392 km apart → score must be 0."""
        c = _companion(dep_lat=48.8566, dep_lon=2.3522)
        p = _passenger(dep_lat=43.2965, dep_lon=5.3698)  # Marseille
        assert _geo_score(c, p) == 0.0

    def test_intermediate_distance(self):
        """Slightly offset coords (within max distance) → 0 < score < 1."""
        # ~2.5 km offset in latitude
        c = _companion(dep_lat=48.8566, dep_lon=2.3522, arr_lat=45.764, arr_lon=4.8357)
        p = _passenger(dep_lat=48.879, dep_lon=2.3522, arr_lat=45.764, arr_lon=4.8357)
        score = _geo_score(c, p)
        assert 0.0 < score < 1.0


# ---------------------------------------------------------------------------
# Time score
# ---------------------------------------------------------------------------

class TestTimeScore:

    def test_identical_time_gives_1(self):
        c = _companion(dep_time=_BASE_TIME)
        p = _passenger(dep_time=_BASE_TIME)
        assert _time_score(c, p) == 1.0

    def test_15_min_diff(self):
        c = _companion(dep_time=_BASE_TIME)
        p = _passenger(dep_time=_BASE_TIME + timedelta(minutes=15))
        score = _time_score(c, p)
        assert score == pytest.approx(0.5, abs=0.01)

    def test_exactly_at_tolerance_gives_0(self):
        c = _companion(dep_time=_BASE_TIME)
        p = _passenger(dep_time=_BASE_TIME + timedelta(minutes=30))
        assert _time_score(c, p) == 0.0

    def test_beyond_tolerance_gives_0(self):
        c = _companion(dep_time=_BASE_TIME)
        p = _passenger(dep_time=_BASE_TIME + timedelta(hours=2))
        assert _time_score(c, p) == 0.0

    def test_missing_time_gives_0(self):
        c = _companion(dep_time=None)
        p = _passenger(dep_time=_BASE_TIME)
        assert _time_score(c, p) == 0.0

    def test_tolerance_zero(self):
        c = _companion(dep_time=_BASE_TIME)
        p = _passenger(dep_time=_BASE_TIME)
        with patch("src.algorithm.matcher.TIME_TOLERANCE_MINUTES", 0):
            assert _time_score(c, p) == 1.0


# ---------------------------------------------------------------------------
# Address score
# ---------------------------------------------------------------------------

class TestAddressScore:

    def test_exact_match_gives_1(self):
        c = _companion(dep_addr="Paris", arr_addr="Lyon")
        p = _passenger(dep_addr="Paris", arr_addr="Lyon")
        assert _address_score(c, p) == 1.0

    def test_case_insensitive_match(self):
        c = _companion(dep_addr="PARIS", arr_addr="lyon")
        p = _passenger(dep_addr="paris", arr_addr="LYON")
        assert _address_score(c, p) == 1.0

    def test_whitespace_trimmed(self):
        c = _companion(dep_addr="  Paris ", arr_addr="Lyon  ")
        p = _passenger(dep_addr="Paris", arr_addr="Lyon")
        assert _address_score(c, p) == 1.0

    def test_one_match_gives_half(self):
        c = _companion(dep_addr="Paris", arr_addr="Lyon")
        p = _passenger(dep_addr="Paris", arr_addr="Marseille")
        assert _address_score(c, p) == 0.5

    def test_no_match_gives_0(self):
        c = _companion(dep_addr="Paris", arr_addr="Lyon")
        p = _passenger(dep_addr="Lille", arr_addr="Marseille")
        assert _address_score(c, p) == 0.0


# ---------------------------------------------------------------------------
# Combined scoring
# ---------------------------------------------------------------------------

class TestComputeMatchScore:

    def test_perfect_match(self):
        """Identical journey data → score = 1.0."""
        c = _companion()
        p = _passenger()
        assert compute_match_score(c, p) == pytest.approx(1.0, abs=0.01)

    def test_zero_score_when_too_far(self):
        """Far away coords + different addresses → very low score."""
        c = _companion(dep_addr="Paris", arr_addr="Lyon",
                       dep_lat=48.8566, dep_lon=2.3522,
                       arr_lat=45.764, arr_lon=4.8357)
        p = _passenger(dep_addr="Marseille", arr_addr="Nice",
                       dep_lat=43.2965, dep_lon=5.3698,
                       arr_lat=43.7102, arr_lon=7.2620)
        score = compute_match_score(c, p)
        assert score < 0.5  # below match threshold


# ---------------------------------------------------------------------------
# find_matches
# ---------------------------------------------------------------------------

class TestFindMatches:

    def test_basic_match(self):
        """Identical journeys → 1 match found."""
        matches = find_matches([_companion()], [_passenger()])
        assert len(matches) == 1
        assert matches[0]["companion_journey_id"] == 1
        assert matches[0]["passenger_journey_id"] == 10
        assert "score" in matches[0]

    def test_no_match_when_too_far(self):
        """Companion in Paris, passenger in Marseille → no match."""
        c = _companion(dep_lat=48.8566, dep_lon=2.3522,
                       arr_lat=48.8566, arr_lon=2.3522)
        p = _passenger(dep_lat=43.2965, dep_lon=5.3698,
                       arr_lat=43.7102, arr_lon=7.2620,
                       dep_addr="Marseille", arr_addr="Nice")
        matches = find_matches([c], [p])
        assert len(matches) == 0

    def test_no_match_when_time_too_different(self):
        """Same location but departure 2h apart and different addresses → no match."""
        c = _companion(dep_addr="Paris Gare de Lyon", arr_addr="Lyon Part-Dieu")
        p = _passenger(dep_addr="Paris Nord", arr_addr="Lyon Perrache",
                       dep_time=_BASE_TIME + timedelta(hours=2))
        matches = find_matches([c], [p])
        assert len(matches) == 0

    def test_sorted_by_score_descending(self):
        """Multiple matches are returned best-first."""
        c1 = _companion(id=1)
        c2 = _companion(id=2, dep_time=_BASE_TIME + timedelta(minutes=10))
        p = _passenger()

        matches = find_matches([c1, c2], [p])
        assert len(matches) == 2
        assert matches[0]["score"] >= matches[1]["score"]
        # The exact-time companion should be the best match
        assert matches[0]["companion_journey_id"] == 1

    def test_multiple_companions_one_passenger(self):
        """Two companions that both qualify → two matches returned."""
        companions = [
            _companion(id=1),
            _companion(id=2),
        ]
        matches = find_matches(companions, [_passenger()])
        assert len(matches) == 2

    def test_empty_inputs(self):
        assert find_matches([], [_passenger()]) == []
        assert find_matches([_companion()], []) == []
        assert find_matches([], []) == []

    def test_match_with_custom_threshold(self):
        """With a very high min score, borderline matches are rejected."""
        c = _companion()
        p = _passenger(dep_time=_BASE_TIME + timedelta(minutes=20))  # 20 min diff

        with patch("src.algorithm.matcher.MIN_MATCH_SCORE", 0.95):
            matches = find_matches([c], [p])
            assert len(matches) == 0  # time penalty pushes score below 0.95

        # But with default threshold it matches
        matches = find_matches([c], [p])
        assert len(matches) == 1


# ---------------------------------------------------------------------------
# Bounding box pre-filter
# ---------------------------------------------------------------------------

class TestBoundingBoxFilter:
    """Tests for the O(n) bounding-box geographic pre-filter."""

    # Target: departs and arrives in Paris (same location for simplicity)
    _PARIS = {
        "departureLat": 48.8566, "departureLon": 2.3522,
        "arrivalLat": 48.8566, "arrivalLon": 2.3522,
    }

    def _make_candidate(self, lat: float, lon: float,
                        arr_lat: float = None, arr_lon: float = None) -> Dict[str, Any]:
        """Build a candidate dict. Arrival defaults to same as departure."""
        return {
            "id": 99,
            "departureLat": lat,
            "departureLon": lon,
            "arrivalLat": arr_lat if arr_lat is not None else lat,
            "arrivalLon": arr_lon if arr_lon is not None else lon,
            "departureAddress": "",
            "arrivalAddress": "",
            "departureTime": _BASE_TIME,
        }

    def test_same_location_passes(self):
        """A candidate at the exact same point must always pass."""
        candidate = self._make_candidate(48.8566, 2.3522)
        result = _bounding_box_filter(self._PARIS.copy(), [candidate], max_km=5.0)
        assert len(result) == 1

    def test_nearby_candidate_passes(self):
        """A candidate ~1 km away must pass a 5 km bounding box."""
        # ~1 km north of Paris (0.009° lat ≈ 1 km)
        candidate = self._make_candidate(48.8656, 2.3522)
        result = _bounding_box_filter(self._PARIS.copy(), [candidate], max_km=5.0)
        assert len(result) == 1

    def test_distant_departure_eliminated(self):
        """A candidate whose departure is in Lyon (~392 km away) must be eliminated."""
        candidate = self._make_candidate(45.7640, 4.8357)  # Lyon
        result = _bounding_box_filter(self._PARIS.copy(), [candidate], max_km=5.0)
        assert len(result) == 0

    def test_distant_arrival_eliminated(self):
        """A candidate with close departure but far arrival must be eliminated."""
        # Departure is nearby Paris, arrival is in Lyon — should be filtered out.
        candidate = self._make_candidate(
            lat=48.860, lon=2.355,          # ~0.5 km from Paris → passes departure check
            arr_lat=45.7640, arr_lon=4.8357  # Lyon → fails arrival check
        )
        result = _bounding_box_filter(self._PARIS.copy(), [candidate], max_km=5.0)
        assert len(result) == 0

    def test_box_is_superset_of_haversine_circle(self):
        """
        A point inside the bounding box but on the diagonal corner must NOT be
        eliminated — the box is always a superset of the Haversine circle.
        """
        # 0.032° lat ≈ 3.5 km, 0.032° lon ≈ ~2.3 km at Paris lat → both within 5 km box
        candidate = self._make_candidate(48.8566 + 0.032, 2.3522 + 0.032)
        result = _bounding_box_filter(self._PARIS.copy(), [candidate], max_km=5.0)
        assert len(result) == 1

    def test_empty_candidates_returns_empty(self):
        """Empty input → empty output."""
        result = _bounding_box_filter(self._PARIS.copy(), [], max_km=5.0)
        assert result == []

    def test_filters_multiple_candidates(self):
        """Mix of nearby and distant candidates — only nearby ones survive."""
        nearby = self._make_candidate(48.860, 2.355)   # ~0.5 km from Paris
        far = self._make_candidate(43.2965, 5.3698)    # Marseille
        result = _bounding_box_filter(self._PARIS.copy(), [nearby, far], max_km=5.0)
        assert len(result) == 1
        assert result[0]["departureLat"] == 48.860

    def test_antimeridian_wraparound(self):
        """
        Two points near ±180° longitude that are geographically ~1 km apart
        must both survive the filter, even though their raw longitudes differ
        by ~360°.  This validates the _lon_in_range wrap-around logic.
        """
        # Target just west of the antimeridian
        target = {
            "departureLat": 0.0, "departureLon": 179.995,
            "arrivalLat": 0.0, "arrivalLon": 179.995,
        }
        # Candidate just east of the antimeridian (~1 km away, raw lon = -179.995)
        candidate = self._make_candidate(lat=0.0, lon=-179.995)
        result = _bounding_box_filter(target, [candidate], max_km=5.0)
        # Must NOT be filtered out — they are ~1 km apart despite lon sign difference
        assert len(result) == 1
