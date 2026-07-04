from __future__ import annotations

import json
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

def _normalize_message(value: str) -> str:
    return " ".join(value.lower().strip().split())

def _contains_any(value: str, keywords: list[str]) -> bool:
    return any(keyword in value for keyword in keywords)

def _is_greeting_message(user_message: str) -> bool:
    message = _normalize_message(user_message)

    if not message:
        return False

    exact_greetings = {
        "hi",
        "hello",
        "hey",
        "hi planora",
        "hello planora",
        "hey planora",
        "good morning",
        "good afternoon",
        "good evening",
        "how are you",
        "thanks",
        "thank you",
    }

    if message in exact_greetings:
        return True

    greeting_prefixes = (
        "hello ",
        "hi ",
        "hey ",
        "good morning ",
        "good afternoon ",
        "good evening ",
    )

    return message.startswith(greeting_prefixes) and len(message.split()) <= 8

def _is_project_related_message(user_message: str) -> bool:
    """
    Keeps Planora AI scoped to the current project.

    This guard blocks general chatbot behavior before the request reaches
    Gemini or the local rule-based assistant.

    Normal greetings are allowed, because the assistant should be able to
    greet the user and explain what it can help with.
    """
    message = _normalize_message(user_message)

    if not message:
        return False

    greeting_keywords = [
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
        "how are you",
        "thanks",
        "thank you",
    ]

    off_topic_keywords = [
        "weather",
        "temperature",
        "forecast",
        "rain",
        "snow",
        "storm",
        "news",
        "politics",
        "president",
        "minister",
        "election",
        "sports",
        "football",
        "basketball",
        "tennis",
        "match",
        "movie",
        "movies",
        "series",
        "song",
        "songs",
        "lyrics",
        "celebrity",
        "recipe",
        "cook",
        "cooking",
        "restaurant",
        "stock",
        "stocks",
        "crypto",
        "bitcoin",
        "currency",
        "exchange rate",
        "medical",
        "doctor",
        "medicine",
        "legal",
        "lawyer",
        "joke",
        "poem",
        "story",
        "translate",
        "history",
        "geography",
        "capital of",
        "homework",
        "essay",
        "solve this math",
    ]

    project_keywords = [
        "planora",
        "project",
        "task",
        "tasks",
        "todo",
        "to do",
        "priority",
        "priorities",
        "deadline",
        "due date",
        "due",
        "overdue",
        "schedule",
        "scheduling",
        "plan",
        "planning",
        "milestone",
        "progress",
        "status",
        "summary",
        "overview",
        "risk",
        "delay",
        "delayed",
        "late",
        "behind",
        "blocked",
        "complete",
        "completed",
        "completion",
        "finish",
        "finished",
        "workload",
        "productivity",
        "team",
        "member",
        "members",
        "assign",
        "assigned",
        "assignee",
        "comment",
        "comments",
        "attachment",
        "attachments",
        "file",
        "files",
        "notification",
        "notifications",
        "reminder",
        "reminders",
        "report",
        "reports",
        "export",
        "timeline",
        "smart schedule",
        "risk analysis",
        "scope",
        "product scope",
        "criteria",
        "success criteria",
        "meaning",
        "means",
        "define",
        "definition",
        "explain",
        "understand",
        "stuck",
        "lost",
    ]

    project_question_patterns = [
        "what should i do",
        "what do i do",
        "what now",
        "where should i start",
        "where do i start",
        "what is next",
        "what's next",
        "next step",
        "next steps",
        "am i behind",
        "are we behind",
        "is this on track",
        "are we on track",
        "can i finish",
        "can we finish",
        "will i finish",
        "will we finish",
        "help me organize",
        "help me prioritize",
        "help me plan",
        "what can you help",
        "what can you do",
        "what does",
        "what is",
        "what are",
        "what means",
        "what do you mean",
        "meaning of",
        "means what",
        "i do not understand",
        "i don't understand",
        "i dont understand",
        "i do not know",
        "i don't know",
        "i dont know",
        "idk",
        "i am lost",
        "i'm lost",
        "i am stuck",
        "i'm stuck",
        "break it down",
        "make it simpler",
        "explain this",
        "explain the task",
        "how do i complete",
        "how should i complete",
    ]

    generic_project_assistant_patterns = [
        "help me",
        "i need help",
        "give me advice",
        "suggest",
        "recommend",
        "explain",
    ]

    has_greeting = _is_greeting_message(user_message)
    has_off_topic_keyword = _contains_any(message, off_topic_keywords)
    has_project_keyword = _contains_any(message, project_keywords)
    has_project_question_pattern = _contains_any(message, project_question_patterns)
    has_generic_project_assistant_pattern = _contains_any(
        message,
        generic_project_assistant_patterns,
    )

    if has_off_topic_keyword and not has_project_keyword and not has_project_question_pattern:
        return False

    if has_project_keyword:
        return True

    if has_project_question_pattern:
        return True

    if has_greeting and not has_off_topic_keyword:
        return True

    if has_generic_project_assistant_pattern and not has_off_topic_keyword:
        return True

    return False

