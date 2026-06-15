from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "MeshFlow API"


def test_api_health_returns_ok() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] in {"development", "test", "production"}


def test_database_health_returns_ok() -> None:
    response = client.get("/api/v1/health/db")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "metadata"
