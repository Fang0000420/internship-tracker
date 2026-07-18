from pathlib import Path
from uuid import uuid4

import pytest
from typer.testing import CliRunner

from internship_tracker.cli import app
from internship_tracker.models import ApplicationStatus, Internship
from internship_tracker.repository import InternshipRepository

runner = CliRunner()


@pytest.fixture
def data_file(tmp_path: Path) -> Path:
    return tmp_path / "internships.json"


def make_internship(
    *,
    company: str,
    title: str,
    country: str,
    url: str,
    status: ApplicationStatus = ApplicationStatus.SAVED,
) -> Internship:
    return Internship.model_validate(
        {
            "company": company,
            "title": title,
            "country": country,
            "url": url,
            "status": status,
        }
    )


def test_add_command_persists_internship(data_file: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--data-file",
            str(data_file),
            "add",
            "--company",
            "Mistral AI",
            "--title",
            "Agent Engineer",
            "--country",
            "France",
            "--url",
            "https://example.com/agent-engineer",
        ],
    )

    assert result.exit_code == 0

    saved = InternshipRepository(data_file).load_all()
    assert len(saved) == 1
    assert saved[0].company == "Mistral AI"


def test_add_command_translates_validation_error(data_file: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--data-file",
            str(data_file),
            "add",
            "--company",
            "Mistral AI",
            "--title",
            "Agent Engineer",
            "--country",
            "   ",
            "--url",
            "https://example.com/agent-engineer",
        ],
    )

    assert result.exit_code == 2
    assert "invalid internship data" in result.output.casefold()
    assert InternshipRepository(data_file).load_all() == []


def test_add_command_rejects_duplicate_url(data_file: Path) -> None:
    first_result = runner.invoke(
        app,
        [
            "--data-file",
            str(data_file),
            "add",
            "--company",
            "Mistral AI",
            "--title",
            "Agent Engineer",
            "--country",
            "France",
            "--url",
            "https://example.com/duplicate",
        ],
    )
    assert first_result.exit_code == 0

    duplicate_result = runner.invoke(
        app,
        [
            "--data-file",
            str(data_file),
            "add",
            "--company",
            "Another Company",
            "--title",
            "Another Position",
            "--country",
            "Germany",
            "--url",
            "https://example.com/duplicate",
        ],
    )

    assert duplicate_result.exit_code == 1
    assert "already exists" in duplicate_result.output.casefold()
    assert len(InternshipRepository(data_file).load_all()) == 1


def test_list_command_displays_saved_internship(data_file: Path) -> None:
    repository = InternshipRepository(data_file)
    internship = make_internship(
        company="Mistral AI",
        title="Agent Engineer",
        country="France",
        url="https://example.com/list",
    )
    repository.add(internship)

    result = runner.invoke(
        app,
        ["--data-file", str(data_file), "list"],
    )

    assert result.exit_code == 0
    assert str(internship.id) in result.output
    assert "Mistral AI" in result.output
    assert "Agent Engineer" in result.output
    assert ApplicationStatus.SAVED.value in result.output


def test_search_command_displays_matching_results(data_file: Path) -> None:
    repository = InternshipRepository(data_file)
    matching = make_internship(
        company="Mistral AI",
        title="Agent Engineer",
        country="France",
        url="https://example.com/matching",
    )
    unrelated = make_internship(
        company="Amazon",
        title="Cloud Developer",
        country="Ireland",
        url="https://example.com/unrelated",
    )
    repository.add(matching)
    repository.add(unrelated)

    result = runner.invoke(
        app,
        [
            "--data-file",
            str(data_file),
            "search",
            "--keyword",
            "AGENT",
        ],
    )

    assert result.exit_code == 0
    assert "Mistral AI" in result.output
    assert "Amazon" not in result.output


def test_search_command_reports_no_results(data_file: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--data-file",
            str(data_file),
            "search",
            "--keyword",
            "nonexistent",
        ],
    )

    assert result.exit_code == 0
    assert "no internships found" in result.output.casefold()


def test_update_status_command_persists_change(data_file: Path) -> None:
    repository = InternshipRepository(data_file)
    internship = Internship.model_validate(
        {
            "company": "Mistral AI",
            "title": "Agent Engineer",
            "country": "France",
            "url": "https://example.com/update",
        }
    )
    repository.add(internship)

    result = runner.invoke(
        app,
        [
            "--data-file",
            str(data_file),
            "update-status",
            str(internship.id),
            ApplicationStatus.APPLIED.value,
        ],
    )

    persisted = InternshipRepository(data_file).get_by_id(internship.id)

    assert result.exit_code == 0
    assert "updated" in result.output.casefold()
    assert str(internship.id) in result.output
    assert ApplicationStatus.APPLIED.value in result.output
    assert persisted.status is ApplicationStatus.APPLIED


@pytest.mark.parametrize(
    "arguments",
    [
        ["update-status", "not-a-uuid", ApplicationStatus.APPLIED.value],
        ["update-status", str(uuid4()), "invalid-status"],
        ["add", "--company", "Mistral AI"],
    ],
)
def test_invalid_cli_arguments_return_nonzero_exit_code(
    data_file: Path,
    arguments: list[str],
) -> None:
    result = runner.invoke(
        app,
        ["--data-file", str(data_file), *arguments],
    )

    assert result.exit_code == 2


def test_update_status_command_reports_unknown_id(
    data_file: Path,
) -> None:
    unknown_id = uuid4()

    result = runner.invoke(
        app,
        [
            "--data-file",
            str(data_file),
            "update-status",
            str(unknown_id),
            ApplicationStatus.APPLIED.value,
        ],
    )

    assert result.exit_code == 1
    assert "not found" in result.output.casefold()
    assert "traceback" not in result.output.casefold()


def test_corrupted_storage_returns_stable_error(data_file: Path) -> None:
    data_file.write_text("{invalid json", encoding="utf-8")

    result = runner.invoke(
        app,
        ["--data-file", str(data_file), "list"],
    )

    assert result.exit_code == 1
    assert "unable to access internship data" in result.output.casefold()
    assert "traceback" not in result.output.casefold()
