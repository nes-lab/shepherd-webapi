"""Mail server config."""

from fastapi_mail import ConnectionConfig
from fastapi_mail import FastMail
from fastapi_mail import MessageSchema
from fastapi_mail import MessageType

from shepherd_wsrv.config import CFG

mail_conf = ConnectionConfig(
    MAIL_USERNAME=CFG.mail_username,
    MAIL_PASSWORD=CFG.mail_password,
    MAIL_FROM=CFG.mail_sender,
    MAIL_PORT=CFG.mail_port,
    MAIL_SERVER=CFG.mail_server,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
)

mail = FastMail(mail_conf)


class MailEngine:
    # TODO reconsider term "MailEngine"

    async def send_verification_email(self, email: str, token: str) -> None: ...

    async def send_password_reset_email(self, email: str, token: str) -> None: ...


class FastMailEngine(MailEngine):
    async def send_verification_email(self, email: str, token: str) -> None:
        """Send user verification email."""
        # Change this later to public endpoint
        _url = CFG.root_url + "/user/verify/" + token
        if CFG.mail_console:
            print("POST to " + _url)
        else:
            message = MessageSchema(
                recipients=[email],
                subject="Shepherd Testbed Email Verification",
                body="Welcome to the Shepherd Testbed! "
                f"We just need to verify your email to begin: {_url}",
                subtype=MessageType.plain,
            )
            await mail.send_message(message)

    async def send_password_reset_email(self, email: str, token: str) -> None:
        """Send password reset email."""
        # Change this later to public endpoint
        _url = CFG.root_url + "/user/reset-password/" + token
        if CFG.mail_console:
            print("POST to " + _url)
        else:
            message = MessageSchema(
                recipients=[email],
                subject="Shepherd Testbed Password Reset",
                body="Click the link to reset your Shepherd Testbed account password: "
                f"{_url}\nIf you did not request this, please ignore this email",
                subtype=MessageType.plain,
            )
            await mail.send_message(message)


def mail_engine():
    return FastMailEngine()
