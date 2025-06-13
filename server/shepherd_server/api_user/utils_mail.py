"""Mail server config."""

from fastapi_mail import ConnectionConfig
from fastapi_mail import FastMail
from fastapi_mail import MessageSchema
from fastapi_mail import MessageType
from pydantic import EmailStr

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


class FastMailEngine(MailEngine):
    @staticmethod
    async def send_approval_email(email: EmailStr, token: str) -> None:
        """Send approval request to admin / contact email."""
        # Change this later to public endpoint
        log.debug("EMAIL APPROVAL")
        if config.mail_enabled:
            message = MessageSchema(
                recipients=[email],
                subject="Shepherd Testbed Approval",
                body="Welcome to the Shepherd Testbed! "
                f"Use the following token for registering this Email-Address: {token}",
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
                subject="Shepherd Testbed Email Verification",
                body="Welcome to the Shepherd Testbed! "
                f"You just need to verify your email to complete registration: {_url}",
                subtype=MessageType.plain,  # TODO: replace with HTTP + Link
            )
            await mail.send_message(message)

    @staticmethod
    async def send_registration_complete_email(email: EmailStr) -> None:
        log.debug("EMAIL REGISTRATION")
        if config.mail_enabled:
            message = MessageSchema(
                recipients=[email],
                subject="Shepherd Testbed Registration Complete",
                body="You are now fully registered and can use the Testbed",
                subtype=MessageType.plain,
            )
            await mail.send_message(message)

    @staticmethod
    async def send_password_reset_email(email: EmailStr, token: str) -> None:
        """Send password reset email."""
        # Change this later to public endpoint
        _url = f"{config.server_url()}/user/reset-password/{token}"
        log.debug("EMAIL POST to %s", _url)
        if config.mail_enabled:
            message = MessageSchema(
                recipients=[email],
                subject="Shepherd Testbed Password Reset",
                body="Click the link to reset your Shepherd Testbed account password: "
                f"{_url}\nIf you did not request this, please ignore this email",
                subtype=MessageType.plain,
            )
            await mail.send_message(message)


def mail_engine() -> MailEngine:
    return FastMailEngine()
