import click
import os
import json
import sys
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


@click.group()
@click.option(
    "--db",
    default=None,
    help="The path to the SQLite database file. Remembers the last used path.",
)
@click.pass_context
def cli(ctx, db):
    """A CLI tool to manage data entries with author, tags, context, question, reason, and answer."""
    last_db_path = load_last_db_path()

    if db is None:
        db_path = last_db_path if last_db_path else "cuddly_potato.db"
    else:
        db_path = db
        save_last_db_path(db_path)

    if db is None and not last_db_path and not os.path.isabs(db_path):
        save_last_db_path(os.path.abspath(db_path))

    ctx.obj = {"DB_PATH": db_path}
    try:
        conn = get_db_connection(db_path)
        create_table(conn)
        conn.close()
    except DatabaseError as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        ctx.exit(1)


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
    conn = get_db_connection(ctx.obj["DB_PATH"])
    try:
        add_entry(conn, author, tags, context, question, reason, answer)
        console.print("[bold green]Entry added successfully![/bold green]")
    except ValidationError as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        ctx.exit(1)
    except DatabaseError as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        ctx.exit(1)
    finally:
        conn.close()


@cli.command()
@click.argument("input_file", type=click.File("r"))
@click.pass_context
def import_json(ctx, input_file):
    """Import entries from a JSON file. Expected format: array of objects with author, tags, context, question, reason, answer fields."""
    try:
        data = json.load(input_file)
    except json.JSONDecodeError as e:
        console.print(f"[bold red]Error: Invalid JSON format: {e}[/bold red]")
        ctx.exit(1)

    if not isinstance(data, list):
        console.print("[bold red]Error: JSON file must contain an array of entries.[/bold red]")
        ctx.exit(1)

    conn = get_db_connection(ctx.obj["DB_PATH"])
    skipped_entries = []
    success_count = 0
    total_entries = len(data)

    try:
        for index, entry in enumerate(data, start=1):
            if not isinstance(entry, dict):
                skipped_entries.append((index, "Entry must be a JSON object."))
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
                skipped_entries.append((index, str(e)))
            except DatabaseError as e:
                skipped_entries.append((index, str(e)))
            except Exception as e:  # pragma: no cover - defensive guard
                skipped_entries.append((index, f"Unexpected error: {e}"))

        if total_entries == 0:
            console.print("[bold yellow]Warning: No entries found in JSON file.[/bold yellow]")
            return

        if success_count == total_entries:
            console.print(f"[bold green]Imported {success_count} entries.[/bold green]")
            return

        if success_count == 0:
            console.print("[bold red]Failed to import any entries.[/bold red]")
        else:
            console.print(f"[bold yellow]Imported {success_count} of {total_entries} entries.[/bold yellow]")

        if skipped_entries:
            console.print("[bold yellow]Skipped entries:[/bold yellow]")
            for entry_no, reason in skipped_entries:
                console.print(f"[yellow]- Entry #{entry_no}: {reason}[/yellow]")
        ctx.exit(1)
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
    conn = get_db_connection(ctx.obj["DB_PATH"])
    try:
        update_entry(conn, entry_id, author, tags, context, question, reason, answer)
        console.print(f"[bold green]Entry {entry_id} updated successfully![/bold green]")
    except DatabaseError as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        ctx.exit(1)
    finally:
        conn.close()


@cli.command()
@click.argument("output_path", type=click.Path())
@click.pass_context
def export_json(ctx, output_path):
    """Export the database to a JSON file."""
    conn = get_db_connection(ctx.obj["DB_PATH"])
    try:
        export_to_json(conn, output_path)
        console.print(f"[bold blue]Data exported to {output_path}[/bold blue]")
    except DatabaseError as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        ctx.exit(1)
    finally:
        conn.close()


@cli.command()
@click.argument("output_path", type=click.Path())
@click.pass_context
def export_excel(ctx, output_path):
    """Export the database to an Excel file."""
    conn = get_db_connection(ctx.obj["DB_PATH"])
    try:
        export_to_excel(conn, output_path)
        console.print(f"[bold blue]Data exported to {output_path}[/bold blue]")
    except DatabaseError as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        ctx.exit(1)
    finally:
        conn.close()


@cli.command()
def gui():
    """Launch the graphical user interface."""
    launch_gui()


if __name__ == "__main__":
    cli()
