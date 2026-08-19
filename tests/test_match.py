import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from src.db.models import CompanionJourney, PassengerJourney, FoundJourney


# ---------------------------------------------------------------------------
# NonClosingSession: wraps the test db_session so that db.close() called by
# handle_match's finally block is a no-op, keeping the test transaction alive.
# ---------------------------------------------------------------------------

class NonClosingSession:
    """Proxy that delegates all attribute access to the wrapped session
    except for close(), which is silently ignored."""

    def __init__(self, session):
        self._session = session

    def close(self):
        pass  # no-op — test transaction must stay open

    def __getattr__(self, name):
        return getattr(self._session, name)


# ---------------------------------------------------------------------------
# Helper: run the background matching logic inline using the test db_session,
# so we can inspect the DB state within the same transaction.
# ---------------------------------------------------------------------------

def _run_match_inline(journey_id, role, db_session):
    """
    Run run_match_and_notify synchronously, injecting the test db_session
    via a SessionLocal mock so no real Postgres connection is needed.
    """
    from src.api.schema import JourneyRole
    from src.controller.match_controller import run_match_and_notify
    role_enum = JourneyRole(role) if isinstance(role, str) else role
    with patch("src.controller.match_controller.SessionLocal", return_value=db_session), \
         patch("src.controller.match_controller.notify_match_result"):
        run_match_and_notify(journey_id=journey_id, role=role_enum)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_match_companion_immediate_response(client, db_session, sample_companion_payload):
    """Endpoint must return 200 immediately with an acknowledgement message."""
    companion = CompanionJourney(**sample_companion_payload)
    db_session.add(companion)
    db_session.commit()
    db_session.refresh(companion)
    companion_id = companion.id

    with patch("src.controller.match_controller.SessionLocal", return_value=NonClosingSession(db_session)), \
         patch("src.api.routes.match.run_match_and_notify"):
        response = client.post("/api/match", json={
            "journey_id": companion_id,
            "role": "companion"
        })

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "Matching started in background"


def test_match_passenger_immediate_response(client, db_session, sample_passenger_payload):
    """Endpoint must return 200 immediately for passenger role."""
    passenger = PassengerJourney(**sample_passenger_payload)
    db_session.add(passenger)
    db_session.commit()
    db_session.refresh(passenger)
    passenger_id = passenger.id

    with patch("src.controller.match_controller.SessionLocal", return_value=NonClosingSession(db_session)), \
         patch("src.api.routes.match.run_match_and_notify"):
        response = client.post("/api/match", json={
            "journey_id": passenger_id,
            "role": "passenger"
        })

    assert response.status_code == 200
    assert response.json()["message"] == "Matching started in background"


def test_match_journey_not_found(client, db_session):
    """Non-existent journey IDs must return 404 synchronously."""
    with patch("src.controller.match_controller.SessionLocal", return_value=NonClosingSession(db_session)), \
         patch("src.api.routes.match.run_match_and_notify"):
        response = client.post("/api/match", json={
            "journey_id": 9999,
            "role": "companion"
        })
    assert response.status_code == 404
    assert "Companion journey with ID 9999 not found" in response.json()["detail"]

    with patch("src.controller.match_controller.SessionLocal", return_value=NonClosingSession(db_session)), \
         patch("src.api.routes.match.run_match_and_notify"):
        response = client.post("/api/match", json={
            "journey_id": 9999,
            "role": "passenger"
        })
    assert response.status_code == 404
    assert "Passenger journey with ID 9999 not found" in response.json()["detail"]


def test_match_background_task_creates_found_journey(client, db_session, sample_companion_payload, sample_passenger_payload):
    """
    Verifies that the background task actually creates a FoundJourney row in DB.
    We capture the journey_id/role from the POST then run the task inline.
    """
    companion = CompanionJourney(**sample_companion_payload)
    passenger = PassengerJourney(**sample_passenger_payload)
    db_session.add(companion)
    db_session.add(passenger)
    db_session.commit()
    db_session.refresh(companion)
    db_session.refresh(passenger)
    companion_id = companion.id
    passenger_id = passenger.id

    with patch("src.controller.match_controller.SessionLocal", return_value=NonClosingSession(db_session)), \
         patch("src.api.routes.match.run_match_and_notify"):
        response = client.post("/api/match", json={
            "journey_id": companion_id,
            "role": "companion"
        })

    assert response.status_code == 200

    # Run the background logic inline
    _run_match_inline(companion_id, "companion", db_session)

    match_in_db = db_session.query(FoundJourney).filter(
        FoundJourney.companionJourneyId == companion_id
    ).first()
    assert match_in_db is not None
    assert match_in_db.companionJourneyId == companion_id
    assert match_in_db.passengerJourneyId == passenger_id
    assert match_in_db.companionStatus == "waiting"
    assert match_in_db.passengerStatus == "waiting"


def test_match_no_candidates_no_found_journey(client, db_session, sample_companion_payload):
    """
    When there are no candidates, no FoundJourney is created.
    """
    companion = CompanionJourney(**sample_companion_payload)
    db_session.add(companion)
    db_session.commit()
    db_session.refresh(companion)
    companion_id = companion.id

    with patch("src.controller.match_controller.SessionLocal", return_value=NonClosingSession(db_session)), \
         patch("src.api.routes.match.run_match_and_notify"):
        response = client.post("/api/match", json={
            "journey_id": companion_id,
            "role": "companion"
        })

    assert response.status_code == 200

    # Run background logic — no passengers → no matches
    _run_match_inline(companion_id, "companion", db_session)
    assert db_session.query(FoundJourney).count() == 0
