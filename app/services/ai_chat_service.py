from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.models.project import Project
from app.models.risk_analysis import RiskAnalysis
from app.models.task import Task
from app.models.user import User
from app.schemas.ai_chat_schema import AIChatRequest
from app.services.ai_provider_service import generate_ai_reply_from_provider


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _get_project_tasks(
    db: Session,
    project_id: int,
) -> list[Task]:
    stmt = (
        select(Task)
        .where(Task.project_id == project_id)
        .order_by(Task.status.asc(), Task.due_date.asc(), Task.task_id.asc())
    )

    return list(db.execute(stmt).scalars().all())


def _get_latest_risk_analysis(
    db: Session,
    project_id: int,
) -> RiskAnalysis | None:
    stmt = (
        select(RiskAnalysis)
        .where(RiskAnalysis.project_id == project_id)
        .order_by(RiskAnalysis.created_at.desc(), RiskAnalysis.risk_id.desc())
    )

    return db.execute(stmt).scalars().first()


def _get_recent_chat_history(
    db: Session,
    project_id: int,
    limit: int = 10,
) -> list[ChatMessage]:
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.project_id == project_id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.message_id.desc())
        .limit(limit)
    )

    messages = list(db.execute(stmt).scalars().all())

    return list(reversed(messages))


def _calculate_task_summary(tasks: list[Task]) -> dict[str, Any]:
    total_tasks = len(tasks)
    completed_tasks = len([task for task in tasks if task.status == "completed"])
    blocked_tasks = len([task for task in tasks if task.status == "blocked"])
    in_progress_tasks = len([task for task in tasks if task.status == "in_progress"])
    todo_tasks = len([task for task in tasks if task.status == "todo"])

    now = datetime.now(timezone.utc)

    overdue_tasks = [
        task
        for task in tasks
        if task.status != "completed"
        and task.due_date is not None
        and _to_utc(task.due_date) < now
    ]

    completion_percentage = (
        round((completed_tasks / total_tasks) * 100, 2)
        if total_tasks > 0
        else 0.0
    )

    remaining_estimated_hours = sum(
        float(task.estimated_hours or 0)
        for task in tasks
        if task.status != "completed"
    )

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "blocked_tasks": blocked_tasks,
        "in_progress_tasks": in_progress_tasks,
        "todo_tasks": todo_tasks,
        "overdue_tasks": len(overdue_tasks),
        "completion_percentage": completion_percentage,
        "remaining_estimated_hours": round(remaining_estimated_hours, 2),
    }


def _get_next_tasks(tasks: list[Task], limit: int = 3) -> list[Task]:
    incomplete_tasks = [
        task
        for task in tasks
        if task.status != "completed"
    ]

    priority_rank = {
        "high": 0,
        "medium": 1,
        "low": 2,
    }

    return sorted(
        incomplete_tasks,
        key=lambda task: (
            priority_rank.get(task.priority, 3),
            _to_utc(task.due_date)
            if task.due_date
            else datetime.max.replace(tzinfo=timezone.utc),
            task.task_id,
        ),
    )[:limit]


def _build_next_task_lines(tasks: list[Task]) -> list[str]:
    lines: list[str] = []

    for task in tasks:
        due_text = (
            _to_utc(task.due_date).date().isoformat()
            if task.due_date is not None
            else "no due date"
        )

        lines.append(
            f"- {task.title} | priority: {task.priority} | status: {task.status} | due: {due_text}"
        )

    return lines


def _format_task_for_prompt(task: Task) -> str:
    due_text = (
        _to_utc(task.due_date).date().isoformat()
        if task.due_date is not None
        else "no due date"
    )

    return (
        f"- title: {task.title}\n"
        f"  status: {task.status}\n"
        f"  priority: {task.priority}\n"
        f"  due_date: {due_text}\n"
        f"  estimated_hours: {float(task.estimated_hours or 0)}"
    )


def _format_chat_history_for_prompt(messages: list[ChatMessage]) -> str:
    if not messages:
        return "No previous chat messages."

    lines: list[str] = []

    for message in messages:
        role = "User" if message.sender_type == "user" else "Assistant"
        lines.append(f"{role}: {message.message}")

    return "\n".join(lines)


