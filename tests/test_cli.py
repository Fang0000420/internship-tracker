import json
import logging
from json import JSONDecodeError
from pathlib import Path
from uuid import uuid4

import pytest
from typer.testing import CliRunner, Result

from internship_tracker.cli import app
from internship_tracker.exceptions import StorageError
from internship_tracker.models import ApplicationStatus, Internship
from internship_tracker.repository import InternshipRepository
from tests.factories import make_internship

runner = CliRunner()


def invoke_cli(data_file: Path, *arguments: str) -> Result:
    return runner.invoke(
        app,
        ["--data-file", str(data_file), *arguments],
    )


def test_add_command_persists_internship(data_file: Path) -> None:
    result = invoke_cli(
        data_file,
        "add",
        "--company",
        "Mistral AI",
        "--title",
        "Agent Engineer",
        "--country",
        "France",
        "--url",
        "https://example.com/agent-engineer",
    )

    assert result.exit_code == 0
    result = invoke_cli(data_file)
    saved = InternshipRepository(data_file).load_all()
    assert len(saved) == 1
    assert saved[0].company == "Mistral AI"


def test_add_command_translates_validation_error(data_file: Path) -> None:
    result = invoke_cli(
        data_file,
        "add",
        "--company",
        "Mistral AI",
        "--title",
        "Agent Engineer",
        "--country",
        "   ",
        "--url",
        "https://example.com/agent-engineer",
    )
    assert result.exit_code == 2
    assert "invalid internship data" in result.output.casefold()
    assert InternshipRepository(data_file).load_all() == []


def test_add_command_rejects_duplicate_url(data_file: Path) -> None:
    first_result = invoke_cli(
        data_file,
        "add",
        "--company",
        "Mistral AI",
        "--title",
        "Agent Engineer",
        "--country",
        "France",
        "--url",
        "https://example.com/duplicate",
    )
    assert first_result.exit_code == 0

    duplicate_result = invoke_cli(
        data_file,
        "add",
        "--company",
        "Mistral AI",
        "--title",
        "Agent Engineer",
        "--country",
        "France",
        "--url",
        "https://example.com/duplicate",
    )

    assert duplicate_result.exit_code == 1
    assert "already exists" in duplicate_result.output.casefold()
    assert len(InternshipRepository(data_file).load_all()) == 1


def test_add_command_reports_storage_error_for_duplicate_ids_in_file(
    data_file: Path,
) -> None:
    first = make_internship(
        company="Mistral AI",
        url="https://example.com/existing-one",
    )
    second = make_internship(
        id=first.id,
        company="Hugging Face",
        url="https://example.com/existing-two",
    )
    payload = [
        first.model_dump(mode="json"),
        second.model_dump(mode="json"),
    ]
    data_file.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    result = invoke_cli(
        data_file,
        "add",
        "--company",
        "Example AI",
        "--title",
        "Research Intern",
        "--country",
        "Germany",
        "--url",
        "https://example.com/new-internship",
    )

    output = result.output.casefold()
    assert result.exit_code == 1
    assert "unable to access internship data" in output
    assert "already exists" not in output
    assert "traceback" not in output
    assert "duplicateinternshiperror" not in output


def test_list_command_displays_saved_internship(data_file: Path) -> None:
    repository = InternshipRepository(data_file)
    internship = make_internship(
        company="Mistral AI",
        title="Agent Engineer",
        country="France",
        url="https://example.com/list",
    )
    repository.add(internship)

    result = invoke_cli(data_file, "list")

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

    result = invoke_cli(
        data_file,
        "search",
        "--keyword",
        "AGENT",
    )

    assert result.exit_code == 0
    assert "Mistral AI" in result.output
    assert "Amazon" not in result.output


def test_search_command_reports_no_results(data_file: Path) -> None:
    result = invoke_cli(data_file, "search", "--keyword", "nonexistent")

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
    result = invoke_cli(
        data_file, "update-status", str(internship.id), ApplicationStatus.APPLIED.value
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
    result = invoke_cli(
        data_file, "update-status", str(unknown_id), ApplicationStatus.APPLIED.value
    )

    assert result.exit_code == 1
    assert "not found" in result.output.casefold()
    assert "traceback" not in result.output.casefold()


@pytest.mark.parametrize(
    "arguments",
    [
        ["list"],
        ["search"],
    ],
)
def test_corrupted_storage_returns_stable_error(
    data_file: Path,
    arguments: list[str],
) -> None:
    data_file.write_text("{invalid json", encoding="utf-8")

    result = invoke_cli(data_file, *arguments)

    assert result.exit_code == 1
    assert "unable to access internship data" in result.output.casefold()
    assert "traceback" not in result.output.casefold()


def test_default_mode_suppresses_debug_logs(
    data_file: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    result = invoke_cli(data_file, "list")

    assert result.exit_code == 0
    assert not any(
        record.levelno == logging.DEBUG and record.name.startswith("internship_tracker")
        for record in caplog.records
    )


def test_verbose_mode_emits_debug_diagnostics(
    data_file: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    result = invoke_cli(data_file, "--verbose", "list")

    assert result.exit_code == 0

    repo_debug_records = [
        rec
        for rec in caplog.records
        if rec.name == "internship_tracker.repository" and rec.levelno == logging.DEBUG
    ]
    assert repo_debug_records
    debug_record = repo_debug_records[0]

    log_msg = debug_record.getMessage()
    assert any(char.isdigit() for char in log_msg)
    assert "loaded" in log_msg.lower() or "load" in log_msg.lower()

    assert log_msg not in result.stdout


def test_verbose_storage_error_logs_exception_chain(
    data_file: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    data_file.write_text("{invalid json", encoding="utf-8")

    result = invoke_cli(data_file, "--verbose", "list")

    assert result.exit_code == 1
    assert "unable to access internship data" in result.output.casefold()

    error_records = [
        record
        for record in caplog.records
        if record.name == "internship_tracker.cli" and record.levelno == logging.ERROR
    ]

    assert len(error_records) == 1
    err_rec = error_records[0]

    assert "Storage operation failed" in err_rec.getMessage()

    assert err_rec.exc_info is not None

    exc_type, exc_val, _ = err_rec.exc_info
    assert exc_type == StorageError
    assert isinstance(exc_val, StorageError)

    assert isinstance(exc_val.__cause__, JSONDecodeError)
    assert err_rec.getMessage() not in result.stdout
    assert "JSONDecodeError" not in result.stdout
