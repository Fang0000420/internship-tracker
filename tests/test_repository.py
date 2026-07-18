import json
from datetime import UTC, datetime
from json import JSONDecodeError
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from internship_tracker.exceptions import (
    DuplicateInternshipError,
    InternshipNotFoundError,
    StorageError,
)
from internship_tracker.models import ApplicationStatus, Internship
from internship_tracker.repository import InternshipRepository


def make_internship(**overrides: object) -> Internship:
    data: dict[str, object] = {
        "company": "Mistral AI",
        "title": "AI Engineer Intern",
        "country": "France",
        "city": "Paris",
        "url": "https://example.com/jobs/agent-engineer",
        "created_at": datetime(2026, 7, 18, 10, 0, tzinfo=UTC),
    }

    data.update(overrides)
    return Internship.model_validate(data)


def test_load_all_returns_empty_list_when_file_does_not_exist(
    tmp_path: Path,
) -> None:
    repository = InternshipRepository(tmp_path / "internships.json")
    assert repository.load_all() == []


def test_save_and_load_one_internship(tmp_path: Path) -> None:
    repository = InternshipRepository(tmp_path / "internships.json")
    internship = make_internship()

    repository.save_all([internship])
    assert repository.load_all() == [internship]


def test_save_and_load_multiple_internships(tmp_path: Path) -> None:
    repository = InternshipRepository(tmp_path / "internships.json")
    internships = [
        make_internship(company="Mistral AI"),
        make_internship(company="Hugging Face"),
    ]

    repository.save_all(internships)

    assert repository.load_all() == internships


def test_save_and_load_preserves_unicode(tmp_path: Path) -> None:
    data_file = tmp_path / "internships.json"
    repository = InternshipRepository(data_file)
    internship = make_internship(
        company="海洋智能科技",
        title="Ingénieur IA",
        notes="你好，candidature française",
    )

    repository.save_all([internship])

    raw_json = data_file.read_text(encoding="utf-8")
    assert "海洋智能科技" in raw_json
    assert "Ingénieur IA" in raw_json
    assert "你好" in raw_json
    assert repository.load_all() == [internship]


def test_add_persists_internship(tmp_path: Path) -> None:
    repository = InternshipRepository(tmp_path / "internships.json")
    internship = make_internship()

    result = repository.add(internship)
    assert result == internship
    assert repository.load_all() == [internship]


def test_get_by_id_returns_matching_internship(tmp_path: Path) -> None:
    repository = InternshipRepository(tmp_path / "internships.json")
    first = make_internship(company="Mistral AI")
    second = make_internship(company="Hugging Face")
    repository.save_all([first, second])

    assert repository.get_by_id(second.id) == second


def test_get_by_id_raises_when_id_is_unknown(tmp_path: Path) -> None:
    repository = InternshipRepository(tmp_path / "internships.json")
    unknown_id = uuid4()

    with pytest.raises(InternshipNotFoundError):
        repository.get_by_id(unknown_id)


def test_update_persists_existing_internship(tmp_path: Path) -> None:
    repository = InternshipRepository(tmp_path / "internships.json")
    original = make_internship()
    repository.save_all([original])

    updated = original.model_copy(
        update={
            "status": ApplicationStatus.APPLIED,
            "notes": "Application submitted",
        }
    )

    result = repository.update(updated)
    assert result == updated
    assert repository.load_all() == [updated]


def test_update_raises_when_id_is_unknown(tmp_path: Path) -> None:
    repository = InternshipRepository(tmp_path / "internships.json")
    unknown = make_internship()

    with pytest.raises(InternshipNotFoundError):
        repository.update(unknown)


def test_load_all_wraps_malformed_json_error(tmp_path: Path) -> None:
    data_file = tmp_path / "internships.json"
    data_file.write_text('{"broken": ', encoding="utf-8")
    repository = InternshipRepository(data_file)

    with pytest.raises(StorageError) as exc_info:
        repository.load_all()

    assert isinstance(exc_info.value.__cause__, JSONDecodeError)


def test_load_all_wraps_validation_error(tmp_path: Path) -> None:
    data_file = tmp_path / "internships.json"
    data_file.write_text(
        '[{"company": "Mistral AI"}]',
        encoding="utf-8",
    )
    repository = InternshipRepository(data_file)

    with pytest.raises(StorageError) as exc_info:
        repository.load_all()

    assert isinstance(exc_info.value.__cause__, ValidationError)


def test_add_rejects_duplicate_id(tmp_path: Path) -> None:
    repository = InternshipRepository(tmp_path / "internships.json")
    original = make_internship(company="Mistral AI")
    duplicate = make_internship(
        id=original.id,
        company="Another company",
    )
    repository.save_all([original])

    with pytest.raises(DuplicateInternshipError):
        repository.add(duplicate)

    assert repository.load_all() == [original]


def test_save_all_rejects_duplicate_ids(tmp_path: Path) -> None:
    repository = InternshipRepository(tmp_path / "internships.json")
    data_file = tmp_path / "internships.json"
    first = make_internship(company="Mistral AI")
    second = make_internship(
        id=first.id,
        company="Hugging Face",
    )

    with pytest.raises(DuplicateInternshipError):
        repository.save_all([first, second])

    assert not data_file.exists()


def test_load_all_rejects_duplicate_ids_in_file(tmp_path: Path) -> None:
    data_file = tmp_path / "internships.json"
    first = make_internship(company="Mistral AI")
    second = make_internship(
        id=first.id,
        company="Hugging Face",
    )
    payload = [
        first.model_dump(mode="json"),
        second.model_dump(mode="json"),
    ]
    data_file.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    repository = InternshipRepository(data_file)

    with pytest.raises(DuplicateInternshipError):
        repository.load_all()


def test_save_all_preserves_existing_file_when_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_file = tmp_path / "internships.json"
    repository = InternshipRepository(data_file)
    original = make_internship(company="Mistral AI")
    replacement = make_internship(company="Hugging Face")
    repository.save_all([original])

    def fail_replace(self: Path, target: Path) -> Path:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(StorageError) as exc_info:
        repository.save_all([replacement])

    assert isinstance(exc_info.value.__cause__, OSError)
    assert repository.load_all() == [original]
    assert list(tmp_path.glob("*.tmp")) == []
