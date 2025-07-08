import click
from .database import (
    get_db_connection,
    create_table,
    add_entry,
    update_entry,
    export_to_json,
)


@click.group()
@click.pass_context
def cli(ctx):
    """A CLI tool to manage question-answer pairs for LLMs."""
    ctx.obj = get_db_connection()
    create_table(ctx.obj)


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
    result = add_entry(ctx.obj, question, model, answer, domain, subdomain, comments)
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
    result = update_entry(
        ctx.obj, entry_id, question, model, answer, domain, subdomain, comments
    )
    click.echo(result)


@cli.command()
@click.argument("output_path", type=click.Path())
@click.pass_context
def export(ctx, output_path):
    """Export the database to a JSON file."""
    result = export_to_json(ctx.obj, output_path)
    click.echo(result)


if __name__ == "__main__":
    cli()
