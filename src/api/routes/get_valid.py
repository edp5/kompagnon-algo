from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import src.db.session as session
import src.db.models as models

router = APIRouter()

@router.get("/get-valid", tags=["Get the list of journeys of valid users"], description="Get the table of valid user from table \"companion_journeys\"")
def get_valid_users_list(db: Session = Depends(session.get_db)):
    """Get the table of valid user."""
    try:
        journeys = db.query(models.CompanionJourney).all()
        return {
            "message": "Valid users journeys found successfully." if journeys else "No users found.",
            "data": [
                {
                    "id": j.id,
                    "userId": j.userId,
                    "departureAddress": j.departureAddress,
                    "arrivalAddress": j.arrivalAddress
                } for j in journeys
            ]
        }
    except Exception as e:
        return {
            "message": f"No users found. Error: {str(e)}",
            "data": []
        }
