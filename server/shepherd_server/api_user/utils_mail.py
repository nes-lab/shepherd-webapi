"""Mail server config."""

from fastapi_mail import ConnectionConfig
from fastapi_mail import FastMail
from fastapi_mail import MessageSchema
from fastapi_mail import MessageType
from pydantic import EmailStr

from shepherd_server.api_experiment.models import WebExperiment
from shepherd_server.config import config
from shepherd_server.logger import log

mail_conf = ConnectionConfig(
    MAIL_USERNAME=config.mail_username,
    MAIL_PASSWORD=config.mail_password,
    MAIL_FROM=config.mail_sender,
    MAIL_FROM_NAME=config.mail_sender_name,
    MAIL_PORT=config.mail_port,
    MAIL_SERVER=config.mail_server,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    MAIL_DEBUG=False,
)

mail = FastMail(mail_conf)


class MailEngine:
    # TODO: reconsider term "MailEngine"

    @staticmethod
    async def send_approval_email(email: EmailStr, token: str) -> None: ...

    @staticmethod
    async def send_verification_email(email: EmailStr, token: str) -> None: ...

    @staticmethod
    async def send_registration_complete_email(email: EmailStr) -> None: ...

    @staticmethod
    async def send_password_reset_email(email: EmailStr, token: str) -> None: ...

    @staticmethod
    async def send_experiment_finished_email(
        email: EmailStr, web_exp: WebExperiment, *, all_done: bool = False
    ) -> None: ...


class FastMailEngine(MailEngine):
    @staticmethod
    async def send_approval_email(email: EmailStr, token: str) -> None:
        """Send approval request to admin / contact email."""
        # Change this later to public endpoint
        log.debug("-> EMAIL APPROVAL")
        if config.mail_enabled:
            message = MessageSchema(
                recipients=[email],
                subject="[Shepherd] Testbed Approval",
                body="Welcome to the Shepherd Nova Testbed!"
                f"\n\nUse the following token for registering this Email-Address: {token}\n"
                "The client is available at: https://pypi.org/project/shepherd-client/",
                subtype=MessageType.plain,
            )
            await mail.send_message(message)

    @staticmethod
    async def send_verification_email(email: EmailStr, token: str) -> None:
        """Send user verification email."""
        _url = f"{config.server_url()}/user/verify/{token}"
        log.info("Verification E-Mail was sent to User (Account deactivated by default).")
        if config.mail_enabled:
            message = MessageSchema(
                recipients=[email],
                subject="[Shepherd] Email Verification",
                body="Welcome to the Shepherd Nova Testbed! "
                f"You just need to verify your email to complete registration: {_url}",
                subtype=MessageType.plain,  # TODO: replace with HTTP + Link
            )
            await mail.send_message(message)

    @staticmethod
    async def send_registration_complete_email(email: EmailStr) -> None:
        log.debug("-> EMAIL REGISTRATION")
        if config.mail_enabled:
            message = MessageSchema(
                recipients=[email],
                subject="[Shepherd] Registration Complete",
                body="You are now fully registered and can use the Testbed",
                subtype=MessageType.plain,
            )
            await mail.send_message(message)

    @staticmethod
    async def send_password_reset_email(email: EmailStr, token: str) -> None:
        """Send password reset email."""
        # Change this later to public endpoint
        _url = f"{config.server_url()}/user/reset-password/{token}"
        log.debug("-> EMAIL RESET POST to %s", _url)
        if config.mail_enabled:
            message = MessageSchema(
                recipients=[email],
                subject="[Shepherd] Password Reset",
                body="Click the link to reset your Testbed account password: "
                f"{_url}\nIf you did not request this, please ignore this email",
                subtype=MessageType.plain,
            )
            await mail.send_message(message)

    @staticmethod
    async def send_experiment_finished_email(
        email: EmailStr, web_exp: WebExperiment, *, all_done: bool = False
    ) -> None:
        msg = f"Experiment {web_exp.experiment.name} ({web_exp.id}) finished.\n"
        if web_exp.max_exit_code > 0:
            msg += (
                "\nErrors were encountered during execution. "
                "The Console-Outputs of failing Observers are attached in this mail and "
                "have also been sent to the admin.\n"
            )
        if web_exp.scheduler_panic:
            msg += "\nThe Scheduler panicked during execution - files might be missing.\n"
        xp_files_n = len(web_exp.result_paths) if web_exp.result_paths is not None else 0
        if xp_files_n > 0:
            xp_size_MiB = round(web_exp.result_size / 2**20)
            msg += f"\nResults can now be downloaded ({xp_files_n} files, {xp_size_MiB} MiB).\n"
        else:
            msg += "\nIt seems that no files were generated.\n"
        if all_done:
            msg += "\nThere are no further experiments scheduled for you.\n"
        if len(web_exp.observers_offline) > 0:
            msg += (
                f"\nDuring the experiment {len(web_exp.observers_offline)} observer(s) "
                f"was/were unavailable: {', '.join(web_exp.observers_offline)}\n"
            )
        extra_subj = " with errors" if web_exp.had_errors else ""
        log.debug("-> EMAIL XP-Finished" + extra_subj)
        if config.mail_enabled:
            message = MessageSchema(
                recipients=list({email, config.contact["email"]})
                if web_exp.had_errors
                else [email],
                subject="[Shepherd] Experiment finished" + extra_subj,
                body=msg,
                subtype=MessageType.plain,
                attachments=web_exp.get_terminal_output(only_faulty=True),
            )
            await mail.send_message(message)


def mail_engine() -> MailEngine:
    return FastMailEngine()