def _build_out_of_scope_reply(project: Project) -> tuple[str, dict[str, Any]]:
    reply = (
        f"I can only help with the Planora project '{project.title}'. "
        "Ask me about project progress, tasks, priorities, deadlines, risks, "
        "scheduling, team workload, or what to work on next."
    )

    context: dict[str, Any] = {
        "source": "project_scope_guard_v1",
        "fallback_used": True,
        "provider_skipped": True,
        "scope": "out_of_scope",
        "project_id": project.project_id,
        "project_title": project.title,
        "project_status": project.status,
        "project_type": project.project_type,
    }

    return reply, context

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
            f"- {task.title} | priority: {task.priority} | "
            f"status: {task.status} | due: {due_text}"
        )

    return lines

def _is_explanation_request(user_message: str) -> bool:
    message = _normalize_message(user_message)

    explanation_patterns = [
        "what does",
        "what is",
        "what are",
        "what means",
        "what do you mean",
        "meaning of",
        "means what",
        "explain",
        "define",
        "definition",
        "understand",
        "i do not understand",
        "i don't understand",
        "i dont understand",
        "i do not know",
        "i don't know",
        "i dont know",
        "idk",
        "lost",
        "stuck",
        "break it down",
        "make it simpler",
        "how do i complete",
        "how should i complete",
        "success criteria",
        "product scope",
        "scope",
    ]

    return _contains_any(message, explanation_patterns)

def _should_use_deterministic_project_reply(user_message: str) -> bool:
    message = _normalize_message(user_message)

    deterministic_patterns = [
        "what should i do",
        "what do i do",
        "what to do",
        "what task",
        "what tasks",
        "what task do i have",
        "first task",
        "next task",
        "next tasks",
        "todo",
        "to do",
        "priority",
        "priorities",
        "progress",
        "status",
        "summary",
        "overview",
        "risk",
        "deadline",
        "schedule",
        "team workload",
        "workload",
    ]

    return _is_explanation_request(user_message) or _contains_any(
        message,
        deterministic_patterns,
    )

def _find_referenced_task(user_message: str, tasks: list[Task]) -> Task | None:
    message = _normalize_message(user_message)

    if not tasks:
        return None

    stop_words = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "what",
        "does",
        "mean",
        "means",
        "explain",
        "define",
        "task",
        "project",
    }

    best_task: Task | None = None
    best_score = 0

    for task in tasks:
        title = _normalize_message(task.title)

        if title and title in message:
            return task

        title_words = [
            word
            for word in title.split()
            if len(word) >= 4 and word not in stop_words
        ]

        score = sum(1 for word in title_words if word in message)

        if score > best_score:
            best_score = score
            best_task = task

    if best_score >= 2:
        return best_task

    if any(
        phrase in message
        for phrase in ["this task", "the task", "first task", "current task"]
    ):
        next_tasks = _get_next_tasks(tasks, limit=1)

        if next_tasks:
            return next_tasks[0]

    return None

