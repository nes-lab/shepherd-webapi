import signal
import sys
from types import FrameType

import shepherd_core
import typer
from shepherd_core.logger import increase_verbose_level
from shepherd_core.logger import logger

cli = typer.Typer(help="Web-Server & -API for the Shepherd-Testbed")


def exit_gracefully(_signum: int, _frame: FrameType | None) -> None:
    logger.warning("Exiting!")
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
    increase_verbose_level(3 if verbose else 2)


@cli.command()
def version() -> None:
    """Prints version-infos (combinable with -v)"""
    import click

    from .version import version as client_version

    logger.info("shepherd-client v%s", client_version)
    logger.debug("shepherd-core v%s", shepherd_core.__version__)
    logger.debug("Python v%s", sys.version)
    logger.debug("typer v%s", typer.__version__)
    logger.debug("click v%s", click.__version__)


# #######################################################################
# Server Tasks ##########################################################
# #######################################################################


# #######################################################################
# Data Management #######################################################
# #######################################################################


if __name__ == "__main__":
    cli()
