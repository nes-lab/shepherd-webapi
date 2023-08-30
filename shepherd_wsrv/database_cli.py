import typer
from asyncio import run as aiorun

from .database_models import models_init

cli_db = typer.Typer(
    name="database",
    help="Sub-Commands to work on the data")


@cli_db.command(help="create tables (deletes old content")
def init():
    aiorun(models_init())


