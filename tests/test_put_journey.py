import pytest
from src.db.models import CompanionJourney, PassengerJourney

class TestPutJourney:
    def test_put_journey_success_returns_200(self, client, db_session, sample_companion_payload, sample_passenger_payload):
        """Creating a match with valid IDs should return 200."""
        # Need existing journeys to satisfy foreign keys if any (sqlite doesn't enforce by default but good practice)
        c_journey = CompanionJourney(**sample_companion_payload)
        p_journey = PassengerJourney(**sample_passenger_payload)
        db_session.add(c_journey)
        db_session.add(p_journey)
        db_session.commit()

        response = client.post(f"/put-journey?companion_id={c_journey.id}&passenger_id={p_journey.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Putting journey ..."
        assert "id" in data["data"]

    @pytest.mark.parametrize("c_id, p_id", [
        ("abc", 1),
        (1, "def"),
        ("", ""),
    ])
    def test_put_journey_invalid_params_returns_422(self, client, c_id, p_id):
        """Passing non-integer IDs should return 422 Unprocessable Entity."""
        # Note: In a real app, you might want to test the actual error message
        response = client.post(f"/put-journey?companion_id={c_id}&passenger_id={p_id}")
        assert response.status_code == 422

    def test_put_journey_missing_params_returns_422(self, client):
        """Missing required query parameters should return 422."""
        response = client.post("/put-journey")
        assert response.status_code == 422
