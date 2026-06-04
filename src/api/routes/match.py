from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.api.schema import MatchRequest, MatchResponse
from src.controller.match_controller import handle_match

router = APIRouter()

@router.post("/match", response_model=MatchResponse, status_code=status.HTTP_200_OK, tags=["Matching"])
def match_journey(payload: MatchRequest, db: Session = Depends(get_db)):
    """
    Trigger matching logic for a specific journey ID.
    If the role is 'companion', it looks for matching 'passengers'.
    If the role is 'passenger', it looks for matching 'companions'.
    """
    try:
        return handle_match(journey_id=payload.journey_id, role=payload.role, db=db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
