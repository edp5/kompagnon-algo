from pydantic import BaseModel, Field
from enum import Enum


class JourneyRole(str, Enum):
    COMPANION = "companion"
    PASSENGER = "passenger"


class MatchRequest(BaseModel):
    journey_id: int = Field(..., description="The ID of the journey that was just created")
    role: JourneyRole = Field(..., description="The role of the user (companion or passenger)")


class MatchResponse(BaseModel):
    message: str = Field(..., description="Acknowledgement message")
