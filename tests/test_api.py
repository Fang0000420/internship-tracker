from fastapi.testclient import TestClient

from internship_tracker.api.app import create_app


def test_health_endpoint_returns_expected_json() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    data = response.json()
    assert data == {"status": "ok"}


def test_openapi_contains_health_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "/health" in schema["paths"]
    assert "get" in schema["paths"]["/health"]