def _build_explanation_reply(
    project: Project,
    user_message: str,
    tasks: list[Task],
) -> str:
    message = _normalize_message(user_message)
    referenced_task = _find_referenced_task(user_message, tasks)

    if "product scope" in message or (
        "scope" in message and "success criteria" in message
    ):
        return (
            f"For '{project.title}', product scope means deciding exactly what "
            "your project will include at the start and what it will not include yet.\n\n"
            "Success criteria means how you will know the task is finished.\n\n"
            "Example:\n"
            "1. Choose the first products or services you will offer.\n"
            "2. Choose the target customer.\n"
            "3. Decide your price range or quality level.\n"
            "4. Write a clear result, like: I selected 3 products, one target "
            "customer, and a first sales channel.\n\n"
            "Next small action: write the first 3 products or services you want "
            "to start with."
        )

    if "success criteria" in message or "criteria" in message:
        return (
            "Success criteria means the clear proof that a task is complete.\n\n"
            f"For '{project.title}', do not leave the task vague. Write what the "
            "finished result should look like.\n\n"
            "Example success criteria:\n"
            "1. The target customer is written down.\n"
            "2. The first products or services are selected.\n"
            "3. The price range is decided.\n"
            "4. The next task can start without confusion."
        )

    if (
        "idk" in message
        or "stuck" in message
        or "lost" in message
        or "i dont know" in message
        or "i don't know" in message
    ):
        next_tasks = _get_next_tasks(tasks, limit=1)

        if next_tasks:
            task = next_tasks[0]

            return (
                f"No problem. Let’s make '{project.title}' simple.\n\n"
                f"Start with this task: {task.title}\n\n"
                "Do it in 3 small steps:\n"
                "1. Read the task title and write what result you need.\n"
                "2. Spend 20-30 minutes collecting the basic information.\n"
                "3. Write one small output, even if it is not perfect.\n\n"
                "After that, come back and ask me to check or improve it."
            )

        return (
            f"No problem. For '{project.title}', start with 3 simple decisions:\n"
            "1. What exactly are you trying to create or launch?\n"
            "2. Who is it for?\n"
            "3. What is the first small result you can finish today?"
        )

    if referenced_task is not None:
        description = (referenced_task.description or "").strip()

        reply = (
            f"The task '{referenced_task.title}' means you need to turn this part "
            "of the project into a clear, doable result.\n\n"
        )

        if description:
            reply += f"Task context: {description}\n\n"

        reply += (
            "How to do it:\n"
            "1. Write what the final output should be.\n"
            "2. Break it into 2-3 small actions.\n"
            "3. Finish the smallest action first.\n"
            "4. Mark the task complete only when the output is clear.\n\n"
            "Next small action: write one sentence describing what this task should "
            "produce."
        )

        return reply

    return (
        f"I can help explain that for '{project.title}'.\n\n"
        "In Planora, a task should tell you:\n"
        "1. What to do.\n"
        "2. Why it matters for the project.\n"
        "3. What result proves it is done.\n\n"
        "Ask me about any task title, and I will explain it in simpler steps."
    )

