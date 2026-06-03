import pytest
import logging
from datetime import datetime, timezone
from src.algorithm.main import run_algorithm
from src.db.models import CompanionJourney, PassengerJourney, FoundJourney

def test_run_algorithm_with_db(db_session, caplog):
    # Setup test data in the test DB
    companion = CompanionJourney(
        userId=1, 
        departureTime=datetime.now(timezone.utc), 
        arrivalTime=datetime.now(timezone.utc),
        departureAddress="Paris", 
        arrivalAddress="Lyon",
        departureLon=2.3522, 
        departureLat=48.8566, 
        arrivalLon=4.8357, 
        arrivalLat=45.7640
    )
    
    passenger = PassengerJourney(
        userId=2, 
        departureTime=datetime.now(timezone.utc), 
        arrivalTime=datetime.now(timezone.utc),
        departureAddress="Paris", 
        arrivalAddress="Lyon",
        departureLon=2.3522, 
        departureLat=48.8566, 
        arrivalLon=4.8357, 
        arrivalLat=45.7640
    )
    
    db_session.add(companion)
    db_session.add(passenger)
    db_session.commit()
    
    # Refresh to get IDs
    db_session.refresh(companion)
    db_session.refresh(passenger)
    
    # Run the algorithm and pass the test database session so it doesn't touch the prod DB
    with caplog.at_level(logging.INFO):
        run_algorithm(db_session)
    
    # Verify the database was updated
    found_journeys = db_session.query(FoundJourney).all()
    assert len(found_journeys) == 1
    assert found_journeys[0].companionJourneyId == companion.id
    assert found_journeys[0].passengerJourneyId == passenger.id
    assert found_journeys[0].status == "WAITING"
    
    # Verify logs
    assert "Starting Kompagnon matching algorithm (PROD mode)..." in caplog.text
    assert "Successfully saved 1 matches to the DB." in caplog.text

def test_run_algorithm_no_match(db_session, caplog):
    # Setup test data that do NOT match
    companion = CompanionJourney(
        userId=1, 
        departureTime=datetime.now(timezone.utc), 
        arrivalTime=datetime.now(timezone.utc),
        departureAddress="Paris", 
        arrivalAddress="Lyon",
        departureLon=2.3, 
        departureLat=48.8, 
        arrivalLon=4.8, 
        arrivalLat=45.7
    )
    passenger = PassengerJourney(
        userId=2, 
        departureTime=datetime.now(timezone.utc), 
        arrivalTime=datetime.now(timezone.utc),
        departureAddress="Marseille", 
        arrivalAddress="Nice",
        departureLon=5.3, 
        departureLat=43.2, 
        arrivalLon=7.2, 
        arrivalLat=43.7
    )
    db_session.add(companion)
    db_session.add(passenger)
    db_session.commit()

    with caplog.at_level(logging.INFO):
        run_algorithm(db_session)

    assert "No matches found." in caplog.text

def test_run_algorithm_exception(monkeypatch, db_session, caplog):
    def mock_get_unmatched(*args, **kwargs):
        raise Exception("Mock DB error")
        
    import src.algorithm.main
    monkeypatch.setattr(src.algorithm.main, "get_unmatched_journeys", mock_get_unmatched)

    with caplog.at_level(logging.ERROR):
        run_algorithm(db_session)

    assert "Error during matching algorithm execution: Mock DB error" in caplog.text

def test_run_algorithm_with_mocked_session_local(monkeypatch, db_session, caplog):
    monkeypatch.setattr("src.algorithm.main.SessionLocal", lambda: db_session)
    
    with caplog.at_level(logging.INFO):
        run_algorithm(db_session=None)
        
    assert "Starting Kompagnon matching algorithm (PROD mode)..." in caplog.text
