# Internship Tracker

Internship Tracker is a typed, offline-first Python CLI for tracking European AI internship applications in a local JSON file.

## Why This Project

Internship searches quickly spread across bookmarks, notes, and spreadsheets. Internship Tracker keeps the essential information in one local, human-readable file and provides repeatable commands for answering questions such as:

- Which roles have I saved or already applied to?
- Which opportunities are in a particular country?
- What is the current status of each application?

The project is intentionally small and offline-first: it has no account, server, or external database to operate.

## Features

- Add an internship with a company, title, country, and validated HTTP(S) URL.
- Reject blank required fields and duplicate URLs.
- List all records by newest first or company name.
- Search company and title text with a case-insensitive keyword.
- Filter by exact country and application status; filters can be combined.
- Track the statuses `saved`, `applied`, `interview`, `offer`, and `rejected`.
- Select a custom JSON file with the global `--data-file` option.
- Enable diagnostic logs with the global `--verbose` option.
- Preserve Unicode text in the JSON data file.

## Architecture

The package separates command handling, business rules, validation, and persistence:

```text
CLI (Typer)
  -> InternshipService (search, sorting, duplicate-URL rule)
       -> InternshipRepository (JSON reads and atomic replacement writes)
            -> Internship model (Pydantic validation and serialization)
```

```text
src/internship_tracker/
├── cli.py          # Commands, options, output, exit codes, and logging setup
├── service.py      # Application workflows and sorting/filtering rules
├── repository.py   # JSON persistence and record lookup/update operations
├── models.py       # Internship schema and application status enum
└── exceptions.py   # Domain and storage exceptions
```

Tests mirror these layers in `tests/test_cli.py`, `tests/test_service.py`, `tests/test_repository.py`, and `tests/test_models.py`.

## Requirements

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/) for environment and dependency management

Runtime dependencies are Typer and Pydantic. Pytest, pytest-cov, Ruff, and mypy are installed through the development dependency group.

## Installation

Clone the repository, enter its directory, and synchronize the locked environment:

```console
git clone <repository-url>
cd internship-tracker
uv sync
```

`uv sync` creates or updates the local virtual environment from `pyproject.toml` and `uv.lock`.

## Quick Start

Commands use `internships.json` in the current directory unless `--data-file` is supplied.


```console
uv run internship-tracker add --company "Mistral AI" --title "Research Intern" --country "France" --url "https://example.com/jobs/research-intern"
```

The command prints the generated UUID:

```text
Added internship 123e4567-e89b-12d3-a456-426614174000.
```

Use the actual UUID printed by `add` when updating a record:

```console
uv run internship-tracker list
uv run internship-tracker update-status 123e4567-e89b-12d3-a456-426614174000 applied
uv run internship-tracker search --country France --status applied
```

PowerShell users can either enter each example on one line or replace the shell continuation character (`\`) with a backtick (`` ` ``).

## Commands and Examples

Global options must appear before the subcommand:

```console
uv run internship-tracker [--data-file PATH] [--verbose] COMMAND
```

### Add a record

All four options are required. New records start with the `saved` status.

```console
uv run internship-tracker add --company "Hugging Face" --title "ML Intern" --country "Germany" --url "https://example.com/jobs/ml-intern"
```

### List records

```console
# Newest first (default)
uv run internship-tracker list

# Case-insensitive company order
uv run internship-tracker list --sort company
```

Each result is printed as a pipe-delimited row:

```text
<uuid> | Mistral AI | Research Intern | France | applied
```

### Search and filter

`--keyword` searches the company and title. Country comparison ignores case and surrounding whitespace but otherwise requires an exact match.

```console
uv run internship-tracker search --keyword research
uv run internship-tracker search --country France --status saved
uv run internship-tracker search --keyword AI --country France --status applied --sort company
```

Running `search` without filters returns all records. A query with no matches prints `No internships found.`

### Update application status

```console
uv run internship-tracker update-status <uuid> interview
```

Valid statuses are `saved`, `applied`, `interview`, `offer`, and `rejected`.

### Use a different data file

```console
uv run internship-tracker --data-file data/europe.json list
uv run internship-tracker --data-file data/europe.json add --company "Example AI" --title "AI Intern" --country "Netherlands" --url "https://example.com/ai-intern"
```

The parent directory must already exist.

Run `uv run internship-tracker --help` or append `--help` to a subcommand for the complete generated CLI reference.

## Data Storage and Design Decisions

Data is stored as a UTF-8 JSON array. A record contains:

| Field | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Generated automatically |
| `company` | string | Required, trimmed, and non-blank |
| `title` | string | Required, trimmed, and non-blank |
| `country` | string | Required, trimmed, and non-blank |
| `url` | HTTP(S) URL | Required and unique through the service layer |
| `city` | string or null |Supported by the data model; not exposed by the CLI yet. |
| `tags` | string array | Supported by the data model; not exposed by the CLI yet. |
| `notes` | string or null | Supported by the data model; not exposed by the CLI yet. |
| `created_at` | timezone-aware datetime | Defaults to a timezone-aware UTC datetime. |
| `status` | enum | Defaults to `saved` |

Unknown fields are rejected when a record is loaded. IDs must be unique, and the top-level JSON value must be an array.

Writes are performed through a temporary file followed by replacement of the target file. If replacement fails, the previous file is retained and the temporary file is cleaned up. This reduces the chance of leaving a partially written data file.

The default relative path keeps separate working directories independent. Use `--data-file` when a stable or shared location is preferred.

## Error Handling and Verbose Diagnostics

The CLI converts expected failures into concise messages:

- Invalid internship input exits with code `2` and identifies the first invalid field.
- Duplicate URLs, unknown internship IDs, and storage failures exit with code `1`.
- Normal successful commands exit with code `0`.
- Malformed JSON, invalid stored records, and filesystem read/write failures are treated as storage errors.

Normal mode avoids tracebacks for handled storage failures. To capture internal debug logs and the exception chain for diagnosis, place `--verbose` before the command:

```console
uv run internship-tracker --verbose --data-file internships.json list
```

Diagnostics include record counts, UUIDs, filters, and status transitions. URLs and notes are deliberately not logged, which helps avoid leaking tokens in job links or private notes.

## Testing and Quality Checks

Run the full verification suite from the repository root:

```console
uv run pytest
uv run pytest --cov=internship_tracker --cov-branch --cov-report=term-missing
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run mypy tests
```

Coverage and test counts are reported by each run rather than treated as permanent project guarantees.
## Limitations

- The CLI can update only application status; it cannot edit other fields or delete a record.
- `city`, `tags`, and `notes` exist in the internal model but are not CLI options.
- There is no browser UI, remote synchronization, authentication, or database backend.
- Opportunities must be entered manually; the project does not scrape job boards.
- JSON writes have no cross-process locking, so concurrent writers can overwrite one another.
- Duplicate detection uses URL equality after Pydantic parsing; it does not resolve redirects or identify equivalent tracking URLs.
- Output is plain text rather than JSON, CSV, or a formatted table.
- Listing, searching, and duplicate checks scan the in-memory records in O(n) time.

## Roadmap

Potential next steps, subject to project needs:

- Expose `city`, `tags`, and `notes` in add/edit commands.
- Add general record editing and deletion with confirmation.
- Add JSON/CSV import and export plus machine-readable command output.
- Add richer search, including city and tag filters.
- Introduce locking or a database backend for safer concurrent use.
- Add packaging and release automation for installation outside the repository.
- Consider a FastAPI interface and PostgreSQL persistence after the CLI boundaries are stable.
- Explore Agent-assisted opportunity collection and application workflows as a later, separate capability.