def _build_team_workload_reply(
    project: Project,
    tasks: list[Task],
) -> str:
    if project.project_type == "personal":
        assigned_tasks = len(
            [
                task
                for task in tasks
                if getattr(task, "assigned_to", None) is not None
                and task.status != "completed"
            ]
        )

        unassigned_tasks = len(
            [
                task
                for task in tasks
                if getattr(task, "assigned_to", None) is None
                and task.status != "completed"
            ]
        )

        return (
            f"'{project.title}' is currently a personal project, so there is no "
            "team workload to balance yet.\n\n"
            f"Open tasks assigned to someone: {assigned_tasks}\n"
            f"Open unassigned tasks: {unassigned_tasks}\n\n"
            "If you invite collaborators later and assign tasks to them, I can "
            "summarize who has too much work, who is free, and which tasks are unassigned."
        )

    workload: dict[int | str, dict[str, int]] = {}
    unassigned = 0

    for task in tasks:
        if task.status == "completed":
            continue

        assignee_id = getattr(task, "assigned_to", None)

        if assignee_id is None:
            unassigned += 1
            continue

        if assignee_id not in workload:
            workload[assignee_id] = {
                "total": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
            }

        workload[assignee_id]["total"] += 1

        if task.priority in ["high", "medium", "low"]:
            workload[assignee_id][task.priority] += 1

    if not workload and unassigned == 0:
        return (
            f"'{project.title}' has no open assigned tasks right now, so there is "
            "no team workload to balance."
        )

    lines = [
        f"Team workload for '{project.title}':",
    ]

    for assignee_id, counts in sorted(
        workload.items(),
        key=lambda item: (-item[1]["total"], str(item[0])),
    ):
        lines.append(
            f"- User {assignee_id}: {counts['total']} open task(s), "
            f"{counts['high']} high priority"
        )

    lines.append(f"- Unassigned open tasks: {unassigned}")

    overloaded = [
        assignee_id
        for assignee_id, counts in workload.items()
        if counts["total"] >= 5 or counts["high"] >= 3
    ]

    if overloaded:
        lines.append(
            "Recommendation: rebalance high-priority tasks from the busiest "
            "member(s) or assign unassigned tasks to members with fewer open tasks."
        )
    else:
        lines.append(
            "Recommendation: workload looks manageable. Keep high-priority tasks "
            "visible and assign unassigned work before the deadline."
        )

    return "\n".join(lines)

def _format_task_for_prompt(task: Task) -> str:
    due_text = (
        _to_utc(task.due_date).date().isoformat()
        if task.due_date is not None
        else "no due date"
    )

    start_text = (
        _to_utc(task.start_date).date().isoformat()
        if getattr(task, "start_date", None) is not None
        else "no start date"
    )

    description = " ".join((task.description or "").strip().split())

    if len(description) > 600:
        description = f"{description[:597].rstrip()}..."

    assignee = getattr(task, "assigned_to", None)

    return (
        f"- task_id: {task.task_id}\n"
        f"  title: {task.title}\n"
        f"  description: {description or 'No description'}\n"
        f"  status: {task.status}\n"
        f"  priority: {task.priority}\n"
        f"  assigned_to: {assignee or 'unassigned'}\n"
        f"  start_date: {start_text}\n"
        f"  due_date: {due_text}\n"
        f"  estimated_hours: {float(task.estimated_hours or 0)}\n"
        f"  actual_hours: {float(task.actual_hours or 0)}"
    )

