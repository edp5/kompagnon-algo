import logging
import os
import httpx

logger = logging.getLogger(__name__)

CALLBACK_PATH = "/api/journeys/match"


def notify_match_result(
    found_journey_ids: list[int],
    journey_id: int,
    role: str,
) -> None:
    """
    Send a POST request to the Companion API to notify it that a match was found.

    The callback URL is built from COMPANION_API_BASE_URL + /api/journeys/match.

    The payload contains the IDs of the newly created FoundJourney records, as well
    as the original journey_id and role that triggered the matching.

    If COMPANION_API_BASE_URL is not set or if the request fails, the error is
    logged and execution continues (fail silently — the match is already persisted in DB).
    """
    base_url = os.getenv("COMPANION_API_BASE_URL")
    if not base_url:
        logger.warning(
            "COMPANION_API_BASE_URL is not set. Skipping callback notification."
        )
        return

    callback_url = base_url.rstrip("/") + CALLBACK_PATH

    payload = {
        "found_journey_ids": found_journey_ids,
        "journey_id": journey_id,
        "role": role,
    }

    try:
        response = httpx.post(callback_url, json=payload, timeout=10.0)
        response.raise_for_status()
        logger.info(
            f"Companion API notified successfully (status {response.status_code}) "
            f"for journey_id={journey_id}, role={role}, "
            f"found_journey_ids={found_journey_ids}"
        )
    except httpx.HTTPStatusError as e:
        logger.error(
            f"Companion API callback returned an error for journey_id={journey_id}: "
            f"{e.response.status_code} – {e.response.text}"
        )
    except httpx.RequestError as e:
        logger.error(
            f"Companion API callback request failed for journey_id={journey_id}: {e}"
        )
