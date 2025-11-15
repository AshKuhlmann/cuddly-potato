import click
import json
import os
from rich.console import Console
from .database import (
    get_db_connection,
    create_table,
    add_entry,
    update_entry,
    export_to_json,
    export_to_excel,
    DatabaseError,
    ValidationError,
)
from .gui import launch_gui
from .logging_utils import StructuredLogger

# Define the path for the configuration file in the user's home directory
CONFIG_DIR = os.path.expanduser("~/.cuddly-potato")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def load_last_db_path():
    """Load the last used database path from the config file."""
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            return config.get("last_db_path")
    except (json.JSONDecodeError, IOError):
        return None


def save_last_db_path(db_path):
    """Save the given database path to the config file."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump({"last_db_path": db_path}, f)


# Create a console object for rich output
console = Console()

EXIT_SUCCESS = 0
EXIT_VALIDATION_ERROR = 2
EXIT_UNEXPECTED_ERROR = 3

LEVEL_TO_INT = {"debug": 10, "info": 20, "warning": 30, "error": 40}
VERBOSITY_THRESHOLDS = {"quiet": 30, "normal": 20, "verbose": 10}


def _command_name(ctx):
    command_path = ctx.command_path or ctx.info_name or ""
    return command_path.split(" ", 1)[-1] if " " in command_path else command_path


def _print_message(ctx, message, level="info"):
    verbosity = ctx.obj.get("verbosity", "normal") if ctx and ctx.obj else "normal"
    if LEVEL_TO_INT[level] >= VERBOSITY_THRESHOLDS.get(verbosity, 20):
        console.print(message)


def _log_command_start(ctx, **fields):
    logger = ctx.obj.get("logger")
    if logger:
        logger.command_start(_command_name(ctx), **fields)


def _log_command_success(ctx, message=None, **fields):
    logger = ctx.obj.get("logger")
    if logger:
        logger.command_result(
            _command_name(ctx),
            status="success",
            exit_code=0,
            message=message,
            **fields,
        )


def _log_command_failure(
    ctx, message=None, exit_code=EXIT_UNEXPECTED_ERROR, status="error", **fields
):
    logger = ctx.obj.get("logger")
    if logger:
        logger.command_result(
            _command_name(ctx),
            status=status,
            exit_code=exit_code,
            message=message,
            **fields,
        )


def _fail_and_exit(ctx, log_message, exit_code, status="error", **fields):
    _log_command_failure(ctx, log_message, exit_code=exit_code, status=status, **fields)
    ctx.exit(exit_code)


@click.group()
@click.option(
    "--db",
    default=None,
    help="The path to the SQLite database file. Remembers the last used path.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress informational output. Errors plus structured logs still emit.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Emit extra diagnostic logs and keep standard output chatty.",
)
@click.pass_context
def cli(ctx, db, quiet, verbose):
    """A CLI tool to manage data entries with author, tags, context, question, reason, and answer."""
    if quiet and verbose:
        raise click.BadParameter("Use either --quiet or --verbose, not both.")

    last_db_path = load_last_db_path()

    if db is None:
        db_path = last_db_path if last_db_path else "cuddly_potato.db"
    else:
        db_path = db
        save_last_db_path(db_path)

    if db is None and not last_db_path and not os.path.isabs(db_path):
        save_last_db_path(os.path.abspath(db_path))

    verbosity = "verbose" if verbose else "quiet" if quiet else "normal"
    logger = StructuredLogger(verbose=verbose)
    ctx.obj = {
        "DB_PATH": db_path,
        "verbosity": verbosity,
        "logger": logger,
    }
    try:
        conn = get_db_connection(db_path)
        create_table(conn)
        conn.close()
    except DatabaseError as e:
        _print_message(ctx, f"[bold red]Error: {e}[/bold red]", level="error")
        _fail_and_exit(
            ctx,
            f"Failed to initialize database: {e}",
            exit_code=EXIT_UNEXPECTED_ERROR,
            status="bootstrap_failed",
            db_path=db_path,
        )


@cli.command()
@click.option("--author", prompt=True, help="The author of the entry.")
@click.option("--tags", default="", help="Comma-separated tags for the entry.")
@click.option("--context", default="", help="Context for the question.")
@click.option("--question", prompt=True, help="The question being asked.")
@click.option("--reason", default="", help="The reason for asking the question.")
@click.option("--answer", prompt=True, help="The answer to the question.")
@click.pass_context
def add(ctx, author, tags, context, question, reason, answer):
    """Add a new entry."""
    _log_command_start(ctx, db_path=ctx.obj["DB_PATH"])
    conn = get_db_connection(ctx.obj["DB_PATH"])
    try:
        add_entry(conn, author, tags, context, question, reason, answer)
        _print_message(ctx, "[bold green]Entry added successfully![/bold green]")
        _log_command_success(ctx, "Entry added successfully.")
    except ValidationError as e:
        _print_message(ctx, f"[bold red]Error: {e}[/bold red]", level="error")
        _fail_and_exit(
            ctx,
            f"Validation failed: {e}",
            exit_code=EXIT_VALIDATION_ERROR,
            status="validation_error",
        )
    except DatabaseError as e:
        _print_message(ctx, f"[bold red]Error: {e}[/bold red]", level="error")
        _fail_and_exit(
            ctx,
            f"Database error while adding entry: {e}",
            exit_code=EXIT_UNEXPECTED_ERROR,
        )
    finally:
        conn.close()


@cli.command()
@click.argument("input_file", type=click.File("r"))
@click.pass_context
def import_json(ctx, input_file):
    """Import entries from a JSON file. Expected format: array of objects with author, tags, context, question, reason, answer fields."""
    _log_command_start(ctx, source=getattr(input_file, "name", "stdin"))
    try:
        data = json.load(input_file)
    except json.JSONDecodeError as e:
        _print_message(
            ctx,
            f"[bold red]Error: Invalid JSON format: {e}[/bold red]",
            level="error",
        )
        _fail_and_exit(
            ctx,
            f"Invalid JSON payload: {e}",
            exit_code=EXIT_VALIDATION_ERROR,
            status="invalid_json",
        )

    if not isinstance(data, list):
        _print_message(
            ctx,
            "[bold red]Error: JSON file must contain an array of entries.[/bold red]",
            level="error",
        )
        _fail_and_exit(
            ctx,
            "JSON import payload was not a list.",
            exit_code=EXIT_VALIDATION_ERROR,
            status="invalid_json",
        )

    conn = get_db_connection(ctx.obj["DB_PATH"])
    skipped_entries = []
    validation_failures = 0
    unexpected_failures = 0
    success_count = 0
    total_entries = len(data)

    try:
        for index, entry in enumerate(data, start=1):
            if not isinstance(entry, dict):
                skipped_entries.append(
                    (index, "validation", "Entry must be a JSON object.")
                )
                validation_failures += 1
                continue

            try:
                add_entry(
                    conn,
                    entry.get("author"),
                    entry.get("tags", ""),
                    entry.get("context", ""),
                    entry.get("question"),
                    entry.get("reason", ""),
                    entry.get("answer"),
                )
                success_count += 1
            except ValidationError as e:
                skipped_entries.append((index, "validation", str(e)))
                validation_failures += 1
            except DatabaseError as e:
                skipped_entries.append((index, "unexpected", str(e)))
                unexpected_failures += 1
            except Exception as e:  # pragma: no cover - defensive guard
                skipped_entries.append((index, "unexpected", f"Unexpected error: {e}"))
                unexpected_failures += 1

        if total_entries == 0:
            _print_message(
                ctx,
                "[bold yellow]Warning: No entries found in JSON file.[/bold yellow]",
                level="warning",
            )
            _log_command_success(
                ctx,
                "No entries to import.",
                imported=0,
                skipped=0,
            )
            return

        if success_count == total_entries:
            _print_message(
                ctx,
                f"[bold green]Imported {success_count} entries.[/bold green]",
            )
            _log_command_success(
                ctx,
                f"Imported {success_count} entries.",
                imported=success_count,
                skipped=0,
            )
            return

        failure_level = "error" if success_count == 0 else "warning"
        summary_message = (
            "[bold red]Failed to import any entries.[/bold red]"
            if success_count == 0
            else f"[bold yellow]Imported {success_count} of {total_entries} entries.[/bold yellow]"
        )
        _print_message(ctx, summary_message, level=failure_level)

        if skipped_entries:
            _print_message(ctx, "[bold yellow]Skipped entries:[/bold yellow]", level="warning")
            for entry_no, _kind, reason in skipped_entries:
                _print_message(ctx, f"[yellow]- Entry #{entry_no}: {reason}[/yellow]", level="warning")
        exit_code = (
            EXIT_UNEXPECTED_ERROR if unexpected_failures else EXIT_VALIDATION_ERROR
        )
        status = "partial_import" if success_count else "import_failed"
        _fail_and_exit(
            ctx,
            f"Imported {success_count} of {total_entries} entries.",
            exit_code=exit_code,
            status=status,
            imported=success_count,
            skipped=len(skipped_entries),
            validation_errors=validation_failures,
            unexpected_errors=unexpected_failures,
        )
    finally:
        conn.close()


@cli.command()
@click.argument("entry_id", type=int)
@click.option("--author", help="The new author.")
@click.option("--tags", help="The new tags (comma-separated).")
@click.option("--context", help="The new context.")
@click.option("--question", help="The new question.")
@click.option("--reason", help="The new reason.")
@click.option("--answer", help="The new answer.")
@click.pass_context
def update(ctx, entry_id, author, tags, context, question, reason, answer):
    """Update an existing entry by its ID."""
    _log_command_start(ctx, entry_id=entry_id)
    conn = get_db_connection(ctx.obj["DB_PATH"])
    try:
        update_entry(conn, entry_id, author, tags, context, question, reason, answer)
        _print_message(
            ctx,
            f"[bold green]Entry {entry_id} updated successfully![/bold green]",
        )
        _log_command_success(ctx, f"Entry {entry_id} updated.", entry_id=entry_id)
    except ValidationError as e:
        _print_message(ctx, f"[bold red]Error: {e}[/bold red]", level="error")
        _fail_and_exit(
            ctx,
            f"Validation failed for entry {entry_id}: {e}",
            exit_code=EXIT_VALIDATION_ERROR,
            status="validation_error",
            entry_id=entry_id,
        )
    except DatabaseError as e:
        _print_message(ctx, f"[bold red]Error: {e}[/bold red]", level="error")
        _fail_and_exit(
            ctx,
            f"Failed to update entry {entry_id}: {e}",
            exit_code=EXIT_UNEXPECTED_ERROR,
            entry_id=entry_id,
        )
    finally:
        conn.close()


@cli.command()
@click.argument("output_path", type=click.Path())
@click.pass_context
def export_json(ctx, output_path):
    """Export the database to a JSON file."""
    _log_command_start(ctx, output_path=output_path)
    conn = get_db_connection(ctx.obj["DB_PATH"])
    try:
        export_to_json(conn, output_path)
        _print_message(
            ctx,
            f"[bold blue]Data exported to {output_path}[/bold blue]",
        )
        _log_command_success(
            ctx,
            f"Data exported to {output_path}",
            output_path=output_path,
        )
    except DatabaseError as e:
        _print_message(ctx, f"[bold red]Error: {e}[/bold red]", level="error")
        _fail_and_exit(
            ctx,
            f"Failed to export JSON to {output_path}: {e}",
            exit_code=EXIT_UNEXPECTED_ERROR,
            output_path=output_path,
        )
    finally:
        conn.close()


@cli.command()
@click.argument("output_path", type=click.Path())
@click.pass_context
def export_excel(ctx, output_path):
    """Export the database to an Excel file."""
    _log_command_start(ctx, output_path=output_path)
    conn = get_db_connection(ctx.obj["DB_PATH"])
    try:
        export_to_excel(conn, output_path)
        _print_message(
            ctx,
            f"[bold blue]Data exported to {output_path}[/bold blue]",
        )
        _log_command_success(
            ctx,
            f"Data exported to {output_path}",
            output_path=output_path,
        )
    except DatabaseError as e:
        _print_message(ctx, f"[bold red]Error: {e}[/bold red]", level="error")
        _fail_and_exit(
            ctx,
            f"Failed to export Excel to {output_path}: {e}",
            exit_code=EXIT_UNEXPECTED_ERROR,
            output_path=output_path,
        )
    finally:
        conn.close()


@cli.command()
@click.pass_context
def gui(ctx):
    """Launch the graphical user interface."""
    _log_command_start(ctx)
    try:
        launch_gui()
        _log_command_success(ctx, "GUI launched.")
    except Exception as e:  # pragma: no cover - GUI errors aren't covered by CLI tests
        _print_message(ctx, f"[bold red]Error launching GUI: {e}[/bold red]", level="error")
        _fail_and_exit(
            ctx,
            f"GUI launch failed: {e}",
            exit_code=EXIT_UNEXPECTED_ERROR,
        )


if __name__ == "__main__":
    cli()
