import pytest
from src.db.models import CompanionJourney

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
