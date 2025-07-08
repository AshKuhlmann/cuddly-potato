import click
import os
import json
from rich.console import Console
from .database import (
    get_db_connection,
    create_table,
    add_entry,
    update_entry,
    export_to_json,
    DatabaseError,
)
from .gui import launch_gui

# --- Start of New Code ---
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


# --- End of New Code ---

# Create a console object for rich output
console = Console()


@click.group()
@click.option(
    "--db",
    default=None,  # Set default to None to handle memory logic
    help="The path to the SQLite database file. Remembers the last used path.",
)
@click.pass_context
def cli(ctx, db):
    """A CLI tool to manage question-answer pairs for LLMs."""
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
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        ctx.exit(1)


@cli.command()
@click.option("--question", prompt=True, help="The question being asked.")
@click.option("--model", prompt=True, help="The model providing the answer.")
@click.option("--answer", prompt=True, help="The answer from the model.")
@click.option("--domain", help="The domain of the question (e.g., Math).")
@click.option("--subdomain", help="The subdomain of the question (e.g., Basic Math).")
@click.option("--comments", help="Any comments or notes.")
@click.pass_context
def add(ctx, question, model, answer, domain, subdomain, comments):
    """Add a new question-answer entry."""
    conn = get_db_connection(ctx.obj["DB_PATH"])
    try:
        add_entry(conn, question, model, answer, domain, subdomain, comments)
        console.print("[bold green]✅ Entry added successfully![/bold green]")
    except DatabaseError as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
    finally:
        conn.close()


@cli.command()
@click.argument("entry_id", type=int)
@click.option("--question", help="The new question.")
@click.option("--model", help="The new model name.")
@click.option("--answer", help="The new answer.")
@click.option("--domain", help="The new domain.")
@click.option("--subdomain", help="The new subdomain.")
@click.option("--comments", help="The new comments.")
@click.pass_context
def update(ctx, entry_id, question, model, answer, domain, subdomain, comments):
    """Update an existing entry by its ID."""
    conn = get_db_connection(ctx.obj["DB_PATH"])
    try:
        update_entry(
            conn, entry_id, question, model, answer, domain, subdomain, comments
        )
        console.print(
            f"[bold green]✅ Entry {entry_id} updated successfully![/bold green]"
        )
    except DatabaseError as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
    finally:
        conn.close()


@cli.command()
@click.argument("output_path", type=click.Path())
@click.pass_context
def export(ctx, output_path):
    """Export the database to a JSON file."""
    conn = get_db_connection(ctx.obj["DB_PATH"])
    try:
        export_to_json(conn, output_path)
        console.print(f"[bold blue]📄 Data exported to {output_path}[/bold blue]")
    except DatabaseError as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
    finally:
        conn.close()


@cli.command()
def gui():
    """Launch the graphical user interface."""
    launch_gui()


if __name__ == "__main__":
    cli()
