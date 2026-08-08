from pathlib import Path

from internship_tracker.repository import InternshipRepository
from internship_tracker.service import InternshipService


def get_internship_service() -> InternshipService:
    data_path = Path("internships.json")
    repository = InternshipRepository(data_path)
    return InternshipService(repository)
