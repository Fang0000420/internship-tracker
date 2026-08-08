from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, HttpUrl, StringConstraints

from internship_tracker.models import ApplicationStatus

ApiNonBlankString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class InternshipCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: ApiNonBlankString
    title: ApiNonBlankString
    country: ApiNonBlankString
    url: HttpUrl


class InternshipResponse(BaseModel):
    id: UUID
    company: ApiNonBlankString
    title: ApiNonBlankString
    country: ApiNonBlankString
    url: HttpUrl
    created_at: datetime
    status: ApplicationStatus
