# tests/factories.py
from datetime import UTC, datetime

from internship_tracker.models import Internship

_DEFAULT_CREATED_AT = datetime(2026, 7, 18, 10, 0, tzinfo=UTC)


def make_internship(**overrides: object) -> Internship:
    data: dict[str, object] = {
        "country": "France",
        "company": "Amazon",
        "title": "Agent Develop",
        "city": "Amazon",
        "url": "https://example.com/update",
        "created_at": _DEFAULT_CREATED_AT,
    }
    data.update(overrides)
    return Internship.model_validate(data)
