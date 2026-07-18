from pathlib import Path
from typing import Annotated, Never
from uuid import UUID

import typer
from pydantic import ValidationError

from internship_tracker.exceptions import (
    DuplicateInternshipError,
    InternshipNotFoundError,
    StorageError,
)
from internship_tracker.models import ApplicationStatus, Internship
from internship_tracker.repository import InternshipRepository
from internship_tracker.service import InternshipService, InternshipSortOrder

DEFAULT_DATA_FILE = Path("internships.json")

app = typer.Typer(
    help="Manage internship applications.",
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode=None,
    pretty_exceptions_enable=False,
)


def _get_service(ctx: typer.Context) -> InternshipService:
    service = ctx.obj

    if not isinstance(service, InternshipService):
        raise RuntimeError("InternshipService was not configured")

    return service


def _format_internship(internship: Internship) -> str:
    return (
        f"{internship.id} | "
        f"{internship.company} | "
        f"{internship.title} | "
        f"{internship.country} | "
        f"{internship.status.value}"
    )


def _print_internships(internships: list[Internship]) -> None:
    if not internships:
        typer.echo("No internships found.")
        return

    for internship in internships:
        typer.echo(_format_internship(internship))


def _abort_with_error(
    error: (ValidationError | DuplicateInternshipError | InternshipNotFoundError | StorageError),
) -> Never:
    if isinstance(error, DuplicateInternshipError):
        typer.echo(
            "Error: internship with this URL already exists.",
            err=True,
        )
        raise typer.Exit(code=1) from error

    if isinstance(error, InternshipNotFoundError):
        typer.echo("Error: internship not found.", err=True)
        raise typer.Exit(code=1) from error

    if isinstance(error, StorageError):
        typer.echo(
            "Error: unable to access internship data.",
            err=True,
        )
        raise typer.Exit(code=1) from error

    first_error = error.errors()[0]
    field = ".".join(str(part) for part in first_error["loc"])
    message = first_error["msg"]

    typer.echo(
        f"Error: invalid internship data: {field}: {message}",
        err=True,
    )
    raise typer.Exit(code=2) from error


def build_service(data_path: Path) -> InternshipService:
    repository = InternshipRepository(data_path)
    return InternshipService(repository)


@app.callback()
def configure(
    ctx: typer.Context,
    data_file: Annotated[
        Path,
        typer.Option("--data-file", help="Path to the JSON data file."),
    ] = DEFAULT_DATA_FILE,
) -> None:
    ctx.obj = build_service(data_file)


@app.command("add")
def add_command(
    ctx: typer.Context,
    company: Annotated[str, typer.Option("--company")],
    title: Annotated[str, typer.Option("--title")],
    country: Annotated[str, typer.Option("--country")],
    url: Annotated[str, typer.Option("--url")],
) -> None:
    service = _get_service(ctx)

    try:
        internship = service.add_internship(
            company=company,
            title=title,
            country=country,
            url=url,
        )
    except (
        ValidationError,
        DuplicateInternshipError,
        StorageError,
    ) as error:
        _abort_with_error(error)

    typer.echo(f"Added internship {internship.id}.")


@app.command("list")
def list_command(
    ctx: typer.Context,
    sort_order: Annotated[
        InternshipSortOrder,
        typer.Option("--sort"),
    ] = InternshipSortOrder.NEWEST,
) -> None:
    service = _get_service(ctx)

    try:
        internships = service.list_internships(sort_order)
    except StorageError as error:
        _abort_with_error(error)
    _print_internships(internships)


@app.command("search")
def search_command(
    ctx: typer.Context,
    keyword: Annotated[str | None, typer.Option("--keyword")] = None,
    country: Annotated[str | None, typer.Option("--country")] = None,
    status: Annotated[
        ApplicationStatus | None,
        typer.Option("--status"),
    ] = None,
    sort_order: Annotated[
        InternshipSortOrder,
        typer.Option("--sort"),
    ] = InternshipSortOrder.NEWEST,
) -> None:
    service = _get_service(ctx)

    try:
        internships = service.search_internships(
            keyword=keyword, country=country, status=status, sort_order=sort_order
        )
    except StorageError as error:
        _abort_with_error(error)
    _print_internships(internships)


@app.command("update-status")
def update_status_command(
    ctx: typer.Context,
    internship_id: Annotated[UUID, typer.Argument()],
    new_status: Annotated[ApplicationStatus, typer.Argument()],
) -> None:
    service = _get_service(ctx)

    try:
        updated = service.update_status(internship_id=internship_id, new_status=new_status)
    except (InternshipNotFoundError, StorageError) as error:
        _abort_with_error(error)

    typer.echo(f"Updated internship {updated.id} status to {updated.status.value}.")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
