import logging
import smtplib
import ssl
from email.message import EmailMessage

import requests

from app.core.config import settings
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    """Raised when the configured email provider cannot send a message."""


def _response_text(response: requests.Response | None) -> str:
    if response is None:
        return ""

    return response.text[:1000]


def _send_email_smtp(message: EmailMessage) -> None:
    ssl_context = ssl.create_default_context()
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

    try:
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
    except (OSError, smtplib.SMTPException) as exc:
        logger.exception("SMTP email delivery failed.")
        raise EmailDeliveryError("Email delivery failed.") from exc


def _send_email_brevo(
    recipient_email: str,
    subject: str,
    text_content: str,
) -> None:
    brevo_api_key = settings.brevo_api_key.strip() if settings.brevo_api_key else ""
    sender_email = settings.email_from.strip()

    if not brevo_api_key:
        logger.error("Brevo email delivery failed: BREVO_API_KEY is not configured.")
        raise EmailDeliveryError("Email provider is not configured.")

    if not sender_email:
        logger.error("Brevo email delivery failed: EMAIL_FROM is not configured.")
        raise EmailDeliveryError("Email provider is not configured.")

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "accept": "application/json",
                "api-key": settings.brevo_api_key.strip(),
                "content-type": "application/json",
            },
            json={
                "sender": {
                    "name": settings.email_from_name.strip(),
                    "email": sender_email,
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
    except requests.HTTPError as exc:
        logger.error(
            "Brevo email delivery failed with status %s: %s",
            response.status_code,
            _response_text(response),
        )
        raise EmailDeliveryError("Email delivery failed.") from exc
    except requests.RequestException as exc:
        logger.exception("Brevo email delivery request failed.")
        raise EmailDeliveryError("Email delivery failed.") from exc


def _send_email(
    recipient_email: str,
    subject: str,
    text_content: str,
) -> None:
    if settings.email_provider.strip().lower() == "brevo":
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


def send_password_reset_email(recipient_email: str, token: str) -> None:
    reset_link = (
        f"{settings.password_reset_frontend_url}"
        f"?{urlencode({'email': recipient_email, 'token': token})}"
    )

    text_content = f"""Hello,

You requested to reset your Planora password.

Click the link below to reset your password:

{reset_link}

This link will expire in {settings.password_reset_code_expire_minutes} minutes.
If you did not request this, you can safely ignore this email.

Planora Team
"""

    _send_email(
        recipient_email=recipient_email,
        subject="Reset your Planora password",
        text_content=text_content,
    )