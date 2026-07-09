import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
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
    sender_name = settings.email_from_name.strip() or "Planora"
    sender_email = settings.email_from.strip()

    message["From"] = formataddr((sender_name, sender_email))
    message["Auto-Submitted"] = "auto-generated"
    message["X-Auto-Response-Suppress"] = "All"
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

<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif;color:#111827;">
  <span style="display:none!important;visibility:hidden;opacity:0;height:0;width:0;overflow:hidden;">
    {safe_preview_text}
  </span>

  <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
         style="background:#f3f4f6;padding:32px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
               style="max-width:580px;background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;">

          <tr>
            <td style="padding:22px 28px;border-bottom:1px solid #e5e7eb;">
              <table role="presentation" width="100%">
                <tr>
                  <td style="font-size:22px;font-weight:700;color:#111827;">
                    Planora
                  </td>
                  <td align="right"
                      style="font-size:12px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:1px;">
                    {safe_eyebrow}
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td style="padding:30px 28px;">
              <h1 style="margin:0 0 16px;font-size:28px;line-height:1.3;color:#111827;">
                {safe_heading}
              </h1>

              <p style="margin:0 0 22px;color:#374151;font-size:15px;line-height:1.7;">
                {safe_intro}
              </p>

              <div style="padding:22px 16px;background:#f9fafb;border:1px solid #d1d5db;border-radius:10px;text-align:center;">
                <div style="margin-bottom:10px;color:#6b7280;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;">
                  One-time code
                </div>

                <div style="font-family:'Courier New',Courier,monospace;font-size:34px;font-weight:700;letter-spacing:6px;color:#111827;">
                  {safe_code}
                </div>
              </div>

              <p style="margin:20px 0 0;color:#374151;font-size:14px;line-height:1.6;">
                This code expires in <strong>{safe_expire_minutes} minutes</strong>.
              </p>

              <div style="margin-top:18px;padding:14px 16px;background:#fffbeb;border:1px solid #fde68a;border-radius:8px;color:#78350f;font-size:13px;line-height:1.6;">
                {safe_security_note}
              </div>
            </td>
          </tr>

          <tr>
            <td style="padding:20px 28px;background:#f9fafb;border-top:1px solid #e5e7eb;">
              <p style="margin:0;color:#6b7280;font-size:12px;line-height:1.6;">
                This automated message was sent because an account action was requested in Planora.
                Planora will never ask you to reply with your password or one-time code.
              </p>

              <p style="margin:10px 0 0;color:#374151;font-size:13px;font-weight:700;">
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

Use the following one-time code to verify your email address in Planora:

{code}

This code expires in {settings.verification_code_expire_minutes} minutes.

If you did not create a Planora account, you can ignore this message.
Do not share this code with anyone, including someone claiming to be from Planora.

Planora Team
"""

    html_content = _build_code_email_html(
        preview_text="Use this code to verify your Planora email address.",
        eyebrow="Email verification",
        heading="Verify your email address",
        intro="Welcome to Planora. Enter this code in the app to finish verifying your email address.",
        code=code,
        expire_minutes=settings.verification_code_expire_minutes,
        security_note=(
    "If you did not request this reset, ignore this email and your "
    "password will remain unchanged. Do not share this code."
        ),
    )

    _send_email(
        recipient_email=recipient_email,
        subject="[Planora] Verify your email address",
        text_content=text_content,
        html_content=html_content,
    )


def send_password_reset_email(recipient_email: str, code: str) -> None:
    text_content = f"""Hello,

A password reset was requested for your Planora account.

Use the following one-time code in the Planora app:

{code}

This code expires in {settings.password_reset_code_expire_minutes} minutes.

If you did not request this password reset, ignore this message and your password will remain unchanged.
Do not share this code with anyone, including someone claiming to be from Planora.

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
        subject="[Planora] Password reset code",
        text_content=text_content,
        html_content=html_content,
    )


def send_report_request_email(
    *,
    recipient_email: str,
    admin_name: str,
    requester_name: str,
    requester_email: str,
    project_title: str,
    project_id: int,
    project_type: str,
) -> None:
    safe_admin_name = escape(admin_name or "Admin")
    safe_requester_name = escape(requester_name or requester_email)
    safe_requester_email = escape(requester_email)
    safe_project_title = escape(project_title)
    safe_project_type = escape(project_type.replace("_", " ").title())
    safe_project_id = escape(str(project_id))

    text_content = f"""Hello {admin_name or 'Admin'},

A Planora user requested a project report.

Project: {project_title}
Project ID: {project_id}
Project type: {project_type}
Requested by: {requester_name or requester_email} <{requester_email}>

Please review this request from the admin dashboard and generate the report if appropriate.

Planora Team
"""

    html_content = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Planora report request</title>
  </head>
  <body style="margin:0;padding:0;background:#f6f3ff;font-family:Arial,Helvetica,sans-serif;color:#111827;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f6f3ff;padding:28px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:560px;background:#ffffff;border:1px solid #e8def8;border-radius:22px;overflow:hidden;">
            <tr>
              <td style="padding:28px 30px;">
                <div style="font-size:14px;font-weight:800;color:#7c3aed;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:12px;">Report request</div>
                <h1 style="margin:0 0 14px 0;font-size:28px;line-height:1.2;color:#111827;">New project report request</h1>
                <p style="margin:0 0 20px 0;color:#4b5563;font-size:15px;line-height:1.6;">Hello {safe_admin_name}, please review this request from the admin dashboard.</p>
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f8f5ff;border:1px solid #eadfff;border-radius:16px;">
                  <tr><td style="padding:18px 20px;color:#111827;font-size:15px;line-height:1.8;">
                    <strong>Project:</strong> {safe_project_title}<br>
                    <strong>Project type:</strong> {safe_project_type}<br>
                    <strong>Internal project reference:</strong> {safe_project_id}<br>
                    <strong>Requested by:</strong> {safe_requester_name} &lt;{safe_requester_email}&gt;
                  </td></tr>
                </table>
                <p style="margin:20px 0 0 0;color:#6b7280;font-size:13px;line-height:1.6;">This automated administrative email was generated after a user requested a report in Planora.</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""

    _send_email(
        recipient_email=recipient_email,
        subject=f"[Planora Admin] Report request - {project_title}",
        text_content=text_content,
        html_content=html_content,
    )
