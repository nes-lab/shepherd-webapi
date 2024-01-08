import typer

from .database_cli import cli_db

cli = typer.Typer(help="Web-Server & -API for the Shepherd-Testbed")
cli.add_typer(cli_db)


if __name__ == "__main__":
    cli()
