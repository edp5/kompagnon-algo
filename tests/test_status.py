import pytest

class TestStatus:
    def test_status_returns_200(self, client):
        """Status endpoint should return ok for both API and DB."""
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["db_status"] == "ok"
