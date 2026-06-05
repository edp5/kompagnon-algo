import logging
from sqlalchemy.orm import Session
from src.api.schema import JourneyRole, MatchResponse
from src.algorithm.matcher import find_matches
from src.repository.journey_repository import (
    get_companion_by_id,
    get_passenger_by_id,
    get_unmatched_companions,
    get_unmatched_passengers,
    save_matches,
)

logger = logging.getLogger(__name__)


def handle_match(journey_id: int, role: JourneyRole, db: Session) -> MatchResponse:
    """
    Orchestrates the matching logic for a given journey:
    1. Fetch the target journey from the repository
    2. Fetch unmatched candidates from the repository
    3. Run the matching algorithm
    4. Save matches via the repository
    5. Return the result

    Raises ValueError if the journey is not found.
    """
    if role == JourneyRole.COMPANION:
        target = get_companion_by_id(db, journey_id)
        if not target:
            raise ValueError(f"Companion journey with ID {journey_id} not found")

        candidates = get_unmatched_passengers(db)
        companions = [{"id": target.id, "departureAddress": target.departureAddress, "arrivalAddress": target.arrivalAddress}]
        passengers = [{"id": p.id, "departureAddress": p.departureAddress, "arrivalAddress": p.arrivalAddress} for p in candidates]

    else:  # PASSENGER
        target = get_passenger_by_id(db, journey_id)
        if not target:
            raise ValueError(f"Passenger journey with ID {journey_id} not found")

        candidates = get_unmatched_companions(db)
        companions = [{"id": c.id, "departureAddress": c.departureAddress, "arrivalAddress": c.arrivalAddress} for c in candidates]
        passengers = [{"id": target.id, "departureAddress": target.departureAddress, "arrivalAddress": target.arrivalAddress}]

    logger.info(f"Running matching for {role} journey ID {journey_id} against {len(candidates)} candidate(s).")

    matches = find_matches(companions, passengers)

    found_journey_ids: list[int] = []
    if matches:
        found_journey_ids = save_matches(matches, db)
        db.commit()

    logger.info(f"Matching completed: {len(found_journey_ids)} match(es) saved.")

    return MatchResponse(
        found_journey_ids=found_journey_ids,
        message=f"Found and saved {len(found_journey_ids)} match(es)"
    )