def _build_llm_prompt(
    project: Project,
    current_user: User,
    user_message: str,
    tasks: list[Task],
    latest_risk: RiskAnalysis | None,
    recent_messages: list[ChatMessage],
) -> str:
    task_summary = _calculate_task_summary(tasks)

    deadline_text = _to_utc(project.deadline).date().isoformat()

    task_lines = "\n".join(
        _format_task_for_prompt(task)
        for task in tasks[:25]
    )

    if not task_lines:
        task_lines = "No tasks found for this project."

    if latest_risk is None:
        risk_context = "No saved risk analysis exists for this project."
    else:
        risk_context = (
            f"risk_level: {latest_risk.risk_level}\n"
            f"predicted_delay_days: {latest_risk.predicted_delay_days}\n"
            f"reason: {latest_risk.reason}\n"
            f"recommendation: {latest_risk.recommendation}"
        )

    chat_history = _format_chat_history_for_prompt(recent_messages)

    return f"""
You are Planora AI, a project planning and productivity assistant inside the Planora app.

Your job:
- Answer naturally like a helpful assistant.
- Use the project context below.
- Give practical next steps.
- Be clear and concise.
- If the user greets you, greet them back and explain what you can help with.
- If the user asks about progress, risk, deadline, or next tasks, use the project data.
- Do not invent database records.
- Do not mention hidden implementation details.
- Do not expose secrets, tokens, passwords, hashes, or unrelated users.
- If information is missing, say what is missing and suggest the next action.

Current user:
- user_id: {current_user.user_id}
- full_name: {current_user.full_name}

Project:
- project_id: {project.project_id}
- title: {project.title}
- description: {project.description or "No description"}
- project_type: {project.project_type}
- status: {project.status}
- deadline: {deadline_text}

Task summary:
- total_tasks: {task_summary["total_tasks"]}
- completed_tasks: {task_summary["completed_tasks"]}
- in_progress_tasks: {task_summary["in_progress_tasks"]}
- todo_tasks: {task_summary["todo_tasks"]}
- blocked_tasks: {task_summary["blocked_tasks"]}
- overdue_tasks: {task_summary["overdue_tasks"]}
- completion_percentage: {task_summary["completion_percentage"]}
- remaining_estimated_hours: {task_summary["remaining_estimated_hours"]}

Latest risk analysis:
{risk_context}

Tasks:
{task_lines}

Recent chat history:
{chat_history}

User message:
{user_message}

Reply as Planora AI:
""".strip()


