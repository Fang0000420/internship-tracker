from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from internship_tracker.exceptions import (
    DuplicateInternshipError,
    InternshipNotFoundError,
)
from internship_tracker.models import ApplicationStatus, Internship
from internship_tracker.repository import InternshipRepository
from internship_tracker.service import InternshipService, InternshipSortOrder

DEFAULT_CREATED_AT = datetime(2026, 7, 18, 8, 0, tzinfo=UTC)


def make_internship(
    *,
    company: str,
    title: str,
    country: str,
    url: str,
    status: ApplicationStatus = ApplicationStatus.SAVED,
    created_at: datetime = DEFAULT_CREATED_AT,
) -> Internship:
    return Internship(
        company=company,
        title=title,
        country=country,
        url=url,  # type: ignore
        status=status,
        created_at=created_at,
    )


@pytest.fixture
def repository(tmp_path: Path) -> InternshipRepository:
    return InternshipRepository(tmp_path / "internships.json")


@pytest.fixture
def service(repository: InternshipRepository) -> InternshipService:
    return InternshipService(repository)


def test_add_internship_persists_record(
    service: InternshipService,
    repository: InternshipRepository,
) -> None:
    result = service.add_internship(
        company="Amazon",
        title="Agent Developer",
        country="Ireland",
        url="https://www.amazon.jobs/agent-developer",
    )

    assert repository.load_all() == [result]


def test_add_internship_rejects_invalid_data_without_writing(
    service: InternshipService,
    repository: InternshipRepository,
) -> None:
    with pytest.raises(ValidationError):
        service.add_internship(
            company="Amazon",
            title="Agent Developer",
            country="   ",
            url="https://www.amazon.jobs/agent-developer",
        )

    assert repository.load_all() == []


def test_add_internship_rejects_duplicate_url_without_writing(
    service: InternshipService,
    repository: InternshipRepository,
) -> None:
    service.add_internship(
        company="Amazon",
        title="Agent Developer",
        country="Ireland",
        url="https://www.amazon.jobs/agent-developer",
    )

    with pytest.raises(
        DuplicateInternshipError,
        match="already exists",
    ):
        service.add_internship(
            company="Different Company",
            title="Different Position",
            country="France",
            url="https://www.amazon.jobs/agent-developer",
        )

    assert len(repository.load_all()) == 1


def test_list_internships_returns_all_newest_first(
    service: InternshipService,
    repository: InternshipRepository,
) -> None:
    older = make_internship(
        company="Amazon",
        title="Agent Developer",
        country="Ireland",
        url="https://example.com/older",
        created_at=datetime(2026, 7, 17, 8, 0, tzinfo=UTC),
    )
    newer = make_internship(
        company="Mistral AI",
        title="LLM Engineer",
        country="France",
        url="https://example.com/newer",
        created_at=datetime(2026, 7, 18, 8, 0, tzinfo=UTC),
    )
    repository.add(older)
    repository.add(newer)

    result = service.list_internships()

    assert [item.id for item in result] == [newer.id, older.id]


def test_list_internships_can_sort_by_company(
    service: InternshipService,
    repository: InternshipRepository,
) -> None:
    zeta = make_internship(
        company="zeta",
        title="Agent Developer",
        country="Ireland",
        url="https://example.com/older",
        created_at=datetime(2026, 7, 17, 8, 0, tzinfo=UTC),
    )
    amazon = make_internship(
        company="Amazon",
        title="Agent Developer",
        country="Ireland",
        url="https://example.com/older",
        created_at=datetime(2026, 7, 17, 8, 0, tzinfo=UTC),
    )
    mistral = make_internship(
        company="mistral AI",
        title="Agent Developer",
        country="Ireland",
        url="https://example.com/older",
        created_at=datetime(2026, 7, 17, 8, 0, tzinfo=UTC),
    )
    repository.save_all([zeta, amazon, mistral])
    result = service.list_internships(InternshipSortOrder.COMPANY)

    assert [item.id for item in result] == [amazon.id, mistral.id, zeta.id]


