import asyncio
from asyncio import Timeout
from signal import signal

import pytest
import pytest_timeout
from typer.testing import CliRunner

from shepherd_server.cli import cli


def test_cli_help_full() -> None:
    res = CliRunner().invoke(
        app=cli,
        args=[
            "--help",
        ],
    )
    assert res.exit_code == 0
    assert len(res.output) > 30


def test_cli_version_minimal() -> None:
    res = CliRunner(mix_stderr=False).invoke(
        app=cli,
        args=["version"],
    )
    assert res.exit_code == 0
    # note: could test length of res.output and res.stderr
    #      -> stderr only usable with CliRunner(mix_stderr=False)


def test_cli_version_short() -> None:
    res = CliRunner().invoke(
        app=cli,
        args=[
            "-v",
            "version",
        ],
    )
    assert res.exit_code == 0


def test_cli_version_full() -> None:
    res = CliRunner().invoke(
        app=cli,
        args=[
            "--verbose",
            "version",
        ],
    )
    assert res.exit_code == 0


def test_cli_version_wrong() -> None:
    res = CliRunner().invoke(
        app=cli,
        args=[
            "--verbose",
            "worseion",
        ],
    )
    assert res.exit_code != 0


def test_cli_version_help_full() -> None:
    res = CliRunner().invoke(
        app=cli,
        args=[
            "--verbose",
            "version",
            "--help",
        ],
    )
    assert res.exit_code == 0
    assert len(res.output) > 30


def test_cli_init_short() -> None:
    res = CliRunner().invoke(
        app=cli,
        args=["-v", "init"],
    )
    assert res.exit_code == 0


def test_cli_backup_short() -> None:
    res = CliRunner().invoke(
        app=cli,
        args=["-v", "backup"],
    )
    assert res.exit_code == 0


@pytest.mark.timeout(10)
@pytest.mark.skipif(not hasattr(signal, "SIGALRM"), reason="Needs SIGALRM")
def test_cli_run_api_short() -> None:
    with pytest.raises(TimeoutError):
        res = CliRunner().invoke(
            app=cli,
            args=["-v", "run-api"],
            catch_exceptions=True,
        )
    assert res.exit_code == 0
