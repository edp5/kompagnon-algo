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
    response = client.post("/api/match", json={
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
    assert match_in_db.companionStatus == "waiting"
    assert match_in_db.passengerStatus == "waiting"

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
    response = client.post("/api/match", json={
        "journey_id": passenger.id,
        "role": "passenger"
    })

    assert response.status_code == 200
    data = response.json()
    assert len(data["found_journey_ids"]) == 1

def test_match_journey_not_found(client):
    # Companion role
    response = client.post("/api/match", json={
        "journey_id": 9999,
        "role": "companion"
    })
    assert response.status_code == 404
    assert "Companion journey with ID 9999 not found" in response.json()["detail"]

    # Passenger role
    response = client.post("/api/match", json={
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

    response = client.post("/api/match", json={
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
        companionStatus="waiting",
        passengerStatus="waiting",
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
    response = client.post("/api/match", json={
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
    response1 = client.post("/api/match", json={"journey_id": companion.id, "role": "companion"})
    assert response1.status_code == 200
    assert len(response1.json()["found_journey_ids"]) == 1

    # 3. Second call — duplicate must be silently skipped, not crash
    response2 = client.post("/api/match", json={"journey_id": companion.id, "role": "companion"})
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


def test_match_mixed_batch_new_duplicate_new(db_session, sample_companion_payload, sample_passenger_payload):
    """
    Mixed batch [new_A, duplicate_B, new_C] must:
    - return exactly 2 IDs (A and C),
    - persist exactly those 2 rows in the DB,
    - leave the pre-existing duplicate row untouched (still 1 row for pair B).
    """
    from src.algorithm.main import save_matches
    from src.db.models import CompanionJourney, PassengerJourney, FoundJourney
    from datetime import datetime, timezone

    # --- helper to build a unique journey pair ---
    def make_pair(user_id_c, user_id_p):
        c = CompanionJourney(**{**sample_companion_payload, "userId": user_id_c})
        p = PassengerJourney(**{**sample_passenger_payload, "userId": user_id_p})
        db_session.add(c)
        db_session.add(p)
        db_session.commit()
        db_session.refresh(c)
        db_session.refresh(p)
        return c, p

    # Pair A (new)
    c_a, p_a = make_pair(101, 201)
    # Pair B (will be pre-inserted then offered again as duplicate)
    c_b, p_b = make_pair(102, 202)
    # Pair C (new)
    c_c, p_c = make_pair(103, 203)

    # Pre-insert pair B so it triggers an IntegrityError during the batch
    pre_b = FoundJourney(
        companionJourneyId=c_b.id,
        passengerJourneyId=p_b.id,
        companionStatus="waiting",
        passengerStatus="waiting",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(pre_b)
    db_session.commit()
    db_session.refresh(pre_b)

    # Build the mixed batch: [new_A, duplicate_B, new_C]
    batch = [
        {"companion_journey_id": c_a.id, "passenger_journey_id": p_a.id},
        {"companion_journey_id": c_b.id, "passenger_journey_id": p_b.id},  # duplicate
        {"companion_journey_id": c_c.id, "passenger_journey_id": p_c.id},
    ]

    created_ids = save_matches(batch, db_session)
    db_session.commit()

    # --- assertions ---
    # 1. Exactly 2 IDs returned (A and C); B was skipped
    assert len(created_ids) == 2, f"Expected 2 created IDs, got {len(created_ids)}: {created_ids}"

    # 2. Both returned IDs actually exist in the DB
    for fid in created_ids:
        row = db_session.query(FoundJourney).filter(FoundJourney.id == fid).first()
        assert row is not None, f"FoundJourney id={fid} not found in DB"

    # 3. Pair A is persisted
    row_a = db_session.query(FoundJourney).filter(
        FoundJourney.companionJourneyId == c_a.id,
        FoundJourney.passengerJourneyId == p_a.id,
    ).one_or_none()
    assert row_a is not None, "Pair A must be persisted"

    # 4. Pair C is persisted
    row_c = db_session.query(FoundJourney).filter(
        FoundJourney.companionJourneyId == c_c.id,
        FoundJourney.passengerJourneyId == p_c.id,
    ).one_or_none()
    assert row_c is not None, "Pair C must be persisted"

    # 5. Pair B still has exactly 1 row (no extra duplicate created)
    count_b = db_session.query(FoundJourney).filter(
        FoundJourney.companionJourneyId == c_b.id,
        FoundJourney.passengerJourneyId == p_b.id,
    ).count()
    assert count_b == 1, f"Pair B must have exactly 1 row, got {count_b}"

