import pytest
import httpx
from unittest.mock import patch, MagicMock
from src.notifier.match_notifier import notify_match_result

API_URL = "http://kompagnon-api.test/api"
API_KEY = "test-api-key"
CALLBACK_URL = API_URL + "/journeys/match"


class TestNotifyMatchResult:

    def test_success(self):
        """Successful POST to the Kompagnon API — no exception raised."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"KOMPAGNON_API_URL": API_URL, "KOMPAGNON_API_KEY": API_KEY}), \
             patch("src.notifier.match_notifier.httpx.post", return_value=mock_response) as mock_post:
            notify_match_result(found_journey_ids=[1, 2])

        mock_post.assert_called_once_with(
            CALLBACK_URL,
            json={"data": [1, 2]},
            headers={"x-api-key": API_KEY},
            timeout=10.0,
        )
        mock_response.raise_for_status.assert_called_once()

    def test_no_api_url_configured(self, caplog):
        """If KOMPAGNON_API_URL is not set, log a warning and return silently."""
        import logging
        with patch.dict("os.environ", {}, clear=True), \
             patch("src.notifier.match_notifier.httpx.post") as mock_post, \
             caplog.at_level(logging.WARNING, logger="src.notifier.match_notifier"):
            import os
            os.environ.pop("KOMPAGNON_API_URL", None)
            notify_match_result(found_journey_ids=[1])

        mock_post.assert_not_called()
        assert any("KOMPAGNON_API_URL" in record.message for record in caplog.records)

    def test_no_api_key_configured(self, caplog):
        """If KOMPAGNON_API_KEY is not set, log a warning and return silently."""
        import logging
        with patch.dict("os.environ", {"KOMPAGNON_API_URL": API_URL}, clear=True), \
             patch("src.notifier.match_notifier.httpx.post") as mock_post, \
             caplog.at_level(logging.WARNING, logger="src.notifier.match_notifier"):
            import os
            os.environ.pop("KOMPAGNON_API_KEY", None)
            notify_match_result(found_journey_ids=[1])

        mock_post.assert_not_called()
        assert any("KOMPAGNON_API_KEY" in record.message for record in caplog.records)

    def test_http_status_error_is_logged_not_raised(self, caplog):
        """An HTTP error response from the Kompagnon API must be logged, not raised."""
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

        with patch.dict("os.environ", {"KOMPAGNON_API_URL": API_URL, "KOMPAGNON_API_KEY": API_KEY}), \
             patch("src.notifier.match_notifier.httpx.post", return_value=mock_response), \
             caplog.at_level(logging.ERROR, logger="src.notifier.match_notifier"):
            notify_match_result(found_journey_ids=[1])

        assert any("error" in record.message.lower() or "500" in record.message for record in caplog.records)

    def test_request_error_is_logged_not_raised(self, caplog):
        """A network error (timeout, connection refused) must be logged, not raised."""
        import logging

        with patch.dict("os.environ", {"KOMPAGNON_API_URL": API_URL, "KOMPAGNON_API_KEY": API_KEY}), \
             patch(
                 "src.notifier.match_notifier.httpx.post",
                 side_effect=httpx.RequestError("Connection refused", request=MagicMock()),
             ), \
             caplog.at_level(logging.ERROR, logger="src.notifier.match_notifier"):
            notify_match_result(found_journey_ids=[1])

        assert any("Connection refused" in record.message for record in caplog.records)

    def test_unexpected_exception_is_logged_not_raised(self, caplog):
        """Any unexpected exception must be caught, logged, and not re-raised."""
        import logging

        with patch.dict("os.environ", {"KOMPAGNON_API_URL": API_URL, "KOMPAGNON_API_KEY": API_KEY}), \
             patch(
                 "src.notifier.match_notifier.httpx.post",
                 side_effect=RuntimeError("Unexpected boom"),
             ), \
             caplog.at_level(logging.ERROR, logger="src.notifier.match_notifier"):
            notify_match_result(found_journey_ids=[1])

        assert any("Unexpected" in record.message for record in caplog.records)

    def test_payload_contains_only_found_journey_ids(self):
        """Callback payload must contain only found_journey_ids."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        captured_payload = {}

        def capture_post(url, json, headers, timeout):
            captured_payload.update(json)
            return mock_response

        with patch.dict("os.environ", {"KOMPAGNON_API_URL": API_URL, "KOMPAGNON_API_KEY": API_KEY}), \
             patch("src.notifier.match_notifier.httpx.post", side_effect=capture_post):
            notify_match_result(found_journey_ids=[10, 20, 30])

        assert captured_payload["data"] == [10, 20, 30]
        assert "journey_id" not in captured_payload
        assert "role" not in captured_payload

    def test_api_key_sent_in_header(self):
        """The API key must be sent as x-api-key header."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        captured_headers = {}

        def capture_post(url, json, headers, timeout):
            captured_headers.update(headers)
            return mock_response

        with patch.dict("os.environ", {"KOMPAGNON_API_URL": API_URL, "KOMPAGNON_API_KEY": API_KEY}), \
             patch("src.notifier.match_notifier.httpx.post", side_effect=capture_post):
            notify_match_result(found_journey_ids=[1])

        assert captured_headers.get("x-api-key") == API_KEY