def _build_local_rule_based_reply(
    project: Project,
    user_message: str,
    tasks: list[Task],
    latest_risk: RiskAnalysis | None,
) -> tuple[str, dict[str, Any]]:
    lowered_message = user_message.lower()
    task_summary = _calculate_task_summary(tasks)
    next_tasks = _get_next_tasks(tasks)

    context: dict[str, Any] = {
        "source": "local_rule_based_chat_v1",
        "fallback_used": True,
        "project_id": project.project_id,
        "project_title": project.title,
        "project_status": project.status,
        "project_type": project.project_type,
        "task_summary": task_summary,
        "latest_risk": None,
    }

    if latest_risk is not None:
        context["latest_risk"] = {
            "risk_level": latest_risk.risk_level,
            "predicted_delay_days": latest_risk.predicted_delay_days,
            "reason": latest_risk.reason,
            "recommendation": latest_risk.recommendation,
            "created_at": latest_risk.created_at.isoformat(),
        }

    next_task_lines = _build_next_task_lines(next_tasks)

    if any(word in lowered_message for word in ["hello", "hi", "hey", "how are you"]):
        reply = (
            f"Hello! I am your Planora project assistant. "
            f"I checked '{project.title}' and I can help with progress, next tasks, risks, deadlines, and scheduling."
        )

        return reply, context

    if any(word in lowered_message for word in ["risk", "delay", "late", "behind", "danger"]):
        if latest_risk is None:
            reply = (
                f"For '{project.title}', I do not see a saved risk analysis yet. "
                f"Current progress is {task_summary['completion_percentage']}%. "
                f"There are {task_summary['overdue_tasks']} overdue tasks and "
                f"{task_summary['blocked_tasks']} blocked tasks. "
                "Generate a risk analysis first if you want a stronger delay prediction."
            )
        else:
            reply = (
                f"Latest risk for '{project.title}' is {latest_risk.risk_level.upper()}. "
                f"Predicted delay: {latest_risk.predicted_delay_days} day(s). "
                f"Reason: {latest_risk.reason} "
                f"Recommendation: {latest_risk.recommendation}"
            )

    elif any(word in lowered_message for word in ["next", "start", "task", "todo", "priority"]):
        if not next_task_lines:
            reply = (
                f"'{project.title}' has no remaining incomplete tasks. "
                "The next step is to review the project, finalize documentation, and mark the project completed if everything is done."
            )
        else:
            reply = (
                f"Best next tasks for '{project.title}':\n"
                + "\n".join(next_task_lines)
                + "\nFocus on high-priority or overdue work first."
            )

    elif any(word in lowered_message for word in ["progress", "status", "summary", "overview"]):
        reply = (
            f"Project summary for '{project.title}': "
            f"{task_summary['completed_tasks']}/{task_summary['total_tasks']} tasks completed "
            f"({task_summary['completion_percentage']}%). "
            f"Todo: {task_summary['todo_tasks']}, in progress: {task_summary['in_progress_tasks']}, "
            f"blocked: {task_summary['blocked_tasks']}, overdue: {task_summary['overdue_tasks']}. "
            f"Remaining estimated work: {task_summary['remaining_estimated_hours']} hour(s)."
        )

    elif any(word in lowered_message for word in ["schedule", "deadline", "plan", "time"]):
        deadline_text = _to_utc(project.deadline).date().isoformat()

        reply = (
            f"'{project.title}' deadline is {deadline_text}. "
            f"You still have {task_summary['total_tasks'] - task_summary['completed_tasks']} incomplete task(s), "
            f"with around {task_summary['remaining_estimated_hours']} estimated hour(s) remaining. "
            "Use smart scheduling if due dates need to be reorganized."
        )

    else:
        reply = (
            f"I checked '{project.title}'. "
            f"Progress is {task_summary['completion_percentage']}%, "
            f"with {task_summary['blocked_tasks']} blocked task(s) and "
            f"{task_summary['overdue_tasks']} overdue task(s). "
        )

        if next_task_lines:
            reply += "Recommended next focus:\n" + "\n".join(next_task_lines)
        else:
            reply += "No incomplete tasks were found."

    return reply, context


def create_ai_chat_exchange(
    db: Session,
    project: Project,
    current_user: User,
    chat_data: AIChatRequest,
) -> tuple[ChatMessage, ChatMessage, dict[str, Any]]:
    tasks = _get_project_tasks(
        db=db,
        project_id=project.project_id,
    )

    latest_risk = _get_latest_risk_analysis(
        db=db,
        project_id=project.project_id,
    )

    recent_messages = _get_recent_chat_history(
        db=db,
        project_id=project.project_id,
    )

    fallback_reply, assistant_context = _build_local_rule_based_reply(
        project=project,
        user_message=chat_data.message,
        tasks=tasks,
        latest_risk=latest_risk,
    )

    llm_prompt = _build_llm_prompt(
        project=project,
        current_user=current_user,
        user_message=chat_data.message,
        tasks=tasks,
        latest_risk=latest_risk,
        recent_messages=recent_messages,
    )

    provider_reply = generate_ai_reply_from_provider(llm_prompt)

    if provider_reply is not None:
        ai_reply = provider_reply
        assistant_context = {
            **assistant_context,
            "source": "gemini_llm_v1",
            "fallback_used": False,
            "provider": "gemini",
        }
    else:
        ai_reply = fallback_reply

    user_message = ChatMessage(
        sender_id=current_user.user_id,
        project_id=project.project_id,
        message=chat_data.message,
        sender_type="user",
    )

    db.add(user_message)
    db.flush()

    ai_message = ChatMessage(
        sender_id=None,
        project_id=project.project_id,
        message=ai_reply,
        sender_type="ai",
    )

    db.add(ai_message)
    db.commit()

    db.refresh(user_message)
    db.refresh(ai_message)

    return user_message, ai_message, assistant_context


def get_project_chat_history(
    db: Session,
    project: Project,
    limit: int = 50,
    offset: int = 0,
) -> list[ChatMessage]:
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.project_id == project.project_id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.message_id.asc())
        .limit(limit)
        .offset(offset)
    )

    return list(db.execute(stmt).scalars().all())