import asyncio
import signal
import sys
from pathlib import Path
from types import FrameType

import typer

from . import instance_db as db
from .api_user.models import PasswordStr
from .database_prune import prune_db
from .instance_api import run as run_api_server
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
    from importlib import metadata

    log.info("shepherd-server v%s", metadata.version("shepherd-server"))
    log.debug("Python v%s", sys.version)
    for package in [
        "shepherd-core",
        "shepherd-herd",
        "typer",
        "click",
        "pydantic",
        "beanie",
        "fastapi",
    ]:
        log.debug("%s v%s", package, metadata.version(package))


# #######################################################################
# Server Tasks ##########################################################
# #######################################################################


@cli.command()
def run_api() -> None:
    """Start web api to access data."""
    run_api_server()


@cli.command()
def run_scheduler(
    inventory: Path | None = None, *, dry_run: bool = False, only_elevated: bool = False
) -> None:
    """Start scheduler to coordinate the testbed.

    This is separate to webAPI to allow starting/stopping both individually
    """
    run_scheduler_server(inventory, dry_run=dry_run, only_elevated=only_elevated)


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
    asyncio.run(db.db_create_admin(email, password))


@cli.command()
def prune(*, delete: bool = False) -> None:
    """Clean up Database."""
    asyncio.run(prune_db(dry_run=not delete))


@cli.command()
def reset(
    *,
    users: bool = False,
    experiments: bool = False,
    stats: bool = False,
    testbed: bool = False,
    yes: bool = False,
) -> None:
    """Delete structures in database - mainly to help to recover after major refactorings."""
    if any([users, experiments, stats, testbed]):
        log.warning("You are about to delete actual data from the DB! Do you have backups?")
        if not yes:
            # ask for permission
            response = typer.prompt("Press y to continue")
            if response.lower() != "y":
                log.info("Process interrupted by user")
                sys.exit(0)
    if users:
        asyncio.run(db.db_delete_all_users())
    if experiments:
        asyncio.run(db.db_delete_all_experiments())
    if stats:
        asyncio.run(db.db_delete_all_experiment_stats())
    if testbed:
        asyncio.run(db.db_delete_testbed())


if __name__ == "__main__":
    cli()
