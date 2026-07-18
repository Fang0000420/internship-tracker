class StorageError(Exception):
    """Raised when internship data cannot be read or written safely."""


class InternshipNotFoundError(Exception):
    """Raised when an internship ID does not exist."""


class DuplicateInternshipError(Exception):
    """Raised when multiple internships use the same ID."""
