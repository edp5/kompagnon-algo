import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.algorithm.matcher import find_matches
from src.db.session import SessionLocal
from src.db.models import CompanionJourney, PassengerJourney, FoundJourney
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def get_unmatched_journeys(db: Session, model):
    """
    Fetch journeys from the database that are not yet matched (not in FoundJourney).
    """
    if model == CompanionJourney:
        subquery = db.query(FoundJourney.companionJourneyId).filter(FoundJourney.companionJourneyId.isnot(None))
        return db.query(CompanionJourney).filter(CompanionJourney.id.notin_(subquery)).all()
    elif model == PassengerJourney:
        subquery = db.query(FoundJourney.passengerJourneyId).filter(FoundJourney.passengerJourneyId.isnot(None))
        return db.query(PassengerJourney).filter(PassengerJourney.id.notin_(subquery)).all()
    return []  # pragma: no cover

def run_algorithm(db_session: Optional[Session] = None):
    logger.info("Starting Kompagnon matching algorithm (PROD mode)...")
    
    # Use provided session or create a new one
    db = db_session if db_session else SessionLocal()
    
    try:
        logger.info("Fetching unmatched journeys from DB...")
        companions_db = get_unmatched_journeys(db, CompanionJourney)
        passengers_db = get_unmatched_journeys(db, PassengerJourney)
        
        # Convert SQLAlchemy objects to dicts for the matcher
        companions = [
            {
                "id": c.id, 
                "departureAddress": c.departureAddress, 
                "arrivalAddress": c.arrivalAddress
            } for c in companions_db
        ]
        passengers = [
            {
                "id": p.id, 
                "departureAddress": p.departureAddress, 
                "arrivalAddress": p.arrivalAddress
            } for p in passengers_db
        ]
        
        logger.info(f"Executing matching logic for {len(passengers)} passengers and {len(companions)} companions...")
        matches = find_matches(companions, passengers)
        
        logger.info("Matching Results:")
        if not matches:
            logger.info("No matches found.")
        else:
            saved_ids = save_matches(matches, db)
            db.commit()
            for match in matches:
                logger.info(f" - Saved Match: Passenger {match['passenger_journey_id']} <-> Companion {match['companion_journey_id']}")
            logger.info(f"Successfully saved {len(saved_ids)} matches to the DB.")
            
    except Exception as e:
        logger.error(f"Error during matching algorithm execution: {e}")
    finally:
        # Close the session only if we created it locally
        if not db_session:
            db.close()

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
            db.refresh(new_match)
            created_ids.append(new_match.id)
            savepoint.commit()
        except IntegrityError:
            savepoint.rollback()
    return created_ids

if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    run_algorithm()
