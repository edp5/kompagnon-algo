import pytest
from datetime import datetime
from src.db.models import CompanionJourney, PassengerJourney, FoundJourney

def test_match_companion_success(client, db_session, sample_companion_payload, sample_passenger_payload):
    # 1. Insert a companion journey
    companion = CompanionJourney(**sample_companion_payload)
    db_session.add(companion)
    db_session.commit()
    db_session.refresh(companion)

    # 2. Insert a matching passenger journey (same departure & arrival address)
    passenger = PassengerJourney(**sample_passenger_payload)
    db_session.add(passenger)
    db_session.commit()
    db_session.refresh(passenger)

    # 3. Call the match API
    response = client.post("/match", json={
        "journey_id": companion.id,
        "role": "companion"
    })

    assert response.status_code == 200
    data = response.json()
    assert len(data["found_journey_ids"]) == 1
    assert "Found and saved 1 match(es)" in data["message"]

    # Verify database insertion
    match_in_db = db_session.query(FoundJourney).first()
    assert match_in_db is not None
    assert match_in_db.companionJourneyId == companion.id
    assert match_in_db.passengerJourneyId == passenger.id
    assert match_in_db.status == "WAITING"

def test_match_passenger_success(client, db_session, sample_companion_payload, sample_passenger_payload):
    # 1. Insert a companion journey
    companion = CompanionJourney(**sample_companion_payload)
    db_session.add(companion)
    db_session.commit()
    db_session.refresh(companion)

    # 2. Insert a matching passenger journey
    passenger = PassengerJourney(**sample_passenger_payload)
    db_session.add(passenger)
    db_session.commit()
    db_session.refresh(passenger)

    # 3. Call the match API targeting the passenger
    response = client.post("/match", json={
        "journey_id": passenger.id,
        "role": "passenger"
    })

    assert response.status_code == 200
    data = response.json()
    assert len(data["found_journey_ids"]) == 1

def test_match_journey_not_found(client):
    # Companion role
    response = client.post("/match", json={
        "journey_id": 9999,
        "role": "companion"
    })
    assert response.status_code == 404
    assert "Companion journey with ID 9999 not found" in response.json()["detail"]

    # Passenger role
    response = client.post("/match", json={
        "journey_id": 9999,
        "role": "passenger"
    })
    assert response.status_code == 404
    assert "Passenger journey with ID 9999 not found" in response.json()["detail"]

def test_match_no_candidates(client, db_session, sample_companion_payload):
    # Insert companion but no passenger
    companion = CompanionJourney(**sample_companion_payload)
    db_session.add(companion)
    db_session.commit()
    db_session.refresh(companion)

    response = client.post("/match", json={
        "journey_id": companion.id,
        "role": "companion"
    })

    assert response.status_code == 200
    data = response.json()
    assert len(data["found_journey_ids"]) == 0
    assert "Found and saved 0 match(es)" in data["message"]


def test_match_returns_only_ids_created_by_current_call(client, db_session, sample_companion_payload, sample_passenger_payload):
    """
    Prove that /match returns only IDs created by the current request.
    A pre-existing FoundJourney row for a different pair must not appear in the response.
    """
    from src.db.models import FoundJourney
    from datetime import datetime, timezone

    # 1. Insert journeys for a pre-existing match (different userId pair)
    pre_companion_payload = {**sample_companion_payload, "userId": 10}
    pre_passenger_payload = {**sample_passenger_payload, "userId": 20}
    pre_companion = CompanionJourney(**pre_companion_payload)
    pre_passenger = PassengerJourney(**pre_passenger_payload)
    db_session.add(pre_companion)
    db_session.add(pre_passenger)
    db_session.commit()
    db_session.refresh(pre_companion)
    db_session.refresh(pre_passenger)

    # Manually create the pre-existing FoundJourney row
    pre_existing = FoundJourney(
        companionJourneyId=pre_companion.id,
        passengerJourneyId=pre_passenger.id,
        status="WAITING",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(pre_existing)
    db_session.commit()
    db_session.refresh(pre_existing)
    pre_existing_id = pre_existing.id

    # 2. Insert a new pair that will be matched by the API call
    new_companion = CompanionJourney(**{**sample_companion_payload, "userId": 30})
    new_passenger = PassengerJourney(**{**sample_passenger_payload, "userId": 40})
    db_session.add(new_companion)
    db_session.add(new_passenger)
    db_session.commit()
    db_session.refresh(new_companion)
    db_session.refresh(new_passenger)

    # 3. Call /match for the new companion — it should only match new_passenger
    response = client.post("/match", json={
        "journey_id": new_companion.id,
        "role": "companion"
    })

    assert response.status_code == 200
    data = response.json()
    # Only 1 new match must be returned, and it must NOT include the pre-existing row
    assert len(data["found_journey_ids"]) == 1
    assert pre_existing_id not in data["found_journey_ids"]


def test_match_duplicate_is_idempotent(client, db_session, sample_companion_payload, sample_passenger_payload):
    """
    Calling /match twice for the same journey must not create a duplicate row
    and must not raise a 500 error (IntegrityError is handled gracefully).
    """
    # 1. Setup matching journeys
    companion = CompanionJourney(**sample_companion_payload)
    passenger = PassengerJourney(**sample_passenger_payload)
    db_session.add(companion)
    db_session.add(passenger)
    db_session.commit()
    db_session.refresh(companion)
    db_session.refresh(passenger)

    # 2. First call — should succeed and create 1 match
    response1 = client.post("/match", json={"journey_id": companion.id, "role": "companion"})
    assert response1.status_code == 200
    assert len(response1.json()["found_journey_ids"]) == 1

    # 3. Second call — duplicate must be silently skipped, not crash
    response2 = client.post("/match", json={"journey_id": companion.id, "role": "companion"})
    assert response2.status_code == 200
    # The companion is now already matched so get_unmatched_journeys should return 0 candidates,
    # meaning 0 new rows are created.
    data2 = response2.json()
    assert len(data2["found_journey_ids"]) == 0

    # Verify only 1 row exists in the DB (no duplicate)
    from src.db.models import FoundJourney
    count = db_session.query(FoundJourney).filter(
        FoundJourney.companionJourneyId == companion.id,
        FoundJourney.passengerJourneyId == passenger.id,
    ).count()
    assert count == 1
