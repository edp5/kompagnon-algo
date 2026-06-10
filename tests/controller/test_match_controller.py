import pytest
from datetime import datetime
from src.db.models import CompanionJourney, PassengerJourney, FoundJourney
from src.api.schema import JourneyRole
from src.controller.match_controller import handle_match


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


# ---------------------------------------------------------------------------
# COMPANION role
# ---------------------------------------------------------------------------

class TestHandleMatchCompanion:

    def test_companion_match_found(self, db_session, sample_companion_payload, sample_passenger_payload):
        """A companion with a matching passenger → 1 FoundJourney created."""
        companion = make_companion(db_session, sample_companion_payload)
        passenger = make_passenger(db_session, sample_passenger_payload)

        response = handle_match(journey_id=companion.id, role=JourneyRole.COMPANION, db=db_session)

        assert len(response.found_journey_ids) == 1
        assert "Found and saved 1 match(es)" in response.message

        row = db_session.query(FoundJourney).filter(FoundJourney.id == response.found_journey_ids[0]).first()
        assert row is not None
        assert row.companionJourneyId == companion.id
        assert row.passengerJourneyId == passenger.id
        assert row.status == "WAITING"

    def test_companion_no_candidates(self, db_session, sample_companion_payload):
        """A companion with no passengers → 0 matches."""
        companion = make_companion(db_session, sample_companion_payload)

        response = handle_match(journey_id=companion.id, role=JourneyRole.COMPANION, db=db_session)

        assert response.found_journey_ids == []
        assert "Found and saved 0 match(es)" in response.message

    def test_no_match_when_criteria_differ(self, db_session, sample_companion_payload, sample_passenger_payload):
        """A companion and a passenger with different addresses, coords AND times → 0 matches."""
        companion = make_companion(db_session, sample_companion_payload)
        different_payload = {
            **sample_passenger_payload,
            "departureAddress": "Bordeaux",
            "arrivalAddress": "Nantes",
            "departureLat": 44.8378,
            "departureLon": -0.5792,
            "arrivalLat": 47.2184,
            "arrivalLon": -1.5536,
            "departureTime": datetime(2024, 6, 15, 8, 0),
            "arrivalTime": datetime(2024, 6, 15, 12, 0),
        }
        make_passenger(db_session, different_payload)

        response = handle_match(journey_id=companion.id, role=JourneyRole.COMPANION, db=db_session)

        assert response.found_journey_ids == []

    def test_companion_not_found_raises_value_error(self, db_session):
        """A non-existent companion ID → ValueError raised."""
        with pytest.raises(ValueError, match="Companion journey with ID 9999 not found"):
            handle_match(journey_id=9999, role=JourneyRole.COMPANION, db=db_session)

    def test_companion_already_matched_passenger_excluded(self, db_session, sample_companion_payload, sample_passenger_payload):
        """Already matched passengers are excluded from candidates."""
        from datetime import datetime, timezone
        companion1 = make_companion(db_session, {**sample_companion_payload, "userId": 10})
        companion2 = make_companion(db_session, {**sample_companion_payload, "userId": 11})
        passenger = make_passenger(db_session, sample_passenger_payload)

        # Pre-match passenger with companion1
        fj = FoundJourney(
            companionJourneyId=companion1.id,
            passengerJourneyId=passenger.id,
            status="WAITING",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(fj)
        db_session.commit()

        # companion2 should find no candidates (passenger already matched)
        response = handle_match(journey_id=companion2.id, role=JourneyRole.COMPANION, db=db_session)
        assert response.found_journey_ids == []


# ---------------------------------------------------------------------------
# PASSENGER role
# ---------------------------------------------------------------------------

class TestHandleMatchPassenger:

    def test_passenger_match_found(self, db_session, sample_companion_payload, sample_passenger_payload):
        """A passenger with a matching companion → 1 FoundJourney created."""
        companion = make_companion(db_session, sample_companion_payload)
        passenger = make_passenger(db_session, sample_passenger_payload)

        response = handle_match(journey_id=passenger.id, role=JourneyRole.PASSENGER, db=db_session)

        assert len(response.found_journey_ids) == 1
        assert "Found and saved 1 match(es)" in response.message

        row = db_session.query(FoundJourney).filter(FoundJourney.id == response.found_journey_ids[0]).first()
        assert row is not None
        assert row.passengerJourneyId == passenger.id
        assert row.companionJourneyId == companion.id

    def test_passenger_no_candidates(self, db_session, sample_passenger_payload):
        """A passenger with no companions → 0 matches."""
        passenger = make_passenger(db_session, sample_passenger_payload)

        response = handle_match(journey_id=passenger.id, role=JourneyRole.PASSENGER, db=db_session)

        assert response.found_journey_ids == []
        assert "Found and saved 0 match(es)" in response.message

    def test_no_match_when_criteria_differ(self, db_session, sample_companion_payload, sample_passenger_payload):
        """A passenger and a companion with different addresses, coords AND times → 0 matches."""
        different_payload = {
            **sample_companion_payload,
            "departureAddress": "Bordeaux",
            "arrivalAddress": "Nantes",
            "departureLat": 44.8378,
            "departureLon": -0.5792,
            "arrivalLat": 47.2184,
            "arrivalLon": -1.5536,
            "departureTime": datetime(2024, 6, 15, 8, 0),
            "arrivalTime": datetime(2024, 6, 15, 12, 0),
        }
        make_companion(db_session, different_payload)
        passenger = make_passenger(db_session, sample_passenger_payload)

        response = handle_match(journey_id=passenger.id, role=JourneyRole.PASSENGER, db=db_session)

        assert response.found_journey_ids == []

    def test_passenger_not_found_raises_value_error(self, db_session):
        """A non-existent passenger ID → ValueError raised."""
        with pytest.raises(ValueError, match="Passenger journey with ID 9999 not found"):
            handle_match(journey_id=9999, role=JourneyRole.PASSENGER, db=db_session)

    def test_passenger_already_matched_companion_excluded(self, db_session, sample_companion_payload, sample_passenger_payload):
        """Already matched companions are excluded from candidates."""
        from datetime import datetime, timezone
        companion = make_companion(db_session, sample_companion_payload)
        passenger1 = make_passenger(db_session, {**sample_passenger_payload, "userId": 20})
        passenger2 = make_passenger(db_session, {**sample_passenger_payload, "userId": 21})

        # Pre-match companion with passenger1
        fj = FoundJourney(
            companionJourneyId=companion.id,
            passengerJourneyId=passenger1.id,
            status="WAITING",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(fj)
        db_session.commit()

        # passenger2 should find no candidates (companion already matched)
        response = handle_match(journey_id=passenger2.id, role=JourneyRole.PASSENGER, db=db_session)
        assert response.found_journey_ids == []
