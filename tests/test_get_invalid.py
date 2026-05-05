import pytest
from src.db.models import PassengerJourney

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
