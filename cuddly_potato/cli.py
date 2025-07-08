import click
from .database import (
    get_db_connection,
    create_table,
    add_entry,
    update_entry,
    export_to_json,
)
from .gui import launch_gui


@click.group()
@click.option(
    "--db", default="cuddly_potato.db", help="The path to the SQLite database file."
)
@click.pass_context
def cli(ctx, db):
    """A CLI tool to manage question-answer pairs for LLMs."""
    ctx.obj = {"DB_PATH": db}
    conn = get_db_connection(db)
    create_table(conn)
    conn.close()


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
    result = add_entry(conn, question, model, answer, domain, subdomain, comments)
    conn.close()
    click.echo(result)


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
    result = update_entry(
        conn, entry_id, question, model, answer, domain, subdomain, comments
    )
    conn.close()
    click.echo(result)


@cli.command()
@click.argument("output_path", type=click.Path())
@click.pass_context
def export(ctx, output_path):
    """Export the database to a JSON file."""
    conn = get_db_connection(ctx.obj["DB_PATH"])
    result = export_to_json(conn, output_path)
    conn.close()
    click.echo(result)


@cli.command()
def gui():
    """Launch the graphical user interface."""
    launch_gui()


if __name__ == "__main__":
    cli()
