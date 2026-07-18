from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, field_validator

NonBlankString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class ApplicationStatus(StrEnum):
    """Application status enum"""

    SAVED = "saved"
    APPLIED = "applied"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"


def _utc_now() -> datetime:
    return datetime.now(UTC)


class Internship(BaseModel):
    """Internship model"""

    model_config = ConfigDict(extra="forbid")
    id: UUID = Field(default_factory=uuid4)
    city: str | None = None
    company: NonBlankString
    title: NonBlankString
    country: NonBlankString
    url: HttpUrl
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    created_at: datetime = Field(default_factory=_utc_now)
    status: ApplicationStatus = ApplicationStatus.SAVED

    @field_validator("created_at")
    @classmethod
    def ensure_created_at_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value.astimezone(UTC)
