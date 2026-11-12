"""Basic smoke tests."""

from fastapi.testclient import TestClient

from gateway.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root():
    response = client.get("/v1/")
    assert response.status_code == 200
    assert response.json()["service"] == "gateway"
