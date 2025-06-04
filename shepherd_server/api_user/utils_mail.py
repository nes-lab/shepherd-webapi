"""Mail server config."""

from fastapi_mail import ConnectionConfig
from fastapi_mail import FastMail
from fastapi_mail import MessageSchema
from fastapi_mail import MessageType
from pydantic import EmailStr

from shepherd_server.config import CFG
from shepherd_server.logger import log

mail_conf = ConnectionConfig(
    MAIL_USERNAME=CFG.mail_username,
    MAIL_PASSWORD=CFG.mail_password,
    MAIL_FROM=CFG.mail_sender,
    MAIL_FROM_NAME=CFG.mail_sender_name,
    MAIL_PORT=CFG.mail_port,
    MAIL_SERVER=CFG.mail_server,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    MAIL_DEBUG=False,
)

mail = FastMail(mail_conf)


class MailEngine:
    # TODO: reconsider term "MailEngine"

    async def send_verification_email(self, email: EmailStr, token: str) -> None: ...

    async def send_password_reset_email(self, email: EmailStr, token: str) -> None: ...

    async def send_approval_request_email(self, email: EmailStr) -> None: ...


class FastMailEngine(MailEngine):
    async def send_verification_email(self, email: EmailStr, token: str) -> None:
        """Send user verification email."""
        # Change this later to public endpoint
        _url = f"{CFG.server_url()}/user/verify/{token}"
        log.debug("EMAIL POST to %s", _url)
        if CFG.mail_enabled:
            message = MessageSchema(
                recipients=[email],
                subject="Shepherd Testbed Email Verification",
                body="Welcome to the Shepherd Testbed! "
                f"We just need to verify your email to begin: {_url}",
                subtype=MessageType.plain,  # TODO: replace with HTTP + Link
            )
            await mail.send_message(message)

    async def send_password_reset_email(self, email: EmailStr, token: str) -> None:
        """Send password reset email."""
        # Change this later to public endpoint
        _url = f"{CFG.server_url()}/user/reset-password/{token}"
        log.debug("EMAIL POST to %s", _url)
        if CFG.mail_enabled:
            message = MessageSchema(
                recipients=[email],
                subject="Shepherd Testbed Password Reset",
                body="Click the link to reset your Shepherd Testbed account password: "
                f"{_url}\nIf you did not request this, please ignore this email",
                subtype=MessageType.plain,
            )
            await mail.send_message(message)

    async def send_approval_request_email(self, email: EmailStr) -> None:
        """Send approval request to admin / contact email."""
        # Change this later to public endpoint
        _url = f"{CFG.server_url()}/user/approve/{email}"
        log.debug("EMAIL POST to %s", _url)
        if CFG.mail_enabled:
            message = MessageSchema(
                recipients=[CFG.contact.get("email")],
                subject="Shepherd Testbed Approval Request",
                body=f"Click the link to approve the user '{email}': {_url}",
                subtype=MessageType.plain,
            )
            await mail.send_message(message)


def mail_engine() -> MailEngine:
    return FastMailEngine()
