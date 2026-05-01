import pytest
from src.db.models import CompanionJourney, PassengerJourney, FoundJourney

class TestRoot:
    def test_root_returns_200(self, client):
        """Root endpoint should return the welcome message."""
        response = client.get("/")
        assert response.status_code == 200
        assert "Kompagnon Matching Algorithm API" in response.json()["message"]

class TestStatus:
    def test_status_returns_200(self, client):
        """Status endpoint should return ok for both API and DB."""
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["db_status"] == "ok"

class TestGetValid:
    def test_get_valid_empty_returns_200_no_users(self, client):
        """When no journeys exist, return 200 with 'No users found' message."""
        response = client.get("/get-valid")
        assert response.status_code == 200
        assert response.json()["message"] == "No users found."
        assert response.json()["data"] == []

    def test_get_valid_with_data_returns_200(self, client, db_session, sample_companion_payload):
        """When journeys exist, return 200 with the list of journeys."""
        # Setup data
        journey = CompanionJourney(**sample_companion_payload)
        db_session.add(journey)
        db_session.commit()

        response = client.get("/get-valid")
        assert response.status_code == 200
        data = response.json()
        assert "Valid users journeys found successfully" in data["message"]
        assert len(data["data"]) == 1
        assert data["data"][0]["departureAddress"] == "Paris"

class TestGetInvalid:
    def test_get_invalid_empty_returns_200_no_users(self, client):
        """When no journeys exist, return 200 with 'No users found' message."""
        response = client.get("/get-invalid")
        assert response.status_code == 200
        assert response.json()["message"] == "No users found."
        assert response.json()["data"] == []

    def test_get_invalid_with_data_returns_200(self, client, db_session, sample_passenger_payload):
        """When journeys exist, return 200 with the list of journeys."""
        # Setup data
        journey = PassengerJourney(**sample_passenger_payload)
        db_session.add(journey)
        db_session.commit()

        response = client.get("/get-invalid")
        assert response.status_code == 200
        data = response.json()
        assert "Invalid users journeys found successfully" in data["message"]
        assert len(data["data"]) == 1
        assert data["data"][0]["departureAddress"] == "Paris"

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
        response = client.post(f"/put-journey?companion_id={c_id}&passenger_id={p_id}")
        assert response.status_code == 422

    def test_put_journey_missing_params_returns_422(self, client):
        """Missing required query parameters should return 422."""
        response = client.post("/put-journey")
        assert response.status_code == 422
