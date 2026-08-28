from fastapi.testclient import TestClient

from api.main_V42 import app


client = TestClient(app)


def test_health_endpoint():

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "ebike-sentinel-api"
    assert data["version"] == "V4.2"
    assert data["database"] == "connected"