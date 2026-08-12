import logging
import os
import httpx

logger = logging.getLogger(__name__)

CALLBACK_PATH = "/journeys/match"


def notify_match_result(
    found_journey_ids: list[int],
) -> None:
    """
    Send a POST request to the Companion API to notify it that matches were found.

    The callback URL is built from COMPANION_API_URL + /journeys/match.
    The request is authenticated with the COMPANION_API_KEY header.

    If COMPANION_API_URL or COMPANION_API_KEY is not set, or if the request fails,
    the error is logged and execution continues (fail silently — the match is
    already persisted in DB).
    """
    api_url = os.getenv("COMPANION_API_URL")
    api_key = os.getenv("COMPANION_API_KEY")

    if not api_url:
        logger.warning("COMPANION_API_URL is not set. Skipping callback notification.")
        return

    if not api_key:
        logger.warning("COMPANION_API_KEY is not set. Skipping callback notification.")
        return

    callback_url = api_url.rstrip("/") + CALLBACK_PATH

    payload = {
        "data": found_journey_ids,
    }

    headers = {
        "x-api-key": api_key,
    }

    try:
        response = httpx.post(callback_url, json=payload, headers=headers, timeout=10.0)
        response.raise_for_status()
        logger.info(
            f"Companion API notified successfully (status {response.status_code}) "
            f"for found_journey_ids={found_journey_ids}"
        )
    except httpx.HTTPStatusError as e:
        logger.error(
            f"Companion API callback returned an error: "
            f"{e.response.status_code} – {e.response.text}"
        )
    except httpx.RequestError as e:
        logger.error(f"Companion API callback request failed: {e}")
