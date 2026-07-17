from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import HttpUrl, ValidationError

from internship_tracker.models import ApplicationStatus, Internship

CAREERS_URL = HttpUrl("https://www.amazon.com/careers")


def test_create_minimal_internship() -> None:
    internship = Internship(
        company="Amazon",
        title="Agent Development",
        country="Netherlands",
        url=CAREERS_URL,
    )

    assert internship.company == "Amazon"
    assert internship.title == "Agent Development"
    assert internship.country == "Netherlands"
    assert internship.status == ApplicationStatus.SAVED


def test_create_internship_with_all_fields() -> None:
    internship_id = UUID("12345678-1234-5678-1234-567812345678")
    created_at = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)

    internship = Internship(
        id=internship_id,
        company="Amazon",
        title="Agent Development",
        country="Netherlands",
        url=CAREERS_URL,
        status=ApplicationStatus.APPLIED,
        city="Amsterdam",
        tags=["ai", "develop"],
        notes="AI agent development internship",
        created_at=created_at,
    )

    assert internship.id == internship_id
    assert internship.city == "Amsterdam"
    assert internship.tags == ["ai", "develop"]
    assert internship.notes == "AI agent development internship"
    assert internship.created_at == created_at


def test_rejects_blank_company() -> None:
    with pytest.raises(ValidationError):
        internship_id = UUID("12345678-1234-5678-1234-567812345678")
        created_at = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)

        Internship(
            id=internship_id,
            company="    ",
            title="Agent Development",
            country="Netherlands",
            url=CAREERS_URL,
            status=ApplicationStatus.APPLIED,
            city="Amsterdam",
            tags=["ai", "develop"],
            notes="AI agent development internship",
            created_at=created_at,
        )


def test_rejects_blank_title() -> None:
    with pytest.raises(ValidationError):
        internship_id = UUID("12345678-1234-5678-1234-567812345678")
        created_at = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)

        Internship(
            id=internship_id,
            company="Amazon",
            title="    ",
            country="Netherlands",
            url=CAREERS_URL,
            status=ApplicationStatus.APPLIED,
            city="Amsterdam",
            tags=["ai", "develop"],
            notes="AI agent development internship",
            created_at=created_at,
        )


def test_rejects_invalid_url() -> None:
    with pytest.raises(ValidationError):
        Internship.model_validate(
            {
                "company": "Amazon",
                "title": "Agent Development",
                "country": "Netherlands",
                "url": "not-a-url",
            }
        )


def test_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        Internship.model_validate(
            {
                "company": "Amazon",
                "title": "Agent Development",
                "country": "Netherlands",
                "status": "withdrawn",
            }
        )


def test_tags_are_not_shared_between_instances() -> None:

    first = Internship(
        company="Amazon",
        title="Agent Development",
        country="Netherlands",
        url=CAREERS_URL,
    )

    second = Internship(
        company="Amazon",
        title="Agent Development",
        country="Netherlands",
        url=CAREERS_URL,
    )
    first.tags.append("ai")

    assert first.tags == ["ai"]
    assert second.tags == []
    assert first.tags is not second.tags


def test_created_at_defaults_to_utc() -> None:
    internship = Internship(
        company="Amazon",
        title="Agent Development",
        country="Netherlands",
        url=CAREERS_URL,
    )

    assert internship.created_at.tzinfo is not None
    assert internship.created_at.utcoffset() == timedelta(0)


def test_default_ids_are_unique() -> None:
    first = Internship(
        company="Amazon",
        title="Agent Development",
        country="Netherlands",
        url=CAREERS_URL,
    )
    second = Internship(
        company="Amazon",
        title="Agent Development",
        country="Netherlands",
        url=CAREERS_URL,
    )

    assert isinstance(first.id, UUID)
    assert isinstance(second.id, UUID)
    assert first.id != second.id


def test_rejects_naive_created_at() -> None:
    with pytest.raises(ValidationError):
        Internship(
            company="Amazon",
            title="Agent Development",
            country="Netherlands",
            url=CAREERS_URL,
            created_at=datetime(2026, 7, 18, 12, 0),
        )


def test_json_round_trip_preserves_types() -> None:
    original = Internship(
        company="Amazon",
        title="Agent Development",
        country="Netherlands",
        url=CAREERS_URL,
    )

    python_data = original.model_dump()
    json_data = original.model_dump(mode="json")
    json_text = original.model_dump_json()
    restored = Internship.model_validate_json(json_text)

    assert isinstance(python_data["id"], UUID)
    assert isinstance(json_data["id"], str)
    assert isinstance(json_text, str)
    assert restored == original
    assert isinstance(restored.id, UUID)
    assert isinstance(restored.url, HttpUrl)
    assert restored.status is ApplicationStatus.SAVED
    assert restored.created_at == original.created_at


def test_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Internship.model_validate(
            {
                "company": "Amazon",
                "title": "Agent Development",
                "country": "Netherlands",
                "create_at": "2026-07-18T12:00:00Z",
            }
        )
