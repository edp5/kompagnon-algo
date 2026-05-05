import pytest

class TestRoot:
    def test_root_returns_200(self, client):
        """Root endpoint should return the welcome message."""
        response = client.get("/")
        assert response.status_code == 200
        assert "Kompagnon Matching Algorithm API" in response.json()["message"]
