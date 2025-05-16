import asyncio
import signal
import sys
from concurrent.futures import ProcessPoolExecutor
from types import FrameType

import click
import shepherd_core
import typer

from shepherd_server import __version__
from shepherd_server.instance_api import run as run_api_server
from shepherd_server.instance_db import db_insert_test
from shepherd_server.instance_redirect import run as run_redirect_server
from shepherd_server.instance_scheduler import run as run_scheduler_server
from shepherd_server.logger import log
from shepherd_server.logger import set_verbosity

cli = typer.Typer(help="Web-Server & -API for the Shepherd-Testbed")


def exit_gracefully(_signum: int, _frame: FrameType | None) -> None:
    log.warning("Exiting!")
    sys.exit(0)


verbose_opt_t = typer.Option(
    False,  # noqa: FBT003
    "--verbose",
    "-v",
    is_flag=True,
    help="Sets logging-level to debug",
)

version_opt_t = typer.Option(
    False,  # noqa: FBT003
    "--version",
    is_flag=True,
    help="Prints version-infos (combinable with -v)",
)


@cli.callback()
def cli_callback(*, verbose: bool = verbose_opt_t, version: bool = version_opt_t) -> None:
    """Enable verbosity and add exit-handlers
    this gets executed prior to the other sub-commands
    """
    signal.signal(signal.SIGTERM, exit_gracefully)
    signal.signal(signal.SIGINT, exit_gracefully)
    set_verbosity(debug=verbose)

    if version:
        log.info("Shepherd-Wsrv v%s", __version__)
        log.debug("Shepherd-Core v%s", shepherd_core.__version__)
        log.debug("Python v%s", sys.version)
        log.debug("Typer v%s", typer.__version__)
        log.debug("Click v%s", click.__version__)


@cli.command()
# def init(file: Path | None = None) -> None:
def init() -> None:
    """Creates structures in database, can also recover data from a backup"""
    asyncio.run(db_insert_test())
    # TODO: implement


@cli.command()
# def backup(file: Path | None = None) -> None:
def backup() -> None:
    """Dumps content of database to a file"""
    # TODO: implement
    # TODO: also dump default config or keep it in DB?


@cli.command()
def run_api() -> None:
    """Start web api to access data."""
    with ProcessPoolExecutor() as ppe:
        ppe.submit(run_api_server)


@cli.command()
def run_scheduler() -> None:
    """Start scheduler to coordinate the testbed.

    This is separate to webAPI to allow starting/stopping both individually
    """
    with ProcessPoolExecutor() as ppe:
        ppe.submit(run_scheduler_server)


@cli.command()
def redirect() -> None:
    """Start http redirect to landing-page."""
    run_redirect_server()


if __name__ == "__main__":
    cli()
