from __future__ import annotations

from html import escape
from urllib.parse import quote, urlencode

from app.core.config import settings
from app.services.email_service import _send_email

PLANORA_ADMIN_FALLBACK_URL = "https://planora-pi-inky.vercel.app"


def admin_base_url() -> str:
    configured_url = settings.admin_dashboard_url.strip().rstrip("/")

    if not configured_url or "localhost" in configured_url or "127.0.0.1" in configured_url:
        return PLANORA_ADMIN_FALLBACK_URL

    return configured_url


def build_send_report_url(
    *,
    project_id: int,
    requester_email: str,
    requester_name: str | None,
) -> str:
    base_url = admin_base_url()
    report_query = urlencode(
        {
            "projectId": str(project_id),
            "address": requester_email,
            "name": requester_name or "",
        }
    )
    next_path = f"/dashboard/send-report?{report_query}"
    return f"{base_url}/login?next={quote(next_path, safe='')}"


def send_actionable_report_request_email(
    *,
    recipient_email: str,
    admin_name: str,
    requester_name: str,
    requester_email: str,
    project_title: str,
    project_id: int,
    project_type: str,
) -> None:
    send_url = build_send_report_url(
        project_id=project_id,
        requester_email=requester_email,
        requester_name=requester_name,
    )

    safe_admin_name = escape(admin_name or "Admin")
    safe_requester_name = escape(requester_name or requester_email)
    safe_requester_email = escape(requester_email)
    safe_project_title = escape(project_title)
    safe_project_type = escape(project_type.replace("_", " ").title())
    safe_project_id = escape(str(project_id))
    safe_send_url = escape(send_url, quote=True)

    text_content = f"""Hello {admin_name or 'Admin'},

A Planora user requested a project report.

Project: {project_title}
Project ID: {project_id}
Project type: {project_type}
Requested by: {requester_name or requester_email} <{requester_email}>

Open this link to sign in and auto-fill the admin Send Report page:
{send_url}

You only need to add your admin note and click Generate & Send Report.

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
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:600px;background:#ffffff;border:1px solid #e8def8;border-radius:22px;overflow:hidden;">
            <tr>
              <td style="padding:28px 30px;">
                <div style="font-size:14px;font-weight:800;color:#7c3aed;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:12px;">Report request</div>
                <h1 style="margin:0 0 14px 0;font-size:28px;line-height:1.2;color:#111827;">A user requested a report</h1>
                <p style="margin:0 0 20px 0;color:#4b5563;font-size:15px;line-height:1.6;">Hello {safe_admin_name}, sign in and Planora will auto-fill the Send Report page from this request.</p>

                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f8f5ff;border:1px solid #eadfff;border-radius:16px;">
                  <tr><td style="padding:18px 20px;color:#111827;font-size:15px;line-height:1.8;">
                    <strong>Project:</strong> {safe_project_title}<br>
                    <strong>Project type:</strong> {safe_project_type}<br>
                    <strong>Project ID:</strong> {safe_project_id}<br>
                    <strong>User:</strong> {safe_requester_name} &lt;{safe_requester_email}&gt;
                  </td></tr>
                </table>

                <div style="text-align:center;margin:24px 0 18px 0;">
                  <a href="{safe_send_url}" style="display:inline-block;background:#7c3aed;color:#ffffff;text-decoration:none;font-weight:800;border-radius:14px;padding:14px 22px;">Open Send Report</a>
                </div>

                <p style="margin:0;color:#6b7280;font-size:13px;line-height:1.6;">After signing in, add your admin note and click Generate & Send Report.</p>
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
        subject=f"Planora report request: {project_title}",
        text_content=text_content,
        html_content=html_content,
    )
