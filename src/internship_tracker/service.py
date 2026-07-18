from enum import StrEnum
from uuid import UUID

from internship_tracker.exceptions import DuplicateInternshipError
from internship_tracker.models import ApplicationStatus, Internship
from internship_tracker.repository import InternshipRepository


class InternshipSortOrder(StrEnum):
    NEWEST = "newest"
    COMPANY = "company"


def _sort_internships(
    internships: list[Internship],
    sort_order: InternshipSortOrder,
) -> list[Internship]:
    if sort_order is InternshipSortOrder.NEWEST:
        return sorted(
            internships,
            key=lambda item: (
                -item.created_at.timestamp(),
                item.company.casefold(),
                item.title.casefold(),
            ),
        )

    if sort_order is InternshipSortOrder.COMPANY:
        return sorted(
            internships,
            key=lambda item: (
                item.company.casefold(),
                item.title.casefold(),
                -item.created_at.timestamp(),
            ),
        )

    raise ValueError(f"Unsupported sort order: {sort_order}")


class InternshipService:
    def __init__(self, repository: InternshipRepository) -> None:
        self.repository = repository

    def add_internship(
        self,
        *,
        company: str,
        title: str,
        country: str,
        url: str,
        city: str | None = None,
        tags: list[str] | None = None,
        notes: str | None = None,
    ) -> Internship:
        candidate = Internship.model_validate(
            {
                "company": company,
                "title": title,
                "country": country,
                "url": url,
                "city": city,
                "tags": [] if tags is None else tags,
                "notes": notes,
            }
        )

        existing_internships = self.repository.load_all()

        duplicate_exists = any(existing.url == candidate.url for existing in existing_internships)

        if duplicate_exists:
            raise DuplicateInternshipError(f"Internship with URL {candidate.url} already exists")
        return self.repository.add(candidate)

    def list_internships(
        self,
        sort_order: InternshipSortOrder = InternshipSortOrder.NEWEST,
    ) -> list[Internship]:
        internships = self.repository.load_all()
        return _sort_internships(internships, sort_order)

    def search_internships(
        self,
        *,
        keyword: str | None = None,
        country: str | None = None,
        status: ApplicationStatus | None = None,
        sort_order: InternshipSortOrder = InternshipSortOrder.NEWEST,
    ) -> list[Internship]:
        normalized_keyword = keyword.strip().casefold() if keyword is not None else ""
        normalized_country = country.strip().casefold() if country is not None else ""

        matches: list[Internship] = []

        for internship in self.repository.load_all():
            if normalized_keyword:
                company_matches = normalized_keyword in internship.company.casefold()
                title_matches = normalized_keyword in internship.title.casefold()

                if not company_matches and not title_matches:
                    continue

            if normalized_country and internship.country.casefold() != normalized_country:
                continue

            if status is not None and internship.status != status:
                continue

            matches.append(internship)

        return _sort_internships(matches, sort_order)

    def update_status(
        self,
        internship_id: UUID,
        new_status: ApplicationStatus,
    ) -> Internship:
        current = self.repository.get_by_id(internship_id)

        updated = current.model_copy(update={"status": new_status})

        return self.repository.update(updated)
