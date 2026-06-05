import logging
from typing import Optional
from sqlalchemy.orm import Session
from src.algorithm.matcher import find_matches
from src.db.session import SessionLocal
from src.repository.journey_repository import (
    get_unmatched_companions,
    get_unmatched_passengers,
    save_matches,
)

logger = logging.getLogger(__name__)

def run_algorithm(db_session: Optional[Session] = None):
    logger.info("Starting Kompagnon matching algorithm (PROD mode)...")

    db = db_session if db_session else SessionLocal()

    try:
        logger.info("Fetching unmatched journeys from DB...")
        companions_db = get_unmatched_companions(db)
        passengers_db = get_unmatched_passengers(db)

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

if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    run_algorithm()
