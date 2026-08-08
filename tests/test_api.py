from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from internship_tracker.api.app import create_app
from internship_tracker.api.dependencies import get_internship_service
from internship_tracker.repository import InternshipRepository
from internship_tracker.service import InternshipService
from tests.factories import make_internship


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


@pytest.fixture
def api_client(repository: InternshipRepository) -> TestClient:
    application = create_app()
    application.dependency_overrides[get_internship_service] = lambda: InternshipService(repository)
    return TestClient(application)


def test_create_internship_returns_created_public_response(
    api_client: TestClient,
    repository: InternshipRepository,
) -> None:
    response = api_client.post(
        "/api/v1/internships",
        json={
            "company": "OpenAI",
            "title": "AI Engineer Intern",
            "country": "France",
            "url": "https://example.com/jobs/123",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {
        "id",
        "company",
        "title",
        "country",
        "url",
        "created_at",
        "status",
    }
    assert body["status"] == "saved"
    assert body["company"] == "OpenAI"
    assert body["title"] == "AI Engineer Intern"
    assert body["country"] == "France"
    assert body["url"] == "https://example.com/jobs/123"
    assert len(repository.load_all()) == 1


@pytest.mark.parametrize(
    "extra_field",
    [
        "id",
        "created_at",
        "status",
        "city",
        "tags",
        "notes",
    ],
)
def test_create_internship_rejects_non_public_fields(
    api_client: TestClient,
    repository: InternshipRepository,
    extra_field: str,
) -> None:
    payload = {
        "company": "OpenAI",
        "title": "AI Engineer Intern",
        "country": "France",
        "url": "https://example.com/jobs/123",
    }
    payload[extra_field] = "not-allowed"

    response = api_client.post(
        "/api/v1/internships",
        json=payload,
    )

    assert response.status_code == 422
    assert repository.load_all() == []


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("company", "   "),
        ("title", ""),
        ("country", " "),
        ("url", "not-a-url"),
    ],
)
def test_create_internship_rejects_invalid_values(
    api_client: TestClient,
    repository: InternshipRepository,
    field: str,
    invalid_value: str,
) -> None:
    payload = {
        "company": "OpenAI",
        "title": "AI Engineer Intern",
        "country": "France",
        "url": "https://example.com/jobs/123",
    }
    payload[field] = invalid_value

    response = api_client.post(
        "/api/v1/internships",
        json=payload,
    )

    assert response.status_code == 422
    assert repository.load_all() == []


def test_openapi_describes_create_internship_contract() -> None:
    client = TestClient(create_app())

    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    operation = schema["paths"]["/api/v1/internships"]["post"]

    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    created_response_schema = operation["responses"]["201"]["content"]["application/json"]["schema"]

    assert request_schema["$ref"] == "#/components/schemas/InternshipCreateRequest"
    assert created_response_schema["$ref"] == "#/components/schemas/InternshipResponse"


def test_list_internships_returns_empty_list(
    api_client: TestClient,
) -> None:
    response = api_client.get("/api/v1/internships")
    assert response.status_code == 200
    assert response.json() == []


def test_list_internships_returns_all_items_newest_first(
    api_client: TestClient,
    repository: InternshipRepository,
) -> None:
    older = make_internship(
        city="Paris",
        tags=["python", "fastapi"],
        notes="Internal note",
        company="Older Company",
        url="https://example.com/jobs/older",
        created_at=datetime(2026, 8, 1, 9, 0, tzinfo=UTC),
    )
    newer = make_internship(
        city="Paris",
        tags=["python", "fastapi"],
        notes="Internal note",
        company="Newer Company",
        url="https://example.com/jobs/newer",
        created_at=datetime(2026, 8, 2, 9, 0, tzinfo=UTC),
    )
    repository.add(older)
    repository.add(newer)

    response = api_client.get("/api/v1/internships")

    assert response.status_code == 200
    body = response.json()
    assert [item["company"] for item in body] == ["Newer Company", "Older Company"]
    public_fields = {
        "id",
        "company",
        "title",
        "country",
        "url",
        "created_at",
        "status",
    }
    private_fields = {
        "city",
        "tags",
        "notes",
    }
    assert all(set(item) == public_fields for item in body)
    assert all(private_fields.isdisjoint(item) for item in body)


def test_openapi_describes_list_internships_contract() -> None:
    client = TestClient(create_app())

    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()

    operation = schema["paths"]["/api/v1/internships"]["get"]

    list_response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]

    assert list_response_schema["type"] == "array"
    assert list_response_schema["items"]["$ref"] == "#/components/schemas/InternshipResponse"
