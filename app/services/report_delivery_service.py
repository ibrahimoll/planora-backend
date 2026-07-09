from __future__ import annotations

from html import escape

from app.schemas.report_schema import ProjectReportResponse
from app.services.email_service import _send_email


def send_project_report_delivery(
    *,
    address: str,
    name: str | None,
    admin_name: str,
    note: str | None,
    report: ProjectReportResponse,
) -> None:
    display_name = name or "there"
    project = report.project
    safe_display_name = escape(display_name)
    safe_project_title = escape(project.title)
    safe_admin = escape(admin_name)
    safe_note = escape(note or "No note provided.")

    text_content = f"""Hello {display_name},

Your Planora project report is ready.

Project: {project.title}

Admin note:
{note or 'No note provided.'}

Open the Planora app, select the project, and open the Reports card to view the report.
The report is not attached to this email.

Sent by: {admin_name}
Planora Team
"""

    html_content = f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>Planora report ready</title>
  </head>
  <body style=\"margin:0;padding:0;background:#f6f3ff;font-family:Arial,Helvetica,sans-serif;color:#111827;\">
    <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" style=\"background:#f6f3ff;padding:28px 12px;\">
      <tr>
        <td align=\"center\">
          <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" style=\"max-width:600px;background:#ffffff;border:1px solid #e8def8;border-radius:22px;overflow:hidden;\">
            <tr>
              <td style=\"padding:30px;\">
                <div style=\"font-size:14px;font-weight:800;color:#7c3aed;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:12px;\">Report ready</div>
                <h1 style=\"margin:0 0 14px 0;font-size:28px;line-height:1.2;color:#111827;\">Your report is ready in Planora</h1>
                <p style=\"margin:0 0 18px 0;color:#4b5563;font-size:15px;line-height:1.7;\">Hello {safe_display_name}, your admin has prepared a report for <strong>{safe_project_title}</strong>.</p>

                <div style=\"padding:16px 18px;background:#f8f5ff;border:1px solid #eadfff;border-radius:16px;color:#4b5563;margin-bottom:18px;line-height:1.7;\">
                  <strong style=\"color:#111827;\">Admin note:</strong><br>{safe_note}
                </div>

                <div style=\"padding:16px 18px;background:#ecfeff;border:1px solid #a5f3fc;border-radius:16px;color:#155e75;line-height:1.7;\">
                  Open the Planora app, go to the project, then open the <strong>Reports</strong> card to view it.
                </div>

                <p style=\"margin:20px 0 0 0;color:#6b7280;font-size:13px;line-height:1.6;\">Prepared by {safe_admin}. Open Planora directly if you were not expecting this message.</p>
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
        recipient_email=address,
        subject=f"[Planora] Project report ready - {project.title}",
        text_content=text_content,
        html_content=html_content,
    )
