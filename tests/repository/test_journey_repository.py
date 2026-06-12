import pytest
from datetime import datetime, timezone
from src.db.models import CompanionJourney, PassengerJourney, FoundJourney
from src.repository.journey_repository import (
    get_unmatched_companions,
    get_unmatched_passengers,
    get_companion_by_id,
    get_passenger_by_id,
    save_matches,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_companion(db_session, payload: dict) -> CompanionJourney:
    companion = CompanionJourney(**payload)
    db_session.add(companion)
    db_session.commit()
    db_session.refresh(companion)
    return companion


def make_passenger(db_session, payload: dict) -> PassengerJourney:
    passenger = PassengerJourney(**payload)
    db_session.add(passenger)
    db_session.commit()
    db_session.refresh(passenger)
    return passenger


def make_found_journey(db_session, companion_id: int, passenger_id: int) -> FoundJourney:
    fj = FoundJourney(
        companionJourneyId=companion_id,
        passengerJourneyId=passenger_id,
        companionStatus="waiting",
        passengerStatus="waiting",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(fj)
    db_session.commit()
    db_session.refresh(fj)
    return fj


# ---------------------------------------------------------------------------
# get_unmatched_companions
# ---------------------------------------------------------------------------

class TestGetUnmatchedCompanions:

    def test_returns_companion_with_no_match(self, db_session, sample_companion_payload):
        companion = make_companion(db_session, sample_companion_payload)
        result = get_unmatched_companions(db_session)
        assert len(result) == 1
        assert result[0].id == companion.id

    def test_excludes_already_matched_companion(self, db_session, sample_companion_payload, sample_passenger_payload):
        companion = make_companion(db_session, sample_companion_payload)
        passenger = make_passenger(db_session, sample_passenger_payload)
        make_found_journey(db_session, companion.id, passenger.id)

        result = get_unmatched_companions(db_session)
        assert result == []

    def test_returns_empty_when_no_companions(self, db_session):
        result = get_unmatched_companions(db_session)
        assert result == []

    def test_returns_only_unmatched_companions(self, db_session, sample_companion_payload, sample_passenger_payload):
        matched = make_companion(db_session, {**sample_companion_payload, "userId": 10})
        unmatched = make_companion(db_session, {**sample_companion_payload, "userId": 11})
        passenger = make_passenger(db_session, sample_passenger_payload)
        make_found_journey(db_session, matched.id, passenger.id)

        result = get_unmatched_companions(db_session)
        ids = [c.id for c in result]
        assert unmatched.id in ids
        assert matched.id not in ids


# ---------------------------------------------------------------------------
# get_unmatched_passengers
# ---------------------------------------------------------------------------

class TestGetUnmatchedPassengers:

    def test_returns_passenger_with_no_match(self, db_session, sample_passenger_payload):
        passenger = make_passenger(db_session, sample_passenger_payload)
        result = get_unmatched_passengers(db_session)
        assert len(result) == 1
        assert result[0].id == passenger.id

    def test_excludes_already_matched_passenger(self, db_session, sample_companion_payload, sample_passenger_payload):
        companion = make_companion(db_session, sample_companion_payload)
        passenger = make_passenger(db_session, sample_passenger_payload)
        make_found_journey(db_session, companion.id, passenger.id)

        result = get_unmatched_passengers(db_session)
        assert result == []

    def test_returns_empty_when_no_passengers(self, db_session):
        result = get_unmatched_passengers(db_session)
        assert result == []

    def test_returns_only_unmatched_passengers(self, db_session, sample_companion_payload, sample_passenger_payload):
        companion = make_companion(db_session, sample_companion_payload)
        matched = make_passenger(db_session, {**sample_passenger_payload, "userId": 20})
        unmatched = make_passenger(db_session, {**sample_passenger_payload, "userId": 21})
        make_found_journey(db_session, companion.id, matched.id)

        result = get_unmatched_passengers(db_session)
        ids = [p.id for p in result]
        assert unmatched.id in ids
        assert matched.id not in ids


# ---------------------------------------------------------------------------
# get_companion_by_id
# ---------------------------------------------------------------------------

class TestGetCompanionById:

    def test_returns_companion_when_found(self, db_session, sample_companion_payload):
        companion = make_companion(db_session, sample_companion_payload)
        result = get_companion_by_id(db_session, companion.id)
        assert result is not None
        assert result.id == companion.id

    def test_returns_none_when_not_found(self, db_session):
        result = get_companion_by_id(db_session, 9999)
        assert result is None


# ---------------------------------------------------------------------------
# get_passenger_by_id
# ---------------------------------------------------------------------------

class TestGetPassengerById:

    def test_returns_passenger_when_found(self, db_session, sample_passenger_payload):
        passenger = make_passenger(db_session, sample_passenger_payload)
        result = get_passenger_by_id(db_session, passenger.id)
        assert result is not None
        assert result.id == passenger.id

    def test_returns_none_when_not_found(self, db_session):
        result = get_passenger_by_id(db_session, 9999)
        assert result is None


# ---------------------------------------------------------------------------
# save_matches
# ---------------------------------------------------------------------------

class TestSaveMatches:

    def test_saves_single_match(self, db_session, sample_companion_payload, sample_passenger_payload):
        companion = make_companion(db_session, sample_companion_payload)
        passenger = make_passenger(db_session, sample_passenger_payload)

        batch = [{"companion_journey_id": companion.id, "passenger_journey_id": passenger.id}]
        created_ids = save_matches(batch, db_session)
        db_session.commit()

        assert len(created_ids) == 1
        row = db_session.query(FoundJourney).filter(FoundJourney.id == created_ids[0]).first()
        assert row is not None
        assert row.companionJourneyId == companion.id
        assert row.passengerJourneyId == passenger.id
        assert row.companionStatus == "waiting"
        assert row.passengerStatus == "waiting"

    def test_returns_empty_list_for_empty_batch(self, db_session):
        created_ids = save_matches([], db_session)
        assert created_ids == []

    def test_skips_duplicate_silently(self, db_session, sample_companion_payload, sample_passenger_payload):
        companion = make_companion(db_session, sample_companion_payload)
        passenger = make_passenger(db_session, sample_passenger_payload)
        make_found_journey(db_session, companion.id, passenger.id)

        batch = [{"companion_journey_id": companion.id, "passenger_journey_id": passenger.id}]
        created_ids = save_matches(batch, db_session)
        db_session.commit()

        # Duplicate skipped → 0 new IDs returned
        assert created_ids == []
        # Only 1 row in DB (no duplicate)
        count = db_session.query(FoundJourney).filter(
            FoundJourney.companionJourneyId == companion.id,
            FoundJourney.passengerJourneyId == passenger.id,
        ).count()
        assert count == 1

    def test_mixed_batch_new_duplicate_new(self, db_session, sample_companion_payload, sample_passenger_payload):
        """
        Batch [new_A, duplicate_B, new_C] must return exactly 2 IDs (A and C)
        and leave pair B with exactly 1 row in the DB.
        """
        c_a = make_companion(db_session, {**sample_companion_payload, "userId": 101})
        p_a = make_passenger(db_session, {**sample_passenger_payload, "userId": 201})
        c_b = make_companion(db_session, {**sample_companion_payload, "userId": 102})
        p_b = make_passenger(db_session, {**sample_passenger_payload, "userId": 202})
        c_c = make_companion(db_session, {**sample_companion_payload, "userId": 103})
        p_c = make_passenger(db_session, {**sample_passenger_payload, "userId": 203})

        # Pre-insert pair B so it becomes a duplicate
        make_found_journey(db_session, c_b.id, p_b.id)

        batch = [
            {"companion_journey_id": c_a.id, "passenger_journey_id": p_a.id},
            {"companion_journey_id": c_b.id, "passenger_journey_id": p_b.id},  # duplicate
            {"companion_journey_id": c_c.id, "passenger_journey_id": p_c.id},
        ]
        created_ids = save_matches(batch, db_session)
        db_session.commit()

        assert len(created_ids) == 2

        count_b = db_session.query(FoundJourney).filter(
            FoundJourney.companionJourneyId == c_b.id,
            FoundJourney.passengerJourneyId == p_b.id,
        ).count()
        assert count_b == 1
