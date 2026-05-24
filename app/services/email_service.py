import smtplib
import ssl
from email.message import EmailMessage

import requests

from app.core.config import settings


def _send_email_smtp(message: EmailMessage) -> None:
    ssl_context = ssl.create_default_context()
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

    with smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
        timeout=20,
    ) as smtp:
        smtp.starttls(context=ssl_context)
        smtp.login(
            settings.smtp_username.strip(),
            settings.smtp_password.strip().replace(" ", ""),
        )
        smtp.send_message(message)


def _send_email_brevo(
    recipient_email: str,
    subject: str,
    text_content: str,
) -> None:
    if not settings.brevo_api_key:
        raise RuntimeError("BREVO_API_KEY is not configured.")

    response = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={
            "accept": "application/json",
            "api-key": settings.brevo_api_key,
            "content-type": "application/json",
        },
        json={
            "sender": {
                "name": settings.email_from_name,
                "email": settings.email_from,
            },
            "to": [
                {
                    "email": recipient_email,
                }
            ],
            "subject": subject,
            "textContent": text_content,
        },
        timeout=20,
    )

    response.raise_for_status()


def _send_email(
    recipient_email: str,
    subject: str,
    text_content: str,
) -> None:
    if settings.email_provider.lower() == "brevo":
        _send_email_brevo(
            recipient_email=recipient_email,
            subject=subject,
            text_content=text_content,
        )
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.email_from.strip()
    message["To"] = recipient_email
    message.set_content(text_content)

    _send_email_smtp(message)


def send_verification_email(recipient_email: str, code: str) -> None:
    text_content = f"""Hello,

Welcome to Planora.
Your email verification code is:

{code}

This code will expire in {settings.verification_code_expire_minutes} minutes.
If you did not create a Planora account, you can safely ignore this email.

Planora Team
"""

    _send_email(
        recipient_email=recipient_email,
        subject="Planora email verification code",
        text_content=text_content,
    )


def send_password_reset_email(recipient_email: str, code: str) -> None:
    text_content = f"""Hello,

You requested to reset your Planora password.
Your password reset code is:

{code}

This code will expire in {settings.password_reset_code_expire_minutes} minutes.
If you did not request this, you can safely ignore this email.

Planora Team
"""

    _send_email(
        recipient_email=recipient_email,
        subject="Planora password reset code",
        text_content=text_content,
    )