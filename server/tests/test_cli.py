from signal import signal

import pytest
from fastapi.testclient import TestClient
from shepherd_server.api_user.utils_mail import MailEngine
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
            f"/user/verify/{token}",
        )
        assert verification_response.status_code == 200


def test_cli_init_short() -> None:
    res = CliRunner().invoke(
        app=cli,
        args=["-v", "init"],
    )
    assert res.exit_code == 0


def test_cli_backup_short() -> None:
    res = CliRunner().invoke(
        app=cli,
        args=["-v", "backup", "."],
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
