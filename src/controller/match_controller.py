import logging
from sqlalchemy.orm import Session
from src.api.schema import JourneyRole, MatchResponse
from src.algorithm.matcher import find_matches
from src.db.session import SessionLocal
from src.notifier.match_notifier import notify_match_result
from src.repository.journey_repository import (
    get_companion_by_id,
    get_passenger_by_id,
    get_unmatched_companions,
    get_unmatched_passengers,
    save_matches,
)

logger = logging.getLogger(__name__)


def _journey_to_dict(j) -> dict:
    """Convert a CompanionJourney or PassengerJourney ORM object to a plain dict."""
    return {
        "id": j.id,
        "departureAddress": j.departureAddress,
        "arrivalAddress": j.arrivalAddress,
        "departureLat": float(j.departureLat),
        "departureLon": float(j.departureLon),
        "arrivalLat": float(j.arrivalLat),
        "arrivalLon": float(j.arrivalLon),
        "departureTime": j.departureTime,
        "arrivalTime": j.arrivalTime,
    }


def run_match_and_notify(journey_id: int, role: JourneyRole) -> None:
    """
    Background task: run the matching algorithm for the given journey and, if
    matches are found, notify the Companion API via HTTP callback.

    Opens its own DB session so it can run independently of the request lifecycle.
    Raises ValueError if the journey is not found (will be logged by FastAPI's
    background task machinery).
    """
    db: Session = SessionLocal()
    try:
        if role == JourneyRole.COMPANION:
            target = get_companion_by_id(db, journey_id)
            if not target:
                raise ValueError(f"Companion journey with ID {journey_id} not found")

            candidates = get_unmatched_passengers(db)
            companions = [_journey_to_dict(target)]
            passengers = [_journey_to_dict(p) for p in candidates]

        else:  # PASSENGER
            target = get_passenger_by_id(db, journey_id)
            if not target:
                raise ValueError(f"Passenger journey with ID {journey_id} not found")

            candidates = get_unmatched_companions(db)
            companions = [_journey_to_dict(c) for c in candidates]
            passengers = [_journey_to_dict(target)]

        logger.info(
            f"[background] Running matching for {role} journey ID {journey_id} "
            f"against {len(candidates)} candidate(s)."
        )

        matches = find_matches(companions, passengers)

        found_journey_ids: list[int] = []
        if matches:
            found_journey_ids = save_matches(matches, db)
            db.commit()

        logger.info(
            f"[background] Matching completed: {len(found_journey_ids)} match(es) saved."
        )

        if found_journey_ids:
            notify_match_result(
                found_journey_ids=found_journey_ids,
                journey_id=journey_id,
                role=role.value,
            )

    except Exception as e:
        logger.error(
            f"[background] Error during matching for {role} journey ID {journey_id}: {e}"
        )
        db.rollback()
    finally:
        db.close()


def handle_match(journey_id: int, role: JourneyRole) -> MatchResponse:
    """
    Validate that the journey exists, then return an immediate acknowledgement.
    The actual matching is performed asynchronously via a BackgroundTask.
    """
    db: Session = SessionLocal()
    try:
        if role == JourneyRole.COMPANION:
            target = get_companion_by_id(db, journey_id)
            if not target:
                raise ValueError(f"Companion journey with ID {journey_id} not found")
        else:
            target = get_passenger_by_id(db, journey_id)
            if not target:
                raise ValueError(f"Passenger journey with ID {journey_id} not found")
    finally:
        db.close()

    logger.info(
        f"Match request received for {role} journey ID {journey_id}. "
        "Processing asynchronously."
    )
    return MatchResponse(message="Matching started in background")
