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
    safe_code_display = escape(" ".join(code.strip()))
    safe_security_note = escape(security_note)
    safe_expire_minutes = escape(str(expire_minutes))

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="dark">
    <meta name="supported-color-schemes" content="dark">
    <title>{safe_heading}</title>
  </head>
  <body style="margin:0;padding:0;background:#0b1018;font-family:Arial,Helvetica,sans-serif;color:#f8fafc;">
    <span style="display:none!important;visibility:hidden;opacity:0;color:transparent;height:0;width:0;overflow:hidden;mso-hide:all;">
      {safe_preview_text}
    </span>

    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#0b1018;margin:0;padding:34px 14px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#111722;border-radius:24px;overflow:hidden;border:1px solid #2b3342;box-shadow:0 22px 54px rgba(0,0,0,0.42);">
            <tr>
              <td style="height:76px;background:#171d28;border-bottom:1px solid #2b3342;line-height:76px;font-size:1px;">
                &nbsp;
              </td>
            </tr>

            <tr>
              <td style="padding:40px 42px 8px 42px;background:#101721;">
                <div style="margin:0 0 26px 0;color:#f8fafc;font-size:30px;line-height:1;font-weight:500;letter-spacing:-0.4px;">
                  Planora
                </div>
                <div style="margin:0 0 18px 0;color:#a9b4c7;font-size:13px;line-height:1.3;font-weight:800;text-transform:uppercase;letter-spacing:3.2px;">
                  {safe_eyebrow}
                </div>
                <h1 style="margin:0;color:#ffffff;font-size:46px;line-height:1.08;font-weight:800;letter-spacing:-1.4px;">
                  {safe_heading}
                </h1>
                <p style="margin:20px 0 0 0;color:#b8c2d2;font-size:17px;line-height:1.75;font-weight:400;">
                  {safe_intro}
                </p>
              </td>
            </tr>

            <tr>
              <td style="padding:30px 42px 24px 42px;background:#101721;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#171d28;border:1px solid #3a4354;border-radius:18px;box-shadow:inset 0 1px 0 rgba(255,255,255,0.04);">
                  <tr>
                    <td align="center" style="padding:29px 20px 28px 20px;">
                      <div style="color:#aeb8ca;font-size:13px;font-weight:800;text-transform:uppercase;letter-spacing:2.7px;margin-bottom:18px;">
                        Your secure code
                      </div>
                      <table role="presentation" cellspacing="0" cellpadding="0" align="center">
                        <tr>
                          <td style="width:62px;border-top:1px solid #485165;font-size:1px;line-height:1px;">&nbsp;</td>
                          <td style="padding:0 14px;color:#a78bfa;font-size:18px;line-height:1;">✦</td>
                          <td style="font-family:'Courier New',Courier,monospace;color:#ffffff;font-size:42px;line-height:1;font-weight:700;letter-spacing:9px;white-space:nowrap;text-shadow:0 2px 14px rgba(255,255,255,0.10);">
                            {safe_code_display}
                          </td>
                          <td style="padding:0 14px;color:#a78bfa;font-size:18px;line-height:1;">✦</td>
                          <td style="width:62px;border-top:1px solid #485165;font-size:1px;line-height:1px;">&nbsp;</td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <tr>
              <td style="padding:0 42px 38px 42px;background:#101721;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#171d28;border:1px solid #323b4d;border-radius:16px;">
                  <tr>
                    <td width="54" valign="top" style="padding:20px 0 20px 22px;">
                      <div style="width:34px;height:34px;border-radius:999px;border:2px solid #a78bfa;color:#a78bfa;text-align:center;line-height:31px;font-size:18px;font-weight:700;">
                        ⏱
                      </div>
                    </td>
                    <td style="padding:20px 22px 20px 10px;color:#c2cad8;font-size:15px;line-height:1.65;">
                      This code expires in <strong style="color:#a78bfa;font-weight:800;">{safe_expire_minutes} minutes</strong>.<br>
                      {safe_security_note}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <tr>
              <td style="padding:0 42px 30px 42px;background:#101721;">
                <div style="height:1px;background:#262f3f;line-height:1px;font-size:1px;">&nbsp;</div>
                <p style="margin:22px 0 0 0;text-align:center;color:#8792a6;font-size:13px;line-height:1.6;">
                  © Planora. All rights reserved.
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
