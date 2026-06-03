from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db.models import CompanionJourney, PassengerJourney
from src.api.schema import MatchRequest, MatchResponse, JourneyRole
from src.algorithm.matcher import find_matches
from src.algorithm.main import save_matches, get_unmatched_journeys

router = APIRouter()

@router.post("/match", response_model=MatchResponse, status_code=status.HTTP_200_OK, tags=["Matching"])
def match_journey(payload: MatchRequest, db: Session = Depends(get_db)):
    """
    Trigger matching logic for a specific journey ID.
    If the role is 'companion', it looks for matching 'passengers'.
    If the role is 'passenger', it looks for matching 'companions'.
    """
    # 1. Fetch the target journey
    if payload.role == JourneyRole.COMPANION:
        target = db.query(CompanionJourney).filter(CompanionJourney.id == payload.journey_id).first()
        if not target:
            raise HTTPException(status_code=404, detail=f"Companion journey with ID {payload.journey_id} not found")
        
        # Fetch unmatched passenger journeys (candidates)
        candidates_db = get_unmatched_journeys(db, PassengerJourney)
        
        # Convert objects to dicts for matcher
        companions = [{"id": target.id, "departureAddress": target.departureAddress, "arrivalAddress": target.arrivalAddress}]
        passengers = [{"id": p.id, "departureAddress": p.departureAddress, "arrivalAddress": p.arrivalAddress} for p in candidates_db]
        
    else:  # PASSENGER
        target = db.query(PassengerJourney).filter(PassengerJourney.id == payload.journey_id).first()
        if not target:
            raise HTTPException(status_code=404, detail=f"Passenger journey with ID {payload.journey_id} not found")
        
        # Fetch unmatched companion journeys (candidates)
        candidates_db = get_unmatched_journeys(db, CompanionJourney)
        
        # Convert objects to dicts for matcher
        companions = [{"id": c.id, "departureAddress": c.departureAddress, "arrivalAddress": c.arrivalAddress} for c in candidates_db]
        passengers = [{"id": target.id, "departureAddress": target.departureAddress, "arrivalAddress": target.arrivalAddress}]

    # 2. Run the matching logic
    matches = find_matches(companions, passengers)
    
    # 3. Save matches to DB and collect their IDs
    found_journey_ids: list[int] = []
    if matches:
        found_journey_ids = save_matches(matches, db)
        db.commit()

    return MatchResponse(
        found_journey_ids=found_journey_ids,
        message=f"Found and saved {len(found_journey_ids)} match(es)"
    )
