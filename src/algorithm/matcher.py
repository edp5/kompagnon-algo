import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def find_matches(companions: List[Dict[str, Any]], passengers: List[Dict[str, Any]]) -> List[Dict[str, int]]:
    """
    Find matches between passengers and companions based on departure and arrival addresses.
    Returns a list of dictionaries with 'companion_journey_id' and 'passenger_journey_id'.
    """
    matches = []
    logger.info(f"Starting matching process for {len(passengers)} passengers and {len(companions)} companions.")
    
    for passenger in passengers:
        for companion in companions:
            # Check for exact address match based on DB schema fields
            if (passenger.get("departureAddress") == companion.get("departureAddress") and 
                passenger.get("arrivalAddress") == companion.get("arrivalAddress")):
                
                logger.info(f"Match found: Passenger Journey {passenger['id']} with Companion Journey {companion['id']}")
                matches.append({
                    "passenger_journey_id": passenger["id"],
                    "companion_journey_id": companion["id"]
                })
                # We can choose to break here if 1 passenger maps to exactly 1 companion, but let's keep it 1-to-many logic for now or just 1-to-1.
                # In a real scenario, we might want to ensure a companion is not overbooked.
                
    logger.info(f"Matching process completed. Found {len(matches)} match(es).")
    return matches
