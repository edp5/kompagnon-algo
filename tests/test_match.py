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
    response = client.post("/match", json={
        "journey_id": 9999,
        "role": "companion"
    })
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

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
