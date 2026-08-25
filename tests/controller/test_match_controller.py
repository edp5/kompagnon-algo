import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from src.db.models import CompanionJourney, PassengerJourney, FoundJourney
from src.api.schema import JourneyRole
from src.controller.match_controller import handle_match, run_match_and_notify
from tests.conftest import NonClosingSession

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
# handle_match – validates existence and returns immediate acknowledgement
# ---------------------------------------------------------------------------

class TestHandleMatch:

    def test_companion_exists_returns_ack(self, db_session, sample_companion_payload):
        """handle_match returns an ack message when the companion exists."""
        companion = make_companion(db_session, sample_companion_payload)
        companion_id = companion.id

        with patch("src.controller.match_controller.SessionLocal", return_value=NonClosingSession(db_session)):
            response = handle_match(journey_id=companion_id, role=JourneyRole.COMPANION)

        assert response.message == "Matching started in background"

    def test_passenger_exists_returns_ack(self, db_session, sample_passenger_payload):
        """handle_match returns an ack message when the passenger exists."""
        passenger = make_passenger(db_session, sample_passenger_payload)
        passenger_id = passenger.id

        with patch("src.controller.match_controller.SessionLocal", return_value=NonClosingSession(db_session)):
            response = handle_match(journey_id=passenger_id, role=JourneyRole.PASSENGER)

        assert response.message == "Matching started in background"

    def test_companion_not_found_raises_value_error(self, db_session):
        """A non-existent companion ID → ValueError raised."""
        with patch("src.controller.match_controller.SessionLocal", return_value=NonClosingSession(db_session)):
            with pytest.raises(ValueError, match="Companion journey with ID 9999 not found"):
                handle_match(journey_id=9999, role=JourneyRole.COMPANION)

    def test_passenger_not_found_raises_value_error(self, db_session):
        """A non-existent passenger ID → ValueError raised."""
        with patch("src.controller.match_controller.SessionLocal", return_value=NonClosingSession(db_session)):
            with pytest.raises(ValueError, match="Passenger journey with ID 9999 not found"):
                handle_match(journey_id=9999, role=JourneyRole.PASSENGER)


# ---------------------------------------------------------------------------
# run_match_and_notify – background task
# ---------------------------------------------------------------------------

class TestRunMatchAndNotify:

    def test_companion_match_found_and_notified(self, db_session, sample_companion_payload, sample_passenger_payload):
        """A companion with a matching passenger → 1 FoundJourney + notifier called."""
        companion = make_companion(db_session, sample_companion_payload)
        passenger = make_passenger(db_session, sample_passenger_payload)
        # Capture IDs before any session manipulation
        companion_id = companion.id
        passenger_id = passenger.id

        with patch("src.controller.match_controller.SessionLocal", return_value=db_session), \
             patch("src.controller.match_controller.notify_match_result") as mock_notify:
            run_match_and_notify(journey_id=companion_id, role=JourneyRole.COMPANION)

        row = db_session.query(FoundJourney).filter(
            FoundJourney.companionJourneyId == companion_id
        ).first()
        assert row is not None
        assert row.companionJourneyId == companion_id
        assert row.passengerJourneyId == passenger_id
        assert row.companionStatus == "waiting"
        assert row.passengerStatus == "waiting"

        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args[1] if mock_notify.call_args[1] else {}
        call_args = mock_notify.call_args[0] if mock_notify.call_args[0] else []
        # Check notifier was given the FoundJourney id
        assert row.id in (call_kwargs.get("found_journey_ids") or call_args[0])

    def test_passenger_match_found_and_notified(self, db_session, sample_companion_payload, sample_passenger_payload):
        """A passenger with a matching companion → 1 FoundJourney + notifier called."""
        companion = make_companion(db_session, sample_companion_payload)
        passenger = make_passenger(db_session, sample_passenger_payload)

        with patch("src.controller.match_controller.SessionLocal", return_value=db_session), \
             patch("src.controller.match_controller.notify_match_result") as mock_notify:
            run_match_and_notify(journey_id=passenger.id, role=JourneyRole.PASSENGER)

        row = db_session.query(FoundJourney).first()
        assert row is not None
        mock_notify.assert_called_once()

    def test_no_candidates_no_notify(self, db_session, sample_companion_payload):
        """A companion with no passengers → 0 matches, notifier NOT called."""
        companion = make_companion(db_session, sample_companion_payload)

        with patch("src.controller.match_controller.SessionLocal", return_value=db_session), \
             patch("src.controller.match_controller.notify_match_result") as mock_notify:
            run_match_and_notify(journey_id=companion.id, role=JourneyRole.COMPANION)

        assert db_session.query(FoundJourney).count() == 0
        mock_notify.assert_not_called()

    def test_no_match_when_criteria_differ(self, db_session, sample_companion_payload, sample_passenger_payload):
        """Different addresses and coords → 0 matches, notifier NOT called."""
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

        with patch("src.controller.match_controller.SessionLocal", return_value=db_session), \
             patch("src.controller.match_controller.notify_match_result") as mock_notify:
            run_match_and_notify(journey_id=companion.id, role=JourneyRole.COMPANION)

        assert db_session.query(FoundJourney).count() == 0
        mock_notify.assert_not_called()

    def test_journey_not_found_does_not_raise(self, db_session):
        """
        If the companion journey is not found in the background task, the error is caught
        and does not propagate (fail gracefully in background context).
        """
        with patch("src.controller.match_controller.SessionLocal", return_value=db_session):
            # Should not raise – error is caught internally
            run_match_and_notify(journey_id=9999, role=JourneyRole.COMPANION)

    def test_passenger_journey_not_found_does_not_raise(self, db_session):
        """
        If the passenger journey is not found in the background task, the error is caught
        and does not propagate (fail gracefully in background context).
        Covers the `raise ValueError` on line 56 of match_controller.py.
        """
        with patch("src.controller.match_controller.SessionLocal", return_value=db_session):
            # Should not raise – error is caught internally
            run_match_and_notify(journey_id=9999, role=JourneyRole.PASSENGER)

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
            companionStatus="waiting",
            passengerStatus="waiting",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(fj)
        db_session.commit()

        with patch("src.controller.match_controller.SessionLocal", return_value=db_session), \
             patch("src.controller.match_controller.notify_match_result") as mock_notify:
            run_match_and_notify(journey_id=companion2.id, role=JourneyRole.COMPANION)

        # Only the pre-existing FoundJourney must be there; no new one
        assert db_session.query(FoundJourney).count() == 1
        mock_notify.assert_not_called()

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
            companionStatus="waiting",
            passengerStatus="waiting",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(fj)
        db_session.commit()

        with patch("src.controller.match_controller.SessionLocal", return_value=db_session), \
             patch("src.controller.match_controller.notify_match_result") as mock_notify:
            run_match_and_notify(journey_id=passenger2.id, role=JourneyRole.PASSENGER)

        assert db_session.query(FoundJourney).count() == 1
        mock_notify.assert_not_called()
