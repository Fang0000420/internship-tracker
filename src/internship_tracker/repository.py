import json
import logging
from collections.abc import Sequence
from contextlib import suppress
from json import JSONDecodeError
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError

from internship_tracker.exceptions import (
    DuplicateInternshipError,
    InternshipNotFoundError,
    StorageError,
)
from internship_tracker.models import Internship

logger = logging.getLogger(__name__)


class InternshipRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load_all(self) -> list[Internship]:
        if not self._path.exists():
            logger.debug("Loaded %d internships", 0)
            return []

        try:
            raw_json = self._path.read_text(encoding="utf-8")
            payload: object = json.loads(raw_json)
        except (OSError, JSONDecodeError) as exc:
            raise StorageError(f"Cannot load internships from {self._path}") from exc

        if not isinstance(payload, list):
            raise StorageError(f"Expected a JSON array in {self._path}")

        internships: list[Internship] = []

        try:
            for item in payload:
                item = Internship.model_validate(item)
                internships.append(item)
        except ValidationError as exc:
            raise StorageError(f"Invalid internship data in {self._path}") from exc

        try:
            self._ensure_unique_ids(internships)
        except DuplicateInternshipError as exc:
            raise StorageError("Unable to load internship data.") from exc

        logger.debug("Loaded %d internships", len(internships))
        return internships

    def save_all(self, internships: Sequence[Internship]) -> None:
        items = list(internships)
        logger.debug("Saving %d internships", len(items))
        self._ensure_unique_ids(items)

        payload: list[dict[str, object]] = []

        for internship in items:
            payload.append(Internship.model_dump(internship, mode="json"))
        text = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )

        temporary_path = self._path.with_name(f".{self._path.name}.tmp")

        try:
            # 写入临时文件
            with temporary_path.open("w", encoding="utf-8") as f:
                f.write(text + "\n")
            # 临时文件写入成功，替换正式文件
            temporary_path.replace(self._path)
        except OSError as exc:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)
            raise StorageError(f"Cannot save internships to {self._path}") from exc

    @staticmethod
    def _ensure_unique_ids(
        internships: Sequence[Internship],
    ) -> None:
        seen: set[UUID] = set()

        for internship in internships:
            if internship.id in seen:
                raise DuplicateInternshipError(f"Duplicate internship ID: {internship.id}")

            seen.add(internship.id)

    def add(self, internship: Internship) -> Internship:
        internships = self.load_all()
        internships.append(internship)
        self._ensure_unique_ids(internships)

        self.save_all(internships)
        return internship

    def get_by_id(self, internship_id: UUID) -> Internship:
        internships = self.load_all()

        for internship in internships:
            if internship.id == internship_id:
                return internship

        raise InternshipNotFoundError(f"Internship not found: {internship_id}")

    def update(self, internship: Internship) -> Internship:
        internships = self.load_all()

        for index, existing in enumerate(internships):
            if existing.id == internship.id:
                internships[index] = internship
                self.save_all(internships)
                return internship
        raise InternshipNotFoundError(f"Internship not found: {internship.id}")
