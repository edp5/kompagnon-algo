import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.db.models import CompanionJourney, PassengerJourney, FoundJourney

logger = logging.getLogger(__name__)


def get_unmatched_companions(db: Session) -> list[CompanionJourney]:
    """
    Fetch all CompanionJourney records that are not yet matched (not in FoundJourney).
    """
    subquery = db.query(FoundJourney.companionJourneyId).filter(
        FoundJourney.companionJourneyId.isnot(None)
    )
    return db.query(CompanionJourney).filter(CompanionJourney.id.notin_(subquery)).all()


def get_unmatched_passengers(db: Session) -> list[PassengerJourney]:
    """
    Fetch all PassengerJourney records that are not yet matched (not in FoundJourney).
    """
    subquery = db.query(FoundJourney.passengerJourneyId).filter(
        FoundJourney.passengerJourneyId.isnot(None)
    )
    return db.query(PassengerJourney).filter(PassengerJourney.id.notin_(subquery)).all()


def get_companion_by_id(db: Session, journey_id: int) -> Optional[CompanionJourney]:
    """
    Fetch a single CompanionJourney by its ID.
    """
    return db.query(CompanionJourney).filter(CompanionJourney.id == journey_id).first()


def get_passenger_by_id(db: Session, journey_id: int) -> Optional[PassengerJourney]:
    """
    Fetch a single PassengerJourney by its ID.
    """
    return db.query(PassengerJourney).filter(PassengerJourney.id == journey_id).first()


def save_matches(matches: list, db: Session) -> list[int]:
    """
    Save the list of matched dictionaries into the found_journeys table.
    Flushes to obtain IDs but does NOT commit — the caller owns the transaction.
    Returns the list of created FoundJourney IDs.
    Silently skips duplicates (IntegrityError) to ensure idempotency.

    Each insert is wrapped in a savepoint (db.begin_nested()) so that an
    IntegrityError on one row only rolls back that savepoint, leaving all
    previously flushed rows intact in the outer transaction.
    """
    created_ids: list[int] = []
    for match in matches:
        new_match = FoundJourney(
            companionJourneyId=match["companion_journey_id"],
            passengerJourneyId=match["passenger_journey_id"],
            status="WAITING",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        savepoint = db.begin_nested()
        db.add(new_match)
        try:
            db.flush()
            created_ids.append(new_match.id)
            savepoint.commit()
        except IntegrityError:
            savepoint.rollback()
    return created_ids
