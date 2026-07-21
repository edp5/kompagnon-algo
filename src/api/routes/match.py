from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from src.api.schema import MatchRequest, MatchResponse
from src.controller.match_controller import handle_match, run_match_and_notify

router = APIRouter()


@router.post("/match", response_model=MatchResponse, status_code=status.HTTP_200_OK, tags=["Matching"])
def match_journey(payload: MatchRequest, background_tasks: BackgroundTasks):
    """
    Trigger matching logic for a specific journey ID.

    The endpoint validates that the journey exists and immediately returns HTTP 200.
    The actual matching algorithm runs asynchronously in a background task.
    Once a match is found, the Companion API is notified via a callback HTTP request.

    If the role is 'companion', it looks for matching 'passengers'.
    If the role is 'passenger', it looks for matching 'companions'.
    """
    try:
        response = handle_match(journey_id=payload.journey_id, role=payload.role)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    background_tasks.add_task(run_match_and_notify, payload.journey_id, payload.role)
    return response
