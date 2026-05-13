import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


def _send_email(message: EmailMessage) -> None:
    ssl_context = ssl.create_default_context()
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

    with smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
    ) as smtp:
        smtp.starttls(context=ssl_context)
        smtp.login(
            settings.smtp_username,
            settings.smtp_password,
        )
        smtp.send_message(message)


def send_verification_email(recipient_email: str, code: str) -> None:
    message = EmailMessage()
    message["Subject"] = "Planora email verification code"
    message["From"] = settings.email_from
    message["To"] = recipient_email

    message.set_content(
        f"""Hello,
        Your Planora verification code is:

                        {code}

        This code will expire in {settings.verification_code_expire_minutes} minutes.
        
        If you did not create a Planora account, you can ignore this email.
        """
    )

    _send_email(message)


def send_password_reset_email(recipient_email: str, code: str) -> None:
    message = EmailMessage()
    message["Subject"] = "Planora password reset code"
    message["From"] = settings.email_from
    message["To"] = recipient_email

    message.set_content(
        f"""Hello,
        Your planora password reset code is:

        {code}

        This code will expire in {settings.password_reset_code_expire_minutes} minutes.
        If you did not request a password reset, you can ignore this email
        or you can change your password.
        """
    )

    _send_email(message)
