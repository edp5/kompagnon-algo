import logging
import os
import httpx

logger = logging.getLogger(__name__)

CALLBACK_PATH = "/journeys/match"


def notify_match_result(
    found_journey_ids: list[int],
) -> None:
    """
    Send a POST request to the Kompagnon API to notify it that matches were found.

    The callback URL is built from KOMPAGNON_API_URL + /journeys/match.
    The request is authenticated with the KOMPAGNON_API_KEY header.

    If KOMPAGNON_API_URL or KOMPAGNON_API_KEY is not set, or if the request fails,
    the error is logged and execution continues (fail silently — the match is
    already persisted in DB). This function never raises.
    """
    api_url = os.getenv("KOMPAGNON_API_URL")
    api_key = os.getenv("KOMPAGNON_API_KEY")

    if not api_url:
        logger.warning("KOMPAGNON_API_URL is not set. Skipping callback notification.")
        return

    if not api_key:
        logger.warning("KOMPAGNON_API_KEY is not set. Skipping callback notification.")
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
            f"Kompagnon API notified successfully (status {response.status_code}) "
            f"for found_journey_ids={found_journey_ids}"
        )
    except httpx.HTTPStatusError as e:
        logger.error(
            f"Kompagnon API callback returned an error: "
            f"{e.response.status_code} – {e.response.text}"
        )
    except httpx.RequestError as e:
        logger.error(f"Kompagnon API callback request failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during Kompagnon API callback: {e}")
