from fastapi.testclient import TestClient

from api.main_V42 import app


client = TestClient(app)


def test_health_endpoint():

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "smart-ebike-api"
    assert data["version"] == "V4.2"