def test_search_internships_filters_by_country(
    service: InternshipService,
    repository: InternshipRepository,
) -> None:
    france = make_internship(
        company="Mistral AI",
        title="LLM Engineer",
        country="France",
        url="https://example.com/france",
    )
    ireland = make_internship(
        company="Amazon",
        title="Agent Developer",
        country="Ireland",
        url="https://example.com/ireland",
    )
    repository.add(france)
    repository.add(ireland)

    result = service.search_internships(country="  FRANCE  ")

    assert [item.id for item in result] == [france.id]


def test_update_status_persists_change(
    service: InternshipService,
    repository: InternshipRepository,
) -> None:
    internship = make_internship(
        company="Amazon",
        title="Agent Developer",
        country="Ireland",
        url="https://example.com/update",
    )
    repository.add(internship)

    updated = service.update_status(
        internship.id,
        ApplicationStatus.APPLIED,
    )
    persisted = repository.get_by_id(internship.id)

    assert updated.status is ApplicationStatus.APPLIED
    assert persisted == updated


def test_update_status_propagates_not_found(
    service: InternshipService,
) -> None:
    with pytest.raises(InternshipNotFoundError):
        service.update_status(
            uuid4(),
            ApplicationStatus.APPLIED,
        )


def test_search_internships_filters_by_status(
    service: InternshipService,
    repository: InternshipRepository,
) -> None:
    saved = make_internship(
        company="Amazon",
        title="Agent Developer",
        country="Ireland",
        url="https://example.com/saved",
        status=ApplicationStatus.SAVED,
    )
    applied = make_internship(
        company="Mistral AI",
        title="LLM Engineer",
        country="France",
        url="https://example.com/applied",
        status=ApplicationStatus.APPLIED,
    )
    repository.add(saved)
    repository.add(applied)

    result = service.search_internships(
        status=ApplicationStatus.APPLIED,
    )

    assert [item.id for item in result] == [applied.id]


def test_search_internships_matches_company_and_title(
    service: InternshipService,
    repository: InternshipRepository,
) -> None:
    company_match = make_internship(
        company="OpenAI",
        title="Research Intern",
        country="France",
        url="https://example.com/company-match",
    )
    title_match = make_internship(
        company="Example Labs",
        title="OpenAI Platform Engineer",
        country="Germany",
        url="https://example.com/title-match",
    )
    unrelated = make_internship(
        company="Amazon",
        title="Cloud Developer",
        country="Ireland",
        url="https://example.com/unrelated",
    )
    repository.add(company_match)
    repository.add(title_match)
    repository.add(unrelated)

    result = service.search_internships(keyword="oPeNaI")
    assert [item.id for item in result] == [title_match.id, company_match.id]


def test_search_internships_combines_filters(
    service: InternshipService,
    repository: InternshipRepository,
) -> None:
    matching = make_internship(
        company="Mistral AI",
        title="Agent Engineer",
        country="France",
        url="https://example.com/matching",
        status=ApplicationStatus.APPLIED,
    )
    wrong_country = make_internship(
        company="Example AI",
        title="Agent Engineer",
        country="Germany",
        url="https://example.com/wrong-country",
        status=ApplicationStatus.APPLIED,
    )
    wrong_status = make_internship(
        company="Another AI",
        title="Agent Engineer",
        country="France",
        url="https://example.com/wrong-status",
        status=ApplicationStatus.SAVED,
    )
    repository.add(matching)
    repository.add(wrong_country)
    repository.add(wrong_status)

    result = service.search_internships(
        keyword="agent",
        country="france",
        status=ApplicationStatus.APPLIED,
    )

    assert [item.id for item in result] == [matching.id]


def test_search_internships_treats_blank_keyword_as_no_filter(
    service: InternshipService,
    repository: InternshipRepository,
) -> None:
    first = make_internship(
        company="Amazon",
        title="Agent Developer",
        country="Ireland",
        url="https://example.com/first",
    )
    second = make_internship(
        company="Mistral AI",
        title="LLM Engineer",
        country="France",
        url="https://example.com/second",
    )
    repository.add(first)
    repository.add(second)

    result = service.search_internships(keyword="   ")

    assert [item.id for item in result] == [first.id, second.id]
