from pathlib import Path

import pytest

from internship_tracker.repository import InternshipRepository


@pytest.fixture
def data_file(tmp_path: Path) -> Path:
    return tmp_path / "internships.json"


@pytest.fixture
def repository(data_file: Path) -> InternshipRepository:
    return InternshipRepository(data_file)
