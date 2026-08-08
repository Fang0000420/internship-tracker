from typing import Annotated

from fastapi import APIRouter, Depends, status

from internship_tracker.api.dependencies import get_internship_service
from internship_tracker.api.schemas.internships import (
    InternshipCreateRequest,
    InternshipResponse,
)
from internship_tracker.service import InternshipService

router = APIRouter(
    prefix="/api/v1/internships",
    tags=["internships"],
)


@router.post(
    "",
    response_model=InternshipResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_internship(
    request: InternshipCreateRequest,
    service: Annotated[
        InternshipService,
        Depends(get_internship_service),
    ],
) -> InternshipResponse:
    created = service.add_internship(
        company=request.company,
        title=request.title,
        country=request.country,
        url=str(request.url),
    )
    response = InternshipResponse.model_validate(created.model_dump())
    return response
