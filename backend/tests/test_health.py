from fastapi.testclient import TestClient

from main import app


def test_health_returns_ok_with_database_status():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "connected" in body["database"]
