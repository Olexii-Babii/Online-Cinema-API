from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr

from config.dependencies import get_settings

settings = get_settings()


class EmailSender:
    def __init__(self) -> None:
        self.conf = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,
            MAIL_FROM=settings.MAIL_FROM,
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_STARTTLS=settings.MAIL_STARTTLS,
            MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
            USE_CREDENTIALS=settings.USE_CREDENTIALS,
            VALIDATE_CERTS=settings.VALIDATE_CERTS,
        )
        self.fm = FastMail(self.conf)

    async def _send_email(self, email_to: EmailStr, subject: str, body: str) -> None:
        message = MessageSchema(
            subject=subject, recipients=[email_to], body=body, subtype=MessageType.plain
        )

        await self.fm.send_message(message)

    async def send_activation_email(self, token: str, email_to: EmailStr):
        subject = "Activate your account"
        body = (
            "Please confirm your email address\n"
            f"{settings.BASE_URL}/accounts/activate?token={token}"
        )
        await self._send_email(email_to=email_to, subject=subject, body=body)

    async def send_activation_complete_email(self, email_to: EmailStr):
        subject = "Account Activated Successfully"
        body = (
            "You have successfully activated your account.\n"
            "Below you can login your account.\n"
            f"{settings.BASE_URL}/accounts/login/"
        )
        await self._send_email(email_to=email_to, subject=subject, body=body)

    async def send_password_reset_email(self, email_to: EmailStr, token: str):
        subject = "Reset your password"
        body = (
            "Please confirm, if you want to change password\n"
            f"{settings.BASE_URL}/accounts/reset-password?token={token}"
        )
        await self._send_email(email_to=email_to, subject=subject, body=body)

    async def send_password_reset_complete_email(self, email_to: EmailStr):
        subject = "Password Changed Successfully"
        body = (
            "You have successfully changed your password.\n"
            "Below you can login your account.\n"
            f"{settings.BASE_URL}/accounts/login/"
        )
        await self._send_email(email_to=email_to, subject=subject, body=body)
