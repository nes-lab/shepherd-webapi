from signal import signal

import pytest
from fastapi.testclient import TestClient
from shepherd_server.api_accounts.utils_mail import MailEngine
from shepherd_server.cli import cli
from typer.testing import CliRunner


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
    res = CliRunner().invoke(
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


@pytest.mark.skip  # TODO: fix mock.problem - create_admin() sends real mail
def test_cli_create_admin_new(client: TestClient, mail_engine_mock: MailEngine) -> None:
    res = CliRunner().invoke(
        app=cli,
        args=[
            "--verbose",
            "create-admin",
            "padmin1@cadmin.de",
            "1234567890",
        ],
    )
    assert res.exit_code == 0
    mail_engine_mock.send_verification_email.assert_called_once()
    _, token = mail_engine_mock.send_verification_email.call_args.args
    with client.regular_joe():
        verification_response = client.post(
            f"/accounts/verify/{token}",
        )
        assert verification_response.status_code == 200


def test_cli_reset_nothing() -> None:
    res = CliRunner().invoke(app=cli, args=["-v", "reset"])
    assert res.exit_code == 0


@pytest.mark.timeout(1)
def test_cli_reset_users_fail() -> None:
    # each expects user-confirmation before doing anything!
    res = CliRunner().invoke(app=cli, args=["-v", "reset", "--users"])
    assert res.exit_code > 0


@pytest.mark.timeout(1)
def test_cli_reset_experiments_fail() -> None:
    res = CliRunner().invoke(app=cli, args=["-v", "reset", "--experiments"])
    assert res.exit_code > 0


@pytest.mark.timeout(1)
def test_cli_reset_stats_fail() -> None:
    res = CliRunner().invoke(app=cli, args=["-v", "reset", "--stats"])
    assert res.exit_code > 0


@pytest.mark.timeout(1)
def test_cli_reset_testbed_fail() -> None:
    res = CliRunner().invoke(app=cli, args=["-v", "reset", "--testbed"])
    assert res.exit_code > 0


@pytest.mark.timeout(1)
def test_cli_reset_users() -> None:
    res = CliRunner().invoke(app=cli, args=["-v", "reset", "--users", "--yes"])
    assert res.exit_code == 0


@pytest.mark.timeout(1)
def test_cli_reset_experiments() -> None:
    res = CliRunner().invoke(app=cli, args=["-v", "reset", "--experiments", "--yes"])
    assert res.exit_code == 0


@pytest.mark.timeout(1)
def test_cli_reset_stats() -> None:
    res = CliRunner().invoke(app=cli, args=["-v", "reset", "--stats", "--yes"])
    assert res.exit_code == 0


@pytest.mark.timeout(1)
def test_cli_reset_testbed() -> None:
    res = CliRunner().invoke(app=cli, args=["-v", "reset", "--testbed", "--yes"])
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


@pytest.mark.timeout(10)
@pytest.mark.skipif(not hasattr(signal, "SIGALRM"), reason="Needs SIGALRM")
def test_cli_run_scheduler_short() -> None:
    with pytest.raises(TimeoutError):
        res = CliRunner().invoke(
            app=cli,
            args=["-v", "run-scheduler"],
            catch_exceptions=True,
        )
    assert res.exit_code == 0


@pytest.mark.timeout(10)
@pytest.mark.skipif(not hasattr(signal, "SIGALRM"), reason="Needs SIGALRM")
def test_cli_run_scheduler_dry() -> None:
    with pytest.raises(TimeoutError):
        res = CliRunner().invoke(
            app=cli,
            args=["-v", "run-scheduler", "--dry-run"],
            catch_exceptions=True,
        )
    assert res.exit_code == 0


@pytest.mark.timeout(10)
@pytest.mark.skipif(not hasattr(signal, "SIGALRM"), reason="Needs SIGALRM")
def test_cli_run_redirect_short() -> None:
    with pytest.raises(TimeoutError):
        res = CliRunner().invoke(
            app=cli,
            args=["-v", "run-redirect"],
            catch_exceptions=True,
        )
    assert res.exit_code == 0


@pytest.mark.timeout(10)
@pytest.mark.skipif(not hasattr(signal, "SIGALRM"), reason="Needs SIGALRM")
def test_cli_run_all_short() -> None:
    with pytest.raises(TimeoutError):
        res = CliRunner().invoke(
            app=cli,
            args=["-v", "run"],
            catch_exceptions=True,
        )
    assert res.exit_code == 0
