import asyncio
import signal
import sys
from pathlib import Path
from types import FrameType
from typing import Annotated

import pydantic
import shepherd_core
import shepherd_herd
import typer

from .api_experiment.models import WebExperiment
from .api_user.models import PasswordStr
from .api_user.models import User
from .database_backup import backup_db
from .database_prune import prune_db
from .instance_api import run as run_api_server
from .instance_db import db_create_admin, db_delete_all_experiments
from .instance_redirect import run as run_redirect_server
from .instance_scheduler import run as run_scheduler_server
from .logger import log
from .logger import set_verbosity

cli = typer.Typer(
    help="Web-Server & -API for the Shepherd-Testbed",
    pretty_exceptions_enable=False,
)


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
    log.debug("shepherd-herd v%s", shepherd_herd.__version__)
    log.debug("Python v%s", sys.version)
    log.debug("typer v%s", typer.__version__)
    log.debug("click v%s", click.__version__)
    log.debug("pydantic v%s", pydantic.__version__)


# #######################################################################
# Server Tasks ##########################################################
# #######################################################################


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

    # TODO: either log-messages are muted or scheduler is not running correctly
    with ProcessPoolExecutor() as ppe:
        ppe.submit(run_scheduler_server, inventory=inventory, dry_run=dry_run)
        ppe.submit(run_api_server)
        ppe.submit(run_redirect_server)


# #######################################################################
# Data Management #######################################################
# #######################################################################


@cli.command()
def create_admin(email: str, password: PasswordStr) -> None:
    """Bootstrap database and add an admin.

    User will have to verify if mail-service is activated."""
    asyncio.run(db_create_admin(email, password))


@cli.command()
def prune(*, delete: bool = False) -> None:
    """Clean up Database."""
    asyncio.run(prune_db(dry_run=not delete))


@cli.command()
# def init(file: Path | None = None) -> None:
def init() -> None:
    """Creates structures in database, can also recover data from a backup"""
    # TODO: implement
    asyncio.run(db_delete_all_experiments())


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
    # TODO: dump to file, restore from it - can beanie or motor do it?


if __name__ == "__main__":
    cli()
