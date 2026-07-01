from __future__ import annotations

from html import escape

from app.schemas.report_schema import ProjectReportResponse
from app.services.email_service import _send_email


def _label(value: str | None) -> str:
    if not value:
        return "Not set"
    return value.replace("_", " ").title()


def _hours(value: float | int | None) -> str:
    if value is None:
        return "0h"
    return f"{float(value):.1f}h"


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
    progress = report.progress

    text_tasks = "\n".join(
        f"- {task.title} | {task.status} | {task.priority} | due {task.due_date or 'Not set'}"
        for task in report.tasks[:30]
    ) or "No tasks in this report."

    text_content = f"""Hello {display_name},

Your Planora project report is ready.

Project: {project.title}
Status: {project.status}
Deadline: {project.deadline}
Completion: {progress.completion_percentage}%
Tasks: {progress.completed_tasks}/{progress.total_tasks} completed
Overdue tasks: {progress.overdue_tasks}
Estimated hours: {report.hours.estimated_hours_total}h
Actual hours: {report.hours.actual_hours_total}h

Admin note:
{note or 'No note provided.'}

Tasks:
{text_tasks}

Sent by: {admin_name}
Planora Team
"""

    safe_project_title = escape(project.title)
    safe_status = escape(_label(str(project.status)))
    safe_deadline = escape(str(project.deadline.date()))
    safe_admin = escape(admin_name)
    safe_note = escape(note or "No note provided.")

    task_rows = "".join(
        f"""
        <tr>
          <td style=\"padding:10px;border-bottom:1px solid #ece7f8;color:#111827;font-weight:700;\">{escape(task.title)}</td>
          <td style=\"padding:10px;border-bottom:1px solid #ece7f8;color:#4b5563;\">{escape(_label(task.status))}</td>
          <td style=\"padding:10px;border-bottom:1px solid #ece7f8;color:#4b5563;\">{escape(_label(task.priority))}</td>
        </tr>
        """
        for task in report.tasks[:20]
    )

    if not task_rows:
        task_rows = """
        <tr>
          <td colspan=\"3\" style=\"padding:14px;color:#6b7280;\">No tasks in this report.</td>
        </tr>
        """

    html_content = f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>Planora Project Report</title>
  </head>
  <body style=\"margin:0;padding:0;background:#f6f3ff;font-family:Arial,Helvetica,sans-serif;color:#111827;\">
    <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" style=\"background:#f6f3ff;padding:28px 12px;\">
      <tr>
        <td align=\"center\">
          <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" style=\"max-width:720px;background:#ffffff;border:1px solid #e8def8;border-radius:22px;overflow:hidden;\">
            <tr>
              <td style=\"padding:30px;\">
                <div style=\"font-size:14px;font-weight:800;color:#7c3aed;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:12px;\">Project report</div>
                <h1 style=\"margin:0 0 8px 0;font-size:30px;line-height:1.2;color:#111827;\">{safe_project_title}</h1>
                <p style=\"margin:0 0 20px 0;color:#6b7280;font-size:14px;\">Sent by {safe_admin}</p>

                <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" style=\"margin-bottom:18px;\">
                  <tr>
                    <td style=\"width:50%;padding:14px;background:#f8f5ff;border-radius:14px;color:#4b5563;\"><strong style=\"display:block;color:#111827;font-size:22px;\">{progress.completion_percentage:.0f}%</strong>Completion</td>
                    <td style=\"width:12px;\"></td>
                    <td style=\"width:50%;padding:14px;background:#f8f5ff;border-radius:14px;color:#4b5563;\"><strong style=\"display:block;color:#111827;font-size:22px;\">{progress.completed_tasks}/{progress.total_tasks}</strong>Tasks completed</td>
                  </tr>
                </table>

                <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" style=\"background:#f8f5ff;border:1px solid #eadfff;border-radius:16px;margin-bottom:18px;\">
                  <tr><td style=\"padding:18px 20px;color:#111827;font-size:15px;line-height:1.8;\">
                    <strong>Status:</strong> {safe_status}<br>
                    <strong>Deadline:</strong> {safe_deadline}<br>
                    <strong>Overdue tasks:</strong> {progress.overdue_tasks}<br>
                    <strong>Estimated hours:</strong> {_hours(report.hours.estimated_hours_total)}<br>
                    <strong>Actual hours:</strong> {_hours(report.hours.actual_hours_total)}
                  </td></tr>
                </table>

                <div style=\"padding:16px 18px;background:#fff7ed;border:1px solid #fed7aa;border-radius:16px;color:#7c2d12;margin-bottom:20px;line-height:1.6;\">
                  <strong>Admin note:</strong><br>{safe_note}
                </div>

                <h2 style=\"font-size:18px;margin:0 0 12px 0;\">Task summary</h2>
                <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" style=\"border:1px solid #ece7f8;border-radius:14px;overflow:hidden;border-collapse:separate;\">
                  <tr>
                    <th align=\"left\" style=\"padding:10px;background:#f8f5ff;color:#4b5563;\">Task</th>
                    <th align=\"left\" style=\"padding:10px;background:#f8f5ff;color:#4b5563;\">Status</th>
                    <th align=\"left\" style=\"padding:10px;background:#f8f5ff;color:#4b5563;\">Priority</th>
                  </tr>
                  {task_rows}
                </table>
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
        subject=f"Planora project report: {project.title}",
        text_content=text_content,
        html_content=html_content,
    )
