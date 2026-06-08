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
import math
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from src.algorithm.matcher import (
    find_matches,
    haversine_distance,
    _geo_score,
    _time_score,
    _address_score,
    compute_match_score,
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