def _format_chat_history_for_prompt(messages: list[ChatMessage]) -> str:
    if not messages:
        return "No previous chat messages."

    lines: list[str] = []

    for message in messages:
        # Never feed an old planner JSON response back into the chat model.
        # That old content can cause the model to continue replying with plans.
        if message.sender_type != "user" and _looks_like_planner_json(message.message):
            continue

        role = "User" if message.sender_type == "user" else "Assistant"
        lines.append(f"{role}: {message.message}")

    if not lines:
        return "No usable previous chat messages."

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
- Only answer questions related to the current Planora project.
- Use the project context below.
- Give practical next steps.
- Be clear and concise.
- If the user greets you, greet them back and explain what you can help with.
- If the user asks about progress, risk, deadline, scheduling, workload, or next tasks, use the project data.
- If the user asks what a task, product scope, success criteria, or project term means, explain it simply with an example and one next action.
- If the user asks about anything unrelated to this project, do not answer that topic.
- For unrelated questions, say you can only help with this Planora project and suggest project-related topics.
- Do not answer weather, news, sports, politics, entertainment, trivia, homework, medical, legal, financial, or unrelated coding questions.
- Do not invent database records.
- Do not mention hidden implementation details.
- Do not expose secrets, tokens, passwords, hashes, or unrelated users.
- If information is missing, say what is missing and suggest the next action.
- Answer the user's exact question first.
- Never give generic productivity advice when project data is available.
- Refer to real task titles from the supplied task list.
- When recommending work, choose the most useful exact task and explain why.
- If the user asks what to do next, give one main task first, not a long unfocused list.
- Break difficult work into small, concrete actions.
- Clearly distinguish project facts from your recommendations.
- Use short headings and bullets when they improve readability.
- End with a practical next action when appropriate.
- Do not repeatedly introduce yourself in every reply.
- Use the recent conversation so the reply feels continuous.

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
    next_task_lines = _build_next_task_lines(next_tasks)

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

    if any(word in lowered_message for word in ["workload", "team workload"]):
        context["intent"] = "team_workload"
        reply = _build_team_workload_reply(project=project, tasks=tasks)

        return reply, context

    if _is_explanation_request(user_message):
        context["intent"] = "explanation"
        reply = _build_explanation_reply(
            project=project,
            user_message=user_message,
            tasks=tasks,
        )

        return reply, context

    if _is_greeting_message(user_message):
        context["intent"] = "greeting"
        reply = (
            f"Hello! I am your Planora project assistant for '{project.title}'. "
            "I can help you choose the next task, explain any task, check progress "
            "and deadline risk, handle blockers, or improve the schedule."
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
                "The next step is to review the project, finalize documentation, "
                "and mark the project completed if everything is done."
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
            f"Todo: {task_summary['todo_tasks']}, "
            f"in progress: {task_summary['in_progress_tasks']}, "
            f"blocked: {task_summary['blocked_tasks']}, "
            f"overdue: {task_summary['overdue_tasks']}. "
            f"Remaining estimated work: {task_summary['remaining_estimated_hours']} hour(s)."
        )

    elif any(word in lowered_message for word in ["schedule", "deadline", "plan", "time"]):
        deadline_text = _to_utc(project.deadline).date().isoformat()

        reply = (
            f"'{project.title}' deadline is {deadline_text}. "
            f"You still have {task_summary['total_tasks'] - task_summary['completed_tasks']} "
            f"incomplete task(s), with around "
            f"{task_summary['remaining_estimated_hours']} estimated hour(s) remaining. "
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

def _save_chat_exchange(
    db: Session,
    project: Project,
    current_user: User,
    user_message_text: str,
    ai_reply: str,
    assistant_context: dict[str, Any],
) -> tuple[ChatMessage, ChatMessage, dict[str, Any]]:
    user_message = ChatMessage(
        sender_id=current_user.user_id,
        project_id=project.project_id,
        message=user_message_text,
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

def _build_follow_up_suggestions(
    project: Project,
    tasks: list[Task],
    latest_risk: RiskAnalysis | None,
) -> list[str]:
    summary = _calculate_task_summary(tasks)
    suggestions: list[str] = []

    if summary["blocked_tasks"] > 0:
        suggestions.append("How can I unblock the blocked tasks?")
    elif summary["overdue_tasks"] > 0:
        suggestions.append("Which overdue task should I handle first?")
    elif summary["in_progress_tasks"] > 0:
        suggestions.append("What should I focus on next?")
    else:
        suggestions.append("What should I do first?")

    if latest_risk is not None:
        suggestions.append("Explain the current project risk")
    else:
        suggestions.append("Am I likely to miss the deadline?")

    suggestions.append("Make me a realistic plan for this week")

    if project.project_type == "team":
        suggestions.append("How is the team workload?")
    else:
        suggestions.append("Break my next task into small steps")

    unique_suggestions: list[str] = []

    for suggestion in suggestions:
        if suggestion not in unique_suggestions:
            unique_suggestions.append(suggestion)

    return unique_suggestions[:4]

def _extract_json_object(value: str | None) -> dict[str, Any] | None:
    if value is None:
        return None

    cleaned = value.strip()

    if not cleaned:
        return None

    # Gemini may wrap JSON in a Markdown code fence.
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        if lines:
            lines = lines[1:]

        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]

        cleaned = "\n".join(lines).strip()

    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")

    if first_brace == -1 or last_brace <= first_brace:
        return None

    candidate = cleaned[first_brace : last_brace + 1]

    try:
        payload = json.loads(candidate)
    except (json.JSONDecodeError, TypeError):
        return None

    return payload if isinstance(payload, dict) else None

def _looks_like_planner_json(value: str | None) -> bool:
    payload = _extract_json_object(value)

    if payload is None:
        return False

    planner_keys = {
        "domain",
        "summary",
        "tasks",
        "milestones",
        "risks",
        "recommendations",
    }

    matching_keys = planner_keys.intersection(payload.keys())

    return (
        isinstance(payload.get("tasks"), list)
        and len(matching_keys) >= 3
    )

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

    suggested_prompts = _build_follow_up_suggestions(
        project=project,
        tasks=tasks,
        latest_risk=latest_risk,
    )

    if not _is_project_related_message(chat_data.message):
        ai_reply, assistant_context = _build_out_of_scope_reply(project)

        assistant_context = {
            **assistant_context,
            "suggested_prompts": suggested_prompts,
        }

        return _save_chat_exchange(
            db=db,
            project=project,
            current_user=current_user,
            user_message_text=chat_data.message,
            ai_reply=ai_reply,
            assistant_context=assistant_context,
        )

    fallback_reply, assistant_context = _build_local_rule_based_reply(
        project=project,
        user_message=chat_data.message,
        tasks=tasks,
        latest_risk=latest_risk,
    )

    # Greetings do not need an external provider. Handling them locally prevents
    # a planning-model fallback from ever appearing as raw JSON in the chat.
    if _is_greeting_message(chat_data.message):
        assistant_context = {
            **assistant_context,
            "source": "local_greeting_v2",
            "fallback_used": False,
            "provider": None,
            "provider_skipped": True,
            "provider_skip_reason": "simple_greeting",
            "suggested_prompts": suggested_prompts,
        }

        return _save_chat_exchange(
            db=db,
            project=project,
            current_user=current_user,
            user_message_text=chat_data.message,
            ai_reply=fallback_reply,
            assistant_context=assistant_context,
        )

    recent_messages = _get_recent_chat_history(
        db=db,
        project_id=project.project_id,
        limit=14,
    )

    llm_prompt = _build_llm_prompt(
        project=project,
        current_user=current_user,
        user_message=chat_data.message,
        tasks=tasks,
        latest_risk=latest_risk,
        recent_messages=recent_messages,
    )

    # Chat must never use the local project-plan generator as a provider fallback.
    # The chat service already has its own safe, human-readable fallback_reply.
    provider_reply = generate_ai_reply_from_provider(
        llm_prompt,
        use_local_fallback=False,
    )

    if provider_reply is not None:
        provider_reply = provider_reply.strip()

    if not provider_reply or _looks_like_planner_json(provider_reply):
        provider_reply = None

    if provider_reply is not None:
        ai_reply = provider_reply

        assistant_context = {
            **assistant_context,
            "source": "gemini_llm_v2",
            "fallback_used": False,
            "provider": "gemini",
            "suggested_prompts": suggested_prompts,
        }
    else:
        ai_reply = fallback_reply

        assistant_context = {
            **assistant_context,
            "source": "local_rule_based_chat_v2",
            "fallback_used": True,
            "provider": None,
            "suggested_prompts": suggested_prompts,
        }

    return _save_chat_exchange(
        db=db,
        project=project,
        current_user=current_user,
        user_message_text=chat_data.message,
        ai_reply=ai_reply,
        assistant_context=assistant_context,
    )

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

    messages = list(db.execute(stmt).scalars().all())

    return [
        message
        for message in messages
        if message.sender_type == "user"
        or not _looks_like_planner_json(message.message)
    ]