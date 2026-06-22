import logging
import smtplib
import ssl
from email.message import EmailMessage
from html import escape

import requests

from app.core.config import settings

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
    html_content: str | None = None,
) -> None:
    brevo_api_key = settings.brevo_api_key.strip() if settings.brevo_api_key else ""
    sender_email = settings.email_from.strip()

    if not brevo_api_key:
        logger.error("Brevo email delivery failed: BREVO_API_KEY is not configured.")
        raise EmailDeliveryError("Email provider is not configured.")

    if not sender_email:
        logger.error("Brevo email delivery failed: EMAIL_FROM is not configured.")
        raise EmailDeliveryError("Email provider is not configured.")

    payload = {
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
    }

    if html_content:
        payload["htmlContent"] = html_content

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "accept": "application/json",
                "api-key": settings.brevo_api_key.strip(),
                "content-type": "application/json",
            },
            json=payload,
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
    html_content: str | None = None,
) -> None:
    if settings.email_provider.strip().lower() == "brevo":
        _send_email_brevo(
            recipient_email=recipient_email,
            subject=subject,
            text_content=text_content,
            html_content=html_content,
        )
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.email_from.strip()
    message["To"] = recipient_email
    message.set_content(text_content)

    if html_content:
        message.add_alternative(html_content, subtype="html")

    _send_email_smtp(message)


def _build_code_email_html(
    *,
    preview_text: str,
    eyebrow: str,
    heading: str,
    intro: str,
    code: str,
    expire_minutes: int,
    security_note: str,
) -> str:
    safe_preview_text = escape(preview_text)
    safe_eyebrow = escape(eyebrow)
    safe_heading = escape(heading)
    safe_intro = escape(intro)
    safe_code = escape(code.strip())
    safe_security_note = escape(security_note)
    safe_expire_minutes = escape(str(expire_minutes))

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_heading}</title>
  </head>
  <body style="margin:0;padding:0;background:#f4f6fb;font-family:Arial,Helvetica,sans-serif;color:#111827;">
    <span style="display:none!important;visibility:hidden;opacity:0;color:transparent;height:0;width:0;overflow:hidden;mso-hide:all;">
      {safe_preview_text}
    </span>

    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f6fb;margin:0;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border-radius:28px;overflow:hidden;border:1px solid #e5e7eb;box-shadow:0 18px 45px rgba(15,23,42,0.10);">
            <tr>
              <td style="padding:32px 32px 20px 32px;background:linear-gradient(135deg,#6759ff 0%,#8a5cf6 52%,#22c1c3 100%);">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td align="left">
                      <div style="display:inline-block;width:52px;height:52px;line-height:52px;text-align:center;border-radius:18px;background:rgba(255,255,255,0.18);color:#ffffff;font-size:26px;font-weight:800;">
                        P
                      </div>
                    </td>
                    <td align="right" style="color:#eef2ff;font-size:14px;font-weight:700;letter-spacing:0.4px;">
                      Planora
                    </td>
                  </tr>
                </table>
                <div style="margin-top:28px;color:#dbeafe;font-size:13px;font-weight:800;text-transform:uppercase;letter-spacing:1.4px;">
                  {safe_eyebrow}
                </div>
                <h1 style="margin:10px 0 0 0;color:#ffffff;font-size:30px;line-height:1.18;font-weight:800;">
                  {safe_heading}
                </h1>
              </td>
            </tr>

            <tr>
              <td style="padding:30px 32px 8px 32px;">
                <p style="margin:0;color:#4b5563;font-size:16px;line-height:1.65;">
                  {safe_intro}
                </p>
              </td>
            </tr>

            <tr>
              <td style="padding:18px 32px 18px 32px;">
                <div style="background:#f8fafc;border:1px solid #e5e7eb;border-radius:22px;padding:24px;text-align:center;">
                  <div style="color:#64748b;font-size:13px;font-weight:800;text-transform:uppercase;letter-spacing:1.2px;margin-bottom:12px;">
                    Your secure code
                  </div>
                  <div style="font-family:'Courier New',Courier,monospace;color:#111827;font-size:36px;line-height:1;font-weight:800;letter-spacing:8px;">
                    {safe_code}
                  </div>
                </div>
              </td>
            </tr>

            <tr>
              <td style="padding:0 32px 28px 32px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#fff7ed;border:1px solid #fed7aa;border-radius:18px;">
                  <tr>
                    <td style="padding:16px 18px;color:#9a3412;font-size:14px;line-height:1.55;">
                      This code expires in <strong>{safe_expire_minutes} minutes</strong>. {safe_security_note}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <tr>
              <td style="padding:24px 32px 30px 32px;border-top:1px solid #eef2f7;">
                <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                  You received this email because a Planora account action was requested for this email address.
                </p>
                <p style="margin:14px 0 0 0;color:#64748b;font-size:14px;font-weight:700;">
                  Planora Team
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def send_verification_email(recipient_email: str, code: str) -> None:
    text_content = f"""Hello,

Welcome to Planora.
Your email verification code is:

{code}

This code will expire in {settings.verification_code_expire_minutes} minutes.
If you did not create a Planora account, you can safely ignore this email.

Planora Team
"""

    html_content = _build_code_email_html(
        preview_text="Use this code to verify your Planora email address.",
        eyebrow="Email verification",
        heading="Verify your email address",
        intro="Welcome to Planora. Enter this code in the app to finish verifying your email address.",
        code=code,
        expire_minutes=settings.verification_code_expire_minutes,
        security_note="If you did not create a Planora account, you can safely ignore this email.",
    )

    _send_email(
        recipient_email=recipient_email,
        subject="Your Planora verification code",
        text_content=text_content,
        html_content=html_content,
    )


def send_password_reset_email(recipient_email: str, code: str) -> None:
    text_content = f"""Hello,

You requested to reset your Planora password.
Your password reset code is:

{code}

This code will expire in {settings.password_reset_code_expire_minutes} minutes.
If you did not request this, you can safely ignore this email.
Never share this code with anyone.

Planora Team
"""

    html_content = _build_code_email_html(
        preview_text="Use this code to reset your Planora password.",
        eyebrow="Password reset",
        heading="Reset your password",
        intro="We received a request to reset your Planora password. Enter this code in the app to continue.",
        code=code,
        expire_minutes=settings.password_reset_code_expire_minutes,
        security_note="If you did not request this, ignore this email. Never share this code with anyone.",
    )

    _send_email(
        recipient_email=recipient_email,
        subject="Your Planora password reset code",
        text_content=text_content,
        html_content=html_content,
    )
