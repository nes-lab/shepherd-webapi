import asyncio
import signal
import sys
from pathlib import Path
from types import FrameType
from typing import Annotated

import shepherd_core
import typer

from shepherd_server.api_experiment.models import WebExperiment
from shepherd_server.api_user.models import User

from .backup_db import backup_db
from .instance_api import run as run_api_server
from .instance_db import db_insert_test
from .instance_redirect import run as run_redirect_server
from .instance_scheduler import run as run_scheduler_server
from .logger import log
from .logger import set_verbosity

cli = typer.Typer(help="Web-Server & -API for the Shepherd-Testbed")


def exit_gracefully(_signum: int, _frame: FrameType | None) -> None:
    log.warning("Exiting!")
    sys.exit(0)


verbose_opt_t = typer.Option(
    False,  # noqa: FBT003
    "--verbose",
    "-v",
    help="Sets logging-level to debug",
)


@cli.callback()
def cli_callback(*, verbose: bool = verbose_opt_t) -> None:
    """Enable verbosity and add exit-handlers
    this gets executed prior to the other sub-commands
    """
    signal.signal(signal.SIGTERM, exit_gracefully)
    signal.signal(signal.SIGINT, exit_gracefully)
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, exit_gracefully)
    set_verbosity(debug=verbose)


@cli.command()
def version() -> None:
    """Prints version-infos (combinable with -v)"""
    import click

    from .version import version as server_version

    log.info("shepherd-server v%s", server_version)
    log.debug("shepherd-core v%s", shepherd_core.__version__)
    log.debug("Python v%s", sys.version)
    log.debug("typer v%s", typer.__version__)
    log.debug("click v%s", click.__version__)


@cli.command()
# def init(file: Path | None = None) -> None:
def init() -> None:
    """Creates structures in database, can also recover data from a backup"""
    asyncio.run(db_insert_test())
    # TODO: implement


@cli.command()
def backup(
    path: Annotated[
        Path,
        typer.Argument(
            exists=True, file_okay=False, dir_okay=True, writable=True, resolve_path=True
        ),
    ],
) -> None:
    """Dumps content of database to a file (in addition to MongoDump-tool)"""
    # TODO: fails ATM
    log.warning("Dumping content of database to YAML-files does not fully work ATM")
    asyncio.run(backup_db(WebExperiment, path))
    if False:
        asyncio.run(backup_db(User, path))


@cli.command()
def run_api() -> None:
    """Start web api to access data."""
    run_api_server()


@cli.command()
def run_scheduler(inventory: Path | None = None, *, dry_run: bool = False) -> None:
    """Start scheduler to coordinate the testbed.

    This is separate to webAPI to allow starting/stopping both individually
    """
    run_scheduler_server(inventory, dry_run=dry_run)


@cli.command()
def run_redirect() -> None:
    """Start http redirect to landing-page."""
    run_redirect_server()


@cli.command()
def run(inventory: Path | None = None, *, dry_run: bool = False) -> None:
    """Start ALL sub-services in separate subprocess."""
    from concurrent.futures import ProcessPoolExecutor

    with ProcessPoolExecutor() as ppe:
        ppe.submit(run_scheduler_server, inventory=inventory, dry_run=dry_run)
        ppe.submit(run_api_server)
        ppe.submit(run_redirect_server)


if __name__ == "__main__":
    cli()
