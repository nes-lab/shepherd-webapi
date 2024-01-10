import asyncio
import signal
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from types import FrameType

import typer

from .logger import log, set_verbosity
from .api_instance import run as web_api_run
from .redirect_instance import run as web_redirect_run
from .db_instance import db_init, db_insert_test


cli = typer.Typer(help="Web-Server & -API for the Shepherd-Testbed")


def exit_gracefully(_signum: int, _frame: FrameType | None) -> None:
    log.warning("Aborted!")
    sys.exit(0)


@cli.callback()
def cli_callback(verbose: bool = False) -> None:
    """ enable verbosity and add exit-handlers
    this gets executed prior to the other sub-commands"""
    signal.signal(signal.SIGTERM, exit_gracefully)
    signal.signal(signal.SIGINT, exit_gracefully)
    set_verbosity(verbose)


@cli.command()
def redirect() -> None:
    """take webserver offline and only redirect to github-documentation"""
    web_redirect_run()


@cli.command()
def init(file: Path) -> None:
    """creates structures in database, can also recover data from a backup"""
    asyncio.run(db_init())
    asyncio.run(db_insert_test())
    # TODO implement


@cli.command()
def backup(file: Path) -> None:
    """dumps content of database to a file"""
    # TODO implement
    # TODO: also dump default config or keep it in DB?


@cli.command()
def run() -> None:
    """default functionality with web api, frontend and demons / schedulers to coordinate the testbed"""
    with ProcessPoolExecutor() as ppe:
        ppe.submit(web_api_run)
        #"web_ui": asyncio.create_task(web_frontend_run()),
    # TODO: starts frontent, api, other demons?
    # TODO: interface for observers
    # TODO: scheduler, job-handler


if __name__ == "__main__":
    cli()
