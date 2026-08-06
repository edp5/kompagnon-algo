import pytest
import httpx
from unittest.mock import patch, MagicMock
from src.notifier.match_notifier import notify_match_result

BASE_URL = "http://companion-api.test"
CALLBACK_URL = BASE_URL + "/api/journeys/match"


class TestNotifyMatchResult:

    def test_success(self):
        """Successful POST to the Companion API — no exception raised."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"COMPANION_API_BASE_URL": BASE_URL}), \
             patch("src.notifier.match_notifier.httpx.post", return_value=mock_response) as mock_post:
            notify_match_result(
                found_journey_ids=[1, 2],
                journey_id=42,
                role="companion",
            )

        mock_post.assert_called_once_with(
            CALLBACK_URL,
            json={
                "found_journey_ids": [1, 2],
                "journey_id": 42,
                "role": "companion",
            },
            timeout=10.0,
        )
        mock_response.raise_for_status.assert_called_once()

    def test_no_base_url_configured(self, caplog):
        """If COMPANION_API_BASE_URL is not set, log a warning and return silently."""
        import logging
        with patch.dict("os.environ", {}, clear=True), \
             patch("src.notifier.match_notifier.httpx.post") as mock_post, \
             caplog.at_level(logging.WARNING, logger="src.notifier.match_notifier"):
            import os
            os.environ.pop("COMPANION_API_BASE_URL", None)
            notify_match_result(found_journey_ids=[1], journey_id=1, role="companion")

        mock_post.assert_not_called()
        assert any("COMPANION_API_BASE_URL" in record.message for record in caplog.records)

    def test_http_status_error_is_logged_not_raised(self, caplog):
        """An HTTP error response from the Companion API must be logged, not raised."""
        import logging

        error_response = MagicMock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"
        http_error = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=error_response,
        )

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = http_error

        with patch.dict("os.environ", {"COMPANION_API_BASE_URL": BASE_URL}), \
             patch("src.notifier.match_notifier.httpx.post", return_value=mock_response), \
             caplog.at_level(logging.ERROR, logger="src.notifier.match_notifier"):
            notify_match_result(found_journey_ids=[1], journey_id=1, role="companion")

        assert any("error" in record.message.lower() or "500" in record.message for record in caplog.records)

    def test_request_error_is_logged_not_raised(self, caplog):
        """A network error (timeout, connection refused) must be logged, not raised."""
        import logging

        with patch.dict("os.environ", {"COMPANION_API_BASE_URL": BASE_URL}), \
             patch(
                 "src.notifier.match_notifier.httpx.post",
                 side_effect=httpx.RequestError("Connection refused", request=MagicMock()),
             ), \
             caplog.at_level(logging.ERROR, logger="src.notifier.match_notifier"):
            notify_match_result(found_journey_ids=[1], journey_id=1, role="companion")

        assert any("Connection refused" in record.message for record in caplog.records)

    def test_payload_contains_all_fields(self):
        """Callback payload must contain found_journey_ids, journey_id, and role."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        captured_payload = {}

        def capture_post(url, json, timeout):
            captured_payload.update(json)
            return mock_response

        with patch.dict("os.environ", {"COMPANION_API_BASE_URL": BASE_URL}), \
             patch("src.notifier.match_notifier.httpx.post", side_effect=capture_post):
            notify_match_result(
                found_journey_ids=[10, 20, 30],
                journey_id=99,
                role="passenger",
            )

        assert captured_payload["found_journey_ids"] == [10, 20, 30]
        assert captured_payload["journey_id"] == 99
        assert captured_payload["role"] == "passenger"
