from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import src.db.session as session
import src.db.models as models

router = APIRouter()

@router.post("/put-journey", tags=["Insert the 1st id for valid user plus the id for 2nd invalid user = journey id"], description="Insert the final, matched journeys in the database")
def put_journey(companion_id: int, passenger_id: int, db: Session = Depends(session.get_db)):
    """Insert the final, matched journeys in the database."""
    new_match = models.FoundJourney(
        companionJourneyId=companion_id,
        passengerJourneyId=passenger_id,
        status="WAITING"
    )
    db.add(new_match)
    db.commit()
    db.refresh(new_match)
    return {"message": "Putting journey ...", "data": {"id": new_match.id}}
