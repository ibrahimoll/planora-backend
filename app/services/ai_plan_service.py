from __future__ import annotations

import json
import inspect
import logging
import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_plan import AIPlan
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.activity_log_schema import ActivityLogEventType
from app.schemas.ai_plan_schema import (
    AIPlanAcceptPreviewRequest,
    AIPlanAcceptPreviewResponse,
    AIPlanGenerateRequest,
    AIPlanGenerateResponse,
    AIPlanGeneratedTaskResponse,
    AIPlanPreviewRequest,
    AIPlanPreviewResponse,
    AIPlanPreviewTaskResponse,
)
from app.schemas.task_schema import TaskStatus
from app.services.activity_log_service import create_activity_log
from app.services.ai_provider_service import (
    generate_ai_reply_from_provider,
    generate_local_planner_reply,
)


INSTRUCTION_PREFIXES = (
    "create a complete planora project plan",
    "project type:",
    "deadline:",
    "available hours per week:",
    "preferred task count:",
    "create tasks that directly depend",
    "do not suggest extreme physical asset tasks",
    "return a practical plan",
)

GENERIC_TASK_TITLE_PATTERNS = (
    r"^\s*research\s*$",
    r"^\s*planning\s*$",
    r"^\s*plan\s+project\s*$",
    r"^\s*analysis\s*$",
    r"^\s*strategy\s*$",
    r"^\s*preparation\s*$",
    r"^\s*review\s*$",
    r"^\s*start\s*$",
    r"^\s*improve\s*$",
    r"^\s*finish\s+project\s*$",
    r"^\s*work\s+on\s+.+$",
    r"^\s*complete\s+project\s+step\s+\d+\s*$",
)

ACTION_VERBS = {
    "add",
    "adjust",
    "analyze",
    "ask",
    "build",
    "celebrate",
    "choose",
    "collect",
    "compare",
    "complete",
    "confirm",
    "contact",
    "create",
    "define",
    "draft",
    "estimate",
    "evaluate",
    "find",
    "fix",
    "gather",
    "identify",
    "increase",
    "improve",
    "list",
    "log",
    "make",
    "map",
    "measure",
    "pick",
    "plan",
    "practice",
    "prepare",
    "prioritize",
    "publish",
    "remove",
    "review",
    "schedule",
    "send",
    "set",
    "share",
    "sketch",
    "split",
    "submit",
    "take",
    "test",
    "track",
    "validate",
    "write",
}

SMART_DESCRIPTION_SECTIONS = (
    "goal:",
    "steps:",
    "deliverable:",
    "done when:",
)

SMART_DESCRIPTION_BENEFIT_SECTIONS = (
    "customer benefit:",
    "why it matters:",
    "benefit:",
)

QUALITY_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "my",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "their",
    "this",
    "to",
    "use",
    "user",
    "users",
    "want",
    "with",
    "you",
    "your",
}

ROBOTIC_DESCRIPTION_FRAGMENTS = (
    "write what this task means",
    "list the concrete items",
    "create the smallest usable output",
    "remove anything that belongs to a later version",
    "check that the output can be used directly",
    "understand what this task requires",
    "complete the smallest useful version",
    "review the result before moving forward",
)

AI_PLANNING_UNAVAILABLE_MESSAGE = (
    "AI planning is unavailable right now. Please try again."
)

PLAN_ALREADY_COVERS_MESSAGE = "This plan already covers the main steps."

logger = logging.getLogger(__name__)


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _build_due_dates(project: Project, task_count: int) -> list[datetime]:
    now = datetime.now(timezone.utc)
    deadline = _to_utc(project.deadline)

    if task_count <= 0:
        return []

    if deadline <= now:
        return [deadline for _ in range(task_count)]

    step_seconds = (deadline - now).total_seconds() / (task_count + 1)

    return [
        now + timedelta(seconds=step_seconds * (index + 1))
        for index in range(task_count)
    ]


def _priority_for_index(index: int, task_count: int) -> str:
    if index == 0 or index >= task_count - 2:
        return "high"

    if index % 4 == 0:
        return "low"

    return "medium"


def _estimated_hours_for_index(index: int) -> float:
    estimates = [2.0, 3.0, 4.0, 5.0, 3.5, 4.5]
    return estimates[index % len(estimates)]


def _matches_any_pattern(
    value: str,
    patterns: tuple[str, ...],
) -> bool:
    return any(
        re.search(pattern, value, flags=re.IGNORECASE) is not None
        for pattern in patterns
    )


def _line_is_generation_instruction(line: str) -> bool:
    normalized = line.strip().lower()

    return any(normalized.startswith(prefix) for prefix in INSTRUCTION_PREFIXES)


def _extract_section_lines(
    lines: list[str],
    start_label: str,
    stop_labels: tuple[str, ...],
) -> list[str]:
    collected: list[str] = []
    is_collecting = False

    for raw_line in lines:
        line = raw_line.strip()
        lower = line.lower()

        if lower == start_label:
            is_collecting = True
            continue

        if is_collecting and lower in stop_labels:
            break

        if is_collecting:
            if not line:
                continue

            if _line_is_generation_instruction(line):
                break

            collected.append(line)

    return collected


def _extract_labeled_value(
    lines: list[str],
    label: str,
) -> str | None:
    label_prefix = f"{label.lower()}:"

    for line in lines:
        stripped = line.strip()

        if stripped.lower().startswith(label_prefix):
            value = stripped[len(label_prefix) :].strip()
            return value or None

    return None


def _extract_user_project_context(
    project: Project,
    input_prompt: str,
) -> str:
    lines = input_prompt.splitlines()
    pieces: list[str] = []

    for value in (
        project.title,
        project.description,
        _extract_labeled_value(lines, "Project title"),
        _extract_labeled_value(lines, "Idea"),
    ):
        if value and value.strip():
            pieces.append(value.strip())

    pieces.extend(
        _extract_section_lines(
            lines=lines,
            start_label="project idea and goal:",
            stop_labels=(
                "extra notes, constraints, or preferences:",
                "user idea and context:",
                "requirements, features, constraints, and notes:",
                "requirements and constraints:",
            ),
        )
    )
    pieces.extend(
        _extract_section_lines(
            lines=lines,
            start_label="extra notes, constraints, or preferences:",
            stop_labels=(),
        )
    )
    pieces.extend(
        _extract_section_lines(
            lines=lines,
            start_label="user idea and context:",
            stop_labels=(),
        )
    )
    pieces.extend(
        _extract_section_lines(
            lines=lines,
            start_label="requirements, features, constraints, and notes:",
            stop_labels=(),
        )
    )

    if pieces:
        return "\n".join(dict.fromkeys(pieces))

    cleaned_lines = [
        line.strip()
        for line in lines
        if line.strip() and not _line_is_generation_instruction(line)
    ]

    return "\n".join(
        value
        for value in (project.title, project.description, "\n".join(cleaned_lines))
        if value and value.strip()
    )


def _quality_tokens(value: str) -> set[str]:
    tokens: set[str] = set()

    for token in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9'-]{2,}", value.lower()):
        if token in QUALITY_STOPWORDS:
            continue

        tokens.add(token)

        if len(token) > 4 and token.endswith("s"):
            tokens.add(token[:-1])

    return tokens


def _token_overlap_score(source: str, candidate: str) -> float:
    source_tokens = _quality_tokens(source)
    candidate_tokens = _quality_tokens(candidate)

    if not source_tokens or not candidate_tokens:
        return 0.0

    return len(source_tokens & candidate_tokens) / max(1, min(len(source_tokens), 8))


def _specificity_score(title: str, description: str) -> float:
    combined = f"{title} {description}"
    tokens = _quality_tokens(combined)
    numbers = len(re.findall(r"\b\d+(?:\.\d+)?\b", combined))
    concrete_markers = len(
        re.findall(
            r"\b(list|draft|send|build|record|measure|compare|choose|write|"
            r"schedule|contact|test|collect|publish|track|create)\b",
            combined,
            flags=re.IGNORECASE,
        )
    )

    return min(1.0, (len(tokens) / 18) + (numbers * 0.08) + (concrete_markers * 0.04))


def _actionability_score(description: str) -> float:
    numbered_steps = len(re.findall(r"(?:^|\n)\s*\d+\.", description))
    required_sections = sum(
        section in description.lower()
        for section in SMART_DESCRIPTION_SECTIONS
    )
    has_benefit_section = any(
        section in description.lower()
        for section in SMART_DESCRIPTION_BENEFIT_SECTIONS
    )
    action_words = len(
        re.findall(
            r"\b(write|create|choose|send|test|record|measure|compare|"
            r"build|draft|schedule|contact|collect|publish|track|review)\b",
            description,
            flags=re.IGNORECASE,
        )
    )

    return min(
        1.0,
        (numbered_steps / 3 * 0.45)
        + (
            (required_sections + int(has_benefit_section))
            / (len(SMART_DESCRIPTION_SECTIONS) + 1)
            * 0.35
        )
        + min(action_words, 5) / 5 * 0.2,
    )


def _duplicate_score(
    title: str,
    description: str,
    seen_titles: set[str],
    seen_descriptions: set[str],
    existing_titles: list[str],
    existing_descriptions: list[str],
) -> float:
    all_titles = [*seen_titles, *existing_titles]
    all_descriptions = [*seen_descriptions, *existing_descriptions]

    if any(_task_titles_are_similar(title, existing) for existing in all_titles):
        return 0.0

    if any(_task_descriptions_are_similar(description, existing) for existing in all_descriptions):
        return 0.0

    return 1.0


def _description_restates_title(title: str, description: str) -> bool:
    description_text = _normalize_comparison_text(description)
    title_text = _normalize_comparison_text(title)

    if not title_text or not description_text:
        return True

    stripped = description_text
    for section in (*SMART_DESCRIPTION_SECTIONS, *SMART_DESCRIPTION_BENEFIT_SECTIONS):
        stripped = stripped.replace(section, "")

    stripped = re.sub(r"\d+\.", "", stripped)
    stripped = re.sub(r"\s+", " ", stripped).strip()

    if stripped == title_text:
        return True

    return title_text in stripped and len(stripped) <= len(title_text) + 80


def _contains_robotic_description(description: str) -> bool:
    lowered = description.lower()
    return any(fragment in lowered for fragment in ROBOTIC_DESCRIPTION_FRAGMENTS)


def _classify_planning_domain(project_context: str) -> str:
    lowered = project_context.lower()

    if any(
        keyword in lowered
        for keyword in (
            "pushup",
            "push-up",
            "workout",
            "fitness",
            "exercise",
            "gym",
            "run",
            "running",
            "5k",
            "5 km",
            "muscle",
            "lose weight",
            "weight loss",
            "reps",
            "sets",
            "squat",
            "plank",
        )
    ):
        return "fitness_health"

    if any(
        keyword in lowered
        for keyword in ("study", "learn", "exam", "course", "homework", "quiz")
    ):
        return "study_learning"

    if any(
        keyword in lowered
        for keyword in ("app", "software", "website", "api", "backend", "frontend")
    ):
        return "software_app"

    if any(
        keyword in lowered
        for keyword in ("habit", "routine", "daily", "journal", "sleep", "wake")
    ):
        return "personal_habit"

    return "generic_project"


def _uses_wrong_domain_product_language(
    *,
    project_context: str,
    task_text: str,
) -> bool:
    domain = _classify_planning_domain(project_context)

    if domain not in {"fitness_health", "personal_habit", "study_learning"}:
        return False

    lowered = task_text.lower()
    forbidden_fragments = (
        "features",
        "requirements",
        "mvp",
        "minimum viable",
        "first useful version",
        "first-version",
        "customer benefit",
        "idea goal",
        "user flow",
        "first release",
        "product",
    )

    return any(fragment in lowered for fragment in forbidden_fragments)


def _strip_json_code_fence(value: str) -> str:
    cleaned = value.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").strip()

    elif cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").strip()

    if cleaned.endswith("```"):
        cleaned = cleaned.removesuffix("```").strip()

    return cleaned


def _json_error_summary(error: json.JSONDecodeError) -> str:
    return f"{error.msg} at line {error.lineno} column {error.colno}"


def _extract_json_object(value: str) -> tuple[dict[str, Any] | None, str | None]:
    cleaned = _strip_json_code_fence(value)
    candidates = [cleaned]

    for match in re.finditer(
        r"```(?:json)?\s*(.*?)```",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        fenced = match.group(1).strip()
        if fenced:
            candidates.append(fenced)

    decoder = json.JSONDecoder()
    errors: list[str] = []

    for candidate in dict.fromkeys(candidates):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError as exc:
            errors.append(_json_error_summary(exc))
        else:
            if isinstance(data, dict):
                return data, None

            errors.append(f"decoded {type(data).__name__}, expected object")

        for match in re.finditer(r"{", candidate):
            start_index = match.start()
            fragment = candidate[start_index:]

            try:
                data, _end_index = decoder.raw_decode(fragment)
            except json.JSONDecodeError as exc:
                errors.append(_json_error_summary(exc))
                continue

            if isinstance(data, dict):
                return data, None

            errors.append(f"decoded {type(data).__name__}, expected object")

    return None, (errors[-1] if errors else "no JSON object found")


def _parse_json_object(value: str) -> dict[str, Any] | None:
    data, reason = _extract_json_object(value)

    if data is None:
        logger.warning("AI Planner JSON parse failed. reason=%s", reason)

    return data


def _generate_ai_plan_reply_from_provider(prompt: str) -> str | None:
    try:
        parameters = inspect.signature(generate_ai_reply_from_provider).parameters
    except (TypeError, ValueError):
        parameters = {}

    supports_kwargs = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )
    supports_json_mode = "response_mime_type" in parameters or supports_kwargs
    supports_fallback_flag = "use_local_fallback" in parameters or supports_kwargs

    if supports_json_mode and supports_fallback_flag:
        return generate_ai_reply_from_provider(
            prompt,
            response_mime_type="application/json",
            use_local_fallback=False,
        )

    if supports_json_mode:
        return generate_ai_reply_from_provider(
            prompt,
            response_mime_type="application/json",
        )

    return generate_ai_reply_from_provider(prompt)


def _build_minimum_local_fallback_tasks(
    project: Project,
    input_prompt: str,
    task_count: int,
) -> list[dict[str, Any]]:
    project_context = _extract_user_project_context(
        project=project,
        input_prompt=input_prompt,
    )
    context_phrases = _extract_project_context_phrases(project_context)
    topic = _clean_ai_text_field(
        context_phrases[0] if context_phrases else project.title,
        fallback=project.title,
        max_length=48,
    )
    domain = _classify_planning_domain(project_context)
    due_dates = _build_ai_due_dates(project=project, task_count=task_count)

    if domain == "fitness_health":
        fitness_titles = [
            "Test your current max pushups",
            "Set a safe daily starting volume",
            "Split pushups into manageable sets",
            "Practice correct pushup form",
            "Create a 2-week progression schedule",
            "Add recovery and pain rules",
            "Track reps, sets, and difficulty",
            "Review progress after 14 days",
        ]
        fitness_goals = [
            "Find your safe starting point before increasing daily pushup volume.",
            "Choose a daily rep target that builds consistency without overloading your joints.",
            "Break the daily total into sets you can complete with good form.",
            "Make each rep useful and reduce shoulder, wrist, and lower-back strain.",
            "Move toward the target gradually instead of jumping there at once.",
            "Know when to rest, reduce reps, or stop before a small issue becomes an injury.",
            "Measure whether the habit is getting easier or too intense.",
            "Check whether the plan is moving you toward the goal safely.",
        ]
        tasks: list[dict[str, Any]] = []

        for index in range(task_count):
            title = fitness_titles[index % len(fitness_titles)]
            goal = fitness_goals[index % len(fitness_goals)]
            tasks.append(
                {
                    "suggested_order": index + 1,
                    "title": title,
                    "description": (
                        f"Goal: {goal}\n\n"
                        "Steps:\n"
                        "1. Record the current reps, sets, effort, or form cue for this task.\n"
                        "2. Choose the safest next training action based on that record.\n"
                        "3. Stop or reduce volume if pain or form breakdown appears.\n\n"
                        f"Deliverable: A pushup training note for {title.lower()}.\n\n"
                        "Done when: The note has reps, effort, and the next safe action.\n\n"
                        "Why it matters: This keeps pushup progress practical and safer to repeat."
                    ),
                    "priority": _priority_for_index(index=index, task_count=task_count),
                    "estimated_hours": _estimated_hours_for_index(index),
                    "due_date": (
                        due_dates[index].isoformat()
                        if index < len(due_dates)
                        else None
                    ),
                    "assigned_to": None,
                }
            )

        return tasks

    blueprints = [
        (
            "Define {topic} success criteria",
            "Write the exact outcome, must-have scope, and measurable checks for the next result.",
            "A success criteria checklist",
        ),
        (
            "Map {topic} constraints",
            "Separate required work, optional improvements, constraints, and open questions before execution.",
            "A prioritized constraints table",
        ),
        (
            "Create {topic} execution plan",
            "Group the work into ordered setup, build, test, and delivery steps with clear dependencies.",
            "An ordered execution plan",
        ),
        (
            "Create {topic} first result",
            "Complete the smallest useful result that proves the main idea can work.",
            "A usable first result",
        ),
        (
            "Test {topic} core flow",
            "Run the main flow, record issues, and choose the fixes needed before sharing.",
            "A test notes tracker",
        ),
        (
            "Prepare {topic} delivery checklist",
            "Confirm final quality, unresolved issues, and the next action after delivery.",
            "A delivery checklist",
        ),
    ]
    tasks: list[dict[str, Any]] = []

    for index in range(task_count):
        title_template, goal, deliverable = blueprints[index % len(blueprints)]
        title = title_template.replace("{topic}", topic)
        tasks.append(
            {
                "suggested_order": index + 1,
                "title": title,
                "description": (
                    f"Goal: {goal}\n\n"
                    "Steps:\n"
                    f"1. Review the current {topic} idea and write the concrete output needed for this task.\n"
                    f"2. Create the task output in a simple document, checklist, tracker, or draft.\n"
                    "3. Check that the output can be used by the next task without extra explanation.\n\n"
                    f"Deliverable: {deliverable} for {topic}.\n\n"
                    f"Done when: The deliverable has at least three concrete items tied to {topic}.\n\n"
                    f"Why it matters: This turns {topic} into visible progress instead of a vague next step."
                ),
                "priority": _priority_for_index(index=index, task_count=task_count),
                "estimated_hours": _estimated_hours_for_index(index),
                "due_date": (
                    due_dates[index].isoformat()
                    if index < len(due_dates)
                    else None
                ),
                "assigned_to": None,
            }
        )

    return tasks


def _build_local_fallback_generated_plan(
    *,
    project: Project,
    input_prompt: str,
    task_count: int,
    include_milestones: bool,
    reason: str,
) -> dict[str, Any]:
    logger.warning(
        "AI Planner using local fallback. reason=%s project_id=%s task_count=%s",
        reason,
        project.project_id,
        task_count,
    )

    local_reply = generate_local_planner_reply(
        _build_structured_ai_plan_prompt(
            project=project,
            input_prompt=input_prompt,
            task_count=task_count,
            include_milestones=include_milestones,
        )
    )
    local_data = _parse_json_object(local_reply) or {}

    normalized_plan = _normalize_ai_plan_response(
        ai_data=local_data,
        project=project,
        input_prompt=input_prompt,
        task_count=task_count,
        include_milestones=include_milestones,
        ai_generation_status="fallback",
    )

    if normalized_plan is not None and normalized_plan["tasks"]:
        normalized_plan["source"] = "local_planner_fallback_v1"
        normalized_plan["message"] = "Generated a fallback project plan."
        logger.info("AI Planner fallback used. source=local_planner_fallback_v1")
        return normalized_plan

    tasks = _build_minimum_local_fallback_tasks(
        project=project,
        input_prompt=input_prompt,
        task_count=task_count,
    )
    milestones = []

    if include_milestones:
        milestones = [
            {
                "name": "Scope confirmed",
                "description": "The first-version direction is clear and ready for execution.",
                "suggested_order": 1,
            },
            {
                "name": "First version completed",
                "description": "The main usable result is built or drafted.",
                "suggested_order": 2,
            },
            {
                "name": "Quality reviewed",
                "description": "The core flow and final issues are checked.",
                "suggested_order": 3,
            },
        ]

    logger.info("AI Planner fallback used. source=minimum_local_planner_v1")
    return {
        "success": True,
        "message": "Generated a fallback project plan.",
        "ai_generation_status": "fallback",
        "source": "minimum_local_planner_v1",
        "domain": _clean_ai_text_field(project.title, fallback="ai_generated", max_length=80),
        "summary": (
            f"Generated a fallback plan for '{project.title}' with {len(tasks)} tasks."
        ),
        "rejected_generic_count": 0,
        "rejected_unrelated_count": 0,
        "tasks_skipped_as_duplicates": 0,
        "rejected_tasks": [],
        "project": {
            "project_id": project.project_id,
            "title": project.title,
            "project_type": project.project_type,
            "deadline": _to_utc(project.deadline).isoformat(),
        },
        "tasks": tasks,
        "milestones": milestones,
        "risks": [
            {
                "risk": "The project idea may need a narrower first version.",
                "recommendation": "Start with the smallest deliverable that proves the idea works.",
            },
            {
                "risk": "Provider-generated detail was unavailable.",
                "recommendation": "Review and adjust the fallback tasks before accepting the plan.",
            },
        ],
        "recommendations": [
            "Review each fallback task before accepting the plan.",
            "Adjust due dates if the deadline is very close.",
            "Keep the first version focused on one clear outcome.",
        ],
    }


def _build_failed_or_fallback_generated_plan(
    *,
    project: Project,
    input_prompt: str,
    task_count: int,
    include_milestones: bool,
    reason: str,
    allow_local_fallback: bool,
    rejected_generic_count: int = 0,
    rejected_unrelated_count: int = 0,
    rejected_tasks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if allow_local_fallback:
        return _build_local_fallback_generated_plan(
            project=project,
            input_prompt=input_prompt,
            task_count=task_count,
            include_milestones=include_milestones,
            reason=reason,
        )

    return _build_failed_generated_plan(
        project,
        rejected_generic_count=rejected_generic_count,
        rejected_unrelated_count=rejected_unrelated_count,
        rejected_tasks=rejected_tasks,
    )


def _build_structured_ai_plan_prompt(
    project: Project,
    input_prompt: str,
    task_count: int,
    include_milestones: bool,
    existing_tasks: list[Task] | None = None,
    overwrite_existing_tasks: bool = False,
) -> str:
    deadline_text = _to_utc(project.deadline).date().isoformat()
    description = project.description or "No description provided."
    existing_tasks_text = _existing_tasks_context(existing_tasks or [])
    improvement_mode = (
        "Rebuild the plan and replace existing tasks with a stronger complete plan."
        if overwrite_existing_tasks
        else "Generate only new complementary tasks that do not duplicate existing work."
    )

    return f"""
You are Planora AI, an expert project planner.

Your job:
Improve the user's existing project plan.
You must understand the idea first, then generate useful tasks that help the user move from idea to execution.
Improve means add missing steps, break down vague work, identify gaps, adjust priorities, and add milestones or risks.
{improvement_mode}

Do not rely on fixed categories, examples, or reusable templates.
Understand the user's exact idea, even if it is unusual, personal, vague, or misspelled.
Do not assume a different goal from the one the user gave.
Handle any practical idea type by reasoning from the provided context only.

First classify the user idea into exactly one domain:
- fitness_health
- study_learning
- software_app
- business_marketing
- content_creator
- event_trip
- personal_habit
- generic_project

Generate a plan that fits that domain.
- Use software/product wording only when the idea is actually an app, website, software tool, or product build.
- For fitness_health and personal_habit goals, write like a practical coach: baseline, safe starting volume, form, progression, recovery, warning rules, tracking, and review.
- For study_learning goals, write like a tutor or study coach.
- For event_trip goals, write like an event/travel organizer.
- For content_creator goals, write like an editor/producer.
- For business_marketing goals, write like an operator/marketer.
- Do not force every idea into features, requirements, MVPs, user flows, releases, or customer language.
- If the domain is not software_app or business_marketing, do not use: features, requirements, MVP, first useful version, customer benefit, idea goal, or user flow.

Critical output rules:
- Return valid JSON only.
- No Markdown.
- No code fences.
- No text outside JSON.
- Generate exactly {task_count} tasks.
- Task titles must start with an action verb.
- Task titles must be specific to the user's idea.
- Avoid vague titles like "Research", "Plan project", "Work on the task", "Prepare strategy", or "Finish project".
- Do not duplicate existing task titles, descriptions, or the same intent.
- If a current task already covers an idea, generate a different missing or follow-up task.
- Priority must be one of: low, medium, high.
- estimated_hours must be realistic: small tasks 0.5-2 hours, medium tasks 2-5 hours, larger tasks 5-12 hours. Avoid 20+ hour tasks.
- suggested_order must start at 1 and increase by 1.

Universal task quality rules:
Every task description must include these exact sections:

Goal:
Explain why this task matters.

Steps:
1. Give the first practical action.
2. Give the second practical action.
3. Give the third practical action.
Add up to 5 steps only when useful.

Deliverable:
Explain exactly what the user should have after finishing the task.

Done when:
Give a measurable condition that proves the task is complete.

Why it matters:
Explain in one short sentence why this task helps the user reach the original goal.

Important:
- The task must teach the user what to do.
- The task must not be only a reminder.
- The task must not be generic.
- The task must be understandable by a beginner.
- The task must move the project forward.
- The task must produce a visible result that is naturally useful for the user's exact idea.
- If information is missing, make a safe assumption and include a short "Assumption:" line only inside the relevant task description.
- If the idea is vague, choose a small useful first path that directly follows from the user's words and make the assumption explicit.

Priority rules:
- high: tasks that unblock the project, define direction, validate demand, or finish delivery.
- medium: normal execution work.
- low: polish, optional improvements, cleanup, or non-critical extras.

Ordering and due-date intent:
- Earlier tasks should clarify, validate, research, or set up.
- Middle tasks should execute the plan.
- Final tasks should test, review, launch, deliver, or collect feedback.

Project context:
- title: {project.title}
- description: {description}
- project_type: {project.project_type}
- deadline: {deadline_text}
- status: {project.status}

Current tasks to avoid duplicating:
{existing_tasks_text}

User idea and context:
{input_prompt.strip()}

Return JSON in exactly this shape:
{{
  "domain": "short natural label inferred from the user idea",
  "summary": "short summary of the generated plan",
  "tasks": [
    {{
      "suggested_order": 1,
      "title": "specific action-based task title",
      "description": "Goal: One sentence explaining why this exact task matters.\\n\\nSteps:\\n1. First practical action.\\n2. Second practical action.\\n3. Third practical action.\\n\\nDeliverable: The exact output the user should have.\\n\\nDone when: A measurable completion condition.\\n\\nWhy it matters: One short sentence explaining how this helps the original goal.",
      "priority": "high",
      "estimated_hours": 2.5
    }}
  ],
  "milestones": [
    {{
      "name": "milestone name",
      "description": "milestone description",
      "suggested_order": 1
    }}
  ],
  "risks": [
    {{
      "risk": "main risk",
      "recommendation": "how to reduce it"
    }}
  ],
  "recommendations": [
    "practical recommendation"
  ]
}}

Milestones:
{"Include 2-4 milestones." if include_milestones else "Return an empty milestones array."}
""".strip()


def _clean_ai_text_field(
    value: Any,
    fallback: str,
    max_length: int = 500,
    preserve_newlines: bool = False,
) -> str:
    if value is None:
        return fallback

    cleaned = str(value).strip()
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"__(.*?)__", r"\1", cleaned)
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
    cleaned = cleaned.replace("$1", "")

    if preserve_newlines:
        lines = [
            re.sub(r"[ \t]+", " ", line).strip()
            for line in cleaned.splitlines()
        ]

        compact_lines: list[str] = []
        previous_blank = False

        for line in lines:
            if not line:
                if not previous_blank:
                    compact_lines.append("")
                previous_blank = True
                continue

            compact_lines.append(line)
            previous_blank = False

        cleaned = "\n".join(compact_lines).strip()
    else:
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if not cleaned:
        return fallback

    if len(cleaned) > max_length:
        cleaned = cleaned[: max_length - 3].rstrip() + "..."

    return cleaned



def _is_bad_ai_task_text(value: str) -> bool:
    lowered = value.lower()

    bad_fragments = [
        "create a complete planora project plan",
        "available hours per week",
        "preferred task count",
        "return valid json",
        "project context:",
        "user idea and requirements:",
        "return json",
        "return a practical plan",
        "every task description must",
        "universal task quality rules",
        "you are planora ai",
        "do not add",
        "$1",
    ]

    return any(fragment in lowered for fragment in bad_fragments)


def _extract_description_section(
    value: str,
    label: str,
    next_labels: tuple[str, ...],
) -> str:
    stop_pattern = "|".join(re.escape(next_label) for next_label in next_labels)
    pattern = rf"{re.escape(label)}\s*(.*?)(?:\n\s*(?:{stop_pattern})|$)"
    match = re.search(pattern, value, flags=re.IGNORECASE | re.DOTALL)

    if match is None:
        return ""

    return match.group(1).strip()


def _description_has_visible_result(value: str) -> bool:
    deliverable = _extract_description_section(
        value=value,
        label="Deliverable:",
        next_labels=("Done when:", "Customer benefit:", "Why it matters:", "Benefit:"),
    )
    normalized = _normalize_comparison_text(deliverable)

    if not normalized:
        return False

    generic_deliverables = {
        "a finished result for this task",
        "a clear finished output for this task",
        "a project specific output for this task",
        "the exact output the user should have",
    }

    if normalized in generic_deliverables:
        return False

    visible_terms = (
        "budget",
        "calendar",
        "checklist",
        "content",
        "document",
        "draft",
        "guest list",
        "lead tracker",
        "list",
        "log",
        "message",
        "plan",
        "post",
        "practice",
        "price",
        "prototype",
        "review",
        "routine",
        "rule",
        "schedule",
        "screen",
        "table",
        "target",
        "tracker",
        "video",
    )

    return any(term in normalized for term in visible_terms)


def _is_actionable_task_description(value: str) -> bool:
    lowered = value.lower()

    has_all_sections = all(section in lowered for section in SMART_DESCRIPTION_SECTIONS)
    has_benefit_section = any(
        section in lowered
        for section in SMART_DESCRIPTION_BENEFIT_SECTIONS
    )
    numbered_steps = len(re.findall(r"(?:^|\n)\s*\d+\.", value))

    return (
        has_all_sections
        and has_benefit_section
        and numbered_steps >= 3
        and _description_has_visible_result(value)
    )



def _normalize_comparison_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _extract_project_context_phrases(project_context: str) -> list[str]:
    phrases: list[str] = []

    for raw_line in project_context.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        line = re.sub(
            r"^(idea|project idea|project idea and goal|user idea and context|extra notes, constraints, or preferences|requirements|requirements and constraints|requirements, features, constraints, and notes)\s*:\s*",
            "",
            line,
            flags=re.IGNORECASE,
        ).strip()

        if len(line) >= 12:
            phrases.append(line)

    compact_context = project_context.strip()

    if len(compact_context) >= 12:
        phrases.append(compact_context)

    return list(dict.fromkeys(phrases))


def _description_repeats_project_idea(
    description: str,
    project_context: str,
) -> bool:
    cleaned_description = _normalize_comparison_text(description)

    if not cleaned_description:
        return True

    for phrase in _extract_project_context_phrases(project_context):
        cleaned_phrase = _normalize_comparison_text(phrase)

        if not cleaned_phrase:
            continue

        if cleaned_description == cleaned_phrase:
            return True

        if cleaned_phrase in cleaned_description and len(cleaned_description) < len(cleaned_phrase) + 140:
            return True

        if cleaned_description in cleaned_phrase and len(cleaned_description) >= 20:
            return True

    return False


def _description_key(description: str) -> str:
    cleaned = _normalize_comparison_text(description)
    cleaned = re.sub(r"goal:\s*", "", cleaned)
    cleaned = re.sub(r"steps:\s*", "", cleaned)
    cleaned = re.sub(r"deliverable:\s*", "", cleaned)
    cleaned = re.sub(r"done when:\s*", "", cleaned)
    cleaned = re.sub(r"customer benefit:\s*", "", cleaned)
    cleaned = re.sub(r"why it matters:\s*", "", cleaned)
    cleaned = re.sub(r"benefit:\s*", "", cleaned)

    return cleaned[:500]


def _description_is_too_generic(description: str) -> bool:
    lowered = description.lower()

    generic_fragments = [
        "focus only on this task",
        "decide the smallest useful result",
        "complete that result without adding extra",
        "check that the result is clear",
        "a clear finished output for",
        "read the project idea and decide what",
        "write the exact output needed for",
        "create the smallest useful version of that output",
        "remove anything that belongs to a later version",
        "save the result so it can be used in the next task",
        "understand what this task requires",
        "complete the smallest useful version",
        "review the result before moving forward",
        "a finished result for this task",
    ]

    matches = sum(fragment in lowered for fragment in generic_fragments)

    return matches >= 2


def _is_low_quality_task_title(title: str) -> bool:
    normalized = _normalize_comparison_text(title)
    first_word = normalized.split(" ", 1)[0] if normalized else ""
    generic_titles = {
        "research",
        "planning",
        "analysis",
        "preparation",
        "strategy",
        "review",
        "improve",
        "start",
        "task",
        "plan project",
        "work on the task",
        "prepare strategy",
        "finish project",
        "complete project step",
        "complete project step 1",
        "complete project step 2",
        "complete project step 3",
    }

    return (
        normalized in generic_titles
        or len(normalized) < 4
        or re.fullmatch(r"complete project step \d+", normalized) is not None
        or first_word not in ACTION_VERBS
    )


def _is_disallowed_generic_task_title(title: str) -> bool:
    normalized = _normalize_comparison_text(title)
    return _matches_any_pattern(normalized, GENERIC_TASK_TITLE_PATTERNS)


def _has_similar_seen_title(title: str, seen_titles: set[str]) -> bool:
    return any(_task_titles_are_similar(title, seen_title) for seen_title in seen_titles)


def _coerce_ai_priority(value: Any, fallback: str = "medium") -> str:
    priority = str(value or "").strip().lower()

    if priority in {"low", "medium", "high"}:
        return priority

    return fallback


def _coerce_ai_estimated_hours(value: Any, fallback: float) -> float:
    try:
        hours = float(value)
    except (TypeError, ValueError):
        return fallback

    if hours <= 0:
        return fallback

    if hours < 0.5:
        return max(0.5, fallback)

    if hours > 12:
        return 12.0

    return round(hours, 2)


def _build_ai_due_dates(project: Project, task_count: int) -> list[str]:
    return [
        due_date.isoformat()
        for due_date in _build_due_dates(project=project, task_count=task_count)
    ]


def _build_json_repair_prompt(
    original_prompt: str,
    provider_reply: str,
) -> str:
    return f"""
You are Planora AI.

Repair this into valid JSON matching the requested schema.
Do not add unrelated content.
Do not invent a different idea.
Keep the same user intent, task meanings, and counts if they are present.
Return valid JSON only. No Markdown. No code fences.

Original prompt:
{original_prompt}

Invalid provider reply:
{provider_reply[:7000]}
""".strip()


def _build_replacement_tasks_prompt(
    original_prompt: str,
    project_context: str,
    accepted_tasks: list[dict[str, Any]],
    rejected_tasks: list[dict[str, Any]],
    missing_count: int,
) -> str:
    accepted_payload = [
        {"title": task.get("title"), "description": task.get("description")}
        for task in accepted_tasks
    ]

    return f"""
You are Planora AI.

Some generated tasks were rejected by generic quality checks.
Generate exactly {missing_count} replacement task(s) that stay closer to the original user idea.

Original user/project context:
{project_context}

Original planning prompt:
{original_prompt}

Accepted tasks to avoid duplicating:
{json.dumps(accepted_payload, ensure_ascii=False, indent=2)}

Rejected tasks and reasons:
{json.dumps(rejected_tasks, ensure_ascii=False, indent=2)}

Rules:
- Stay specific to the original idea.
- Do not add unrelated goals or generic project-management filler.
- Do not duplicate accepted or existing task intent.
- Each replacement task must produce real progress for the stated idea.
- Return valid JSON only with this shape:
{{
  "domain": "natural label inferred from the idea",
  "summary": "short summary",
  "tasks": [
    {{
      "suggested_order": 1,
      "title": "specific action title",
      "description": "Goal: ...\\n\\nSteps:\\n1. ...\\n2. ...\\n3. ...\\n\\nDeliverable: ...\\n\\nDone when: ...\\n\\nWhy it matters: ...",
      "priority": "high",
      "estimated_hours": 2
    }}
  ],
  "milestones": [],
  "risks": [],
  "recommendations": []
}}
""".strip()


def _task_quality_rejection_reasons(
    *,
    title: str,
    description: str,
    project_context: str,
    seen_titles: set[str],
    seen_descriptions: set[str],
    existing_titles: list[str],
    existing_descriptions: list[str],
) -> tuple[list[str], dict[str, float]]:
    combined_task_text = f"{title}\n{description}"
    relevance_score = _token_overlap_score(project_context, combined_task_text)
    specificity_score = _specificity_score(title, description)
    actionability_score = _actionability_score(description)
    project_domain = _classify_planning_domain(project_context)
    task_domain = _classify_planning_domain(combined_task_text)
    duplicate_score = _duplicate_score(
        title=title,
        description=description,
        seen_titles=seen_titles,
        seen_descriptions=seen_descriptions,
        existing_titles=existing_titles,
        existing_descriptions=existing_descriptions,
    )
    scores = {
        "relevance_score": round(relevance_score, 3),
        "specificity_score": round(specificity_score, 3),
        "actionability_score": round(actionability_score, 3),
        "duplicate_score": round(duplicate_score, 3),
    }
    reasons: list[str] = []

    if _is_bad_ai_task_text(title) or _is_bad_ai_task_text(description):
        reasons.append("instruction_leak")

    if _uses_wrong_domain_product_language(
        project_context=project_context,
        task_text=combined_task_text,
    ):
        reasons.append("wrong_domain_language")

    if _is_low_quality_task_title(title) or _is_disallowed_generic_task_title(title):
        reasons.append("generic_title")

    if (
        not _is_actionable_task_description(description)
        or _description_is_too_generic(description)
        or _contains_robotic_description(description)
        or _description_restates_title(title, description)
    ):
        reasons.append("generic_description")

    if _description_repeats_project_idea(description, project_context):
        reasons.append("description_repeats_idea")

    if relevance_score < 0.18 and task_domain != project_domain:
        reasons.append("unrelated_to_idea")

    if specificity_score < 0.35:
        reasons.append("not_specific_enough")

    if actionability_score < 0.65:
        reasons.append("not_actionable_enough")

    if duplicate_score <= 0:
        reasons.append("duplicate_intent")

    return reasons, scores


def _build_failed_generated_plan(
    project: Project,
    message: str = AI_PLANNING_UNAVAILABLE_MESSAGE,
    rejected_generic_count: int = 0,
    rejected_unrelated_count: int = 0,
    rejected_tasks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "ai_generation_status": "failed",
        "source": "ai_provider",
        "domain": "ai_generated",
        "summary": message,
        "rejected_generic_count": rejected_generic_count,
        "rejected_unrelated_count": rejected_unrelated_count,
        "tasks_skipped_as_duplicates": 0,
        "rejected_tasks": rejected_tasks or [],
        "project": {
            "project_id": project.project_id,
            "title": project.title,
            "project_type": project.project_type,
            "deadline": _to_utc(project.deadline).isoformat(),
        },
        "tasks": [],
        "milestones": [],
        "risks": [],
        "recommendations": [],
    }


def _has_only_duplicate_rejections(generated_plan: dict[str, Any]) -> bool:
    rejected_tasks = generated_plan.get("rejected_tasks")

    if not isinstance(rejected_tasks, list) or not rejected_tasks:
        return True

    for rejected_task in rejected_tasks:
        if not isinstance(rejected_task, dict):
            return False

        reasons = rejected_task.get("reasons")

        if not isinstance(reasons, list) or set(reasons) != {"duplicate_intent"}:
            return False

    return True


def _normalize_ai_plan_response(
    ai_data: dict[str, Any],
    project: Project,
    input_prompt: str,
    task_count: int,
    include_milestones: bool,
    existing_tasks: list[Task] | None = None,
    existing_generated_tasks: list[dict[str, Any]] | None = None,
    ai_generation_status: str = "generated",
    allow_zero_tasks: bool = False,
) -> dict[str, Any] | None:
    raw_tasks = ai_data.get("tasks")

    if not isinstance(raw_tasks, list):
        return None

    if not raw_tasks and not allow_zero_tasks:
        return None

    if len(raw_tasks) > max(task_count * 2, task_count + 3):
        raw_tasks = raw_tasks[: max(task_count * 2, task_count + 3)]

    tasks: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    seen_descriptions: set[str] = set()
    rejected_generic_count = 0
    rejected_unrelated_count = 0
    rejected_tasks: list[dict[str, Any]] = []
    project_context = _extract_user_project_context(
        project=project,
        input_prompt=input_prompt,
    )
    existing_titles = [
        task.title
        for task in (existing_tasks or [])
        if task.title and task.title.strip()
    ]
    existing_descriptions = [
        task.description
        for task in (existing_tasks or [])
        if task.description and task.description.strip()
    ]

    for task in existing_generated_tasks or []:
        title = str(task.get("title") or "").strip()
        description = str(task.get("description") or "").strip()

        if title:
            existing_titles.append(title)

        if description:
            existing_descriptions.append(description)

    for index, raw_task in enumerate(raw_tasks):
        if not isinstance(raw_task, dict):
            rejected_generic_count += 1
            rejected_tasks.append(
                {
                    "index": index + 1,
                    "title": "",
                    "reasons": ["invalid_task_shape"],
                }
            )
            continue

        title = _clean_ai_text_field(
            raw_task.get("title"),
            fallback="",
            max_length=120,
        )
        description = _clean_ai_text_field(
            raw_task.get("description"),
            fallback="",
            max_length=2200,
            preserve_newlines=True,
        )
        reasons, scores = _task_quality_rejection_reasons(
            title=title,
            description=description,
            project_context=project_context,
            seen_titles=seen_titles,
            seen_descriptions=seen_descriptions,
            existing_titles=existing_titles,
            existing_descriptions=existing_descriptions,
        )

        if reasons:
            if "unrelated_to_idea" in reasons:
                rejected_unrelated_count += 1
            else:
                rejected_generic_count += 1

            rejected_tasks.append(
                {
                    "index": index + 1,
                    "title": title,
                    "reasons": reasons,
                    "scores": scores,
                }
            )
            continue

        if scores["duplicate_score"] <= 0:
            rejected_generic_count += 1
            continue

        description_key = _description_key(description)
        normalized_title_key = title.lower()
        seen_titles.add(normalized_title_key)
        seen_descriptions.add(description_key)
        estimated_hours = _coerce_ai_estimated_hours(
            raw_task.get("estimated_hours"),
            fallback=_estimated_hours_for_index(index),
        )

        tasks.append(
            {
                "suggested_order": index + 1,
                "title": title,
                "description": description,
                "priority": _coerce_ai_priority(
                    raw_task.get("priority"),
                    fallback=_priority_for_index(index=index, task_count=len(raw_tasks)),
                ),
                "estimated_hours": estimated_hours,
                "due_date": None,
                "assigned_to": raw_task.get("assigned_to"),
            }
        )

        if len(tasks) >= task_count:
            break

    due_dates = _build_ai_due_dates(project=project, task_count=len(tasks))

    for index, task in enumerate(tasks):
        task["suggested_order"] = index + 1
        task["due_date"] = due_dates[index] if index < len(due_dates) else None

    domain = _clean_ai_text_field(
        ai_data.get("domain"),
        fallback="ai_generated",
        max_length=80,
    )
    summary = _clean_ai_text_field(
        ai_data.get("summary"),
        fallback=(
            f"Generated a practical AI plan for '{project.title}' with "
            f"{len(tasks)} tasks before the project deadline."
        ),
        max_length=700,
    )

    milestones: list[dict[str, Any]] = []

    if include_milestones:
        raw_milestones = ai_data.get("milestones")

        if isinstance(raw_milestones, list):
            for index, raw_milestone in enumerate(raw_milestones[:4]):
                if not isinstance(raw_milestone, dict):
                    continue

                milestones.append(
                    {
                        "name": _clean_ai_text_field(
                            raw_milestone.get("name"),
                            fallback=f"Milestone {index + 1}",
                            max_length=120,
                        ),
                        "description": _clean_ai_text_field(
                            raw_milestone.get("description"),
                            fallback="Important project checkpoint.",
                            max_length=300,
                        ),
                        "suggested_order": index + 1,
                    }
                )

    risks: list[dict[str, str]] = []
    raw_risks = ai_data.get("risks")

    if isinstance(raw_risks, list):
        for raw_risk in raw_risks[:4]:
            if not isinstance(raw_risk, dict):
                continue

            risks.append(
                {
                    "risk": _clean_ai_text_field(
                        raw_risk.get("risk"),
                        fallback="Project risk",
                        max_length=160,
                    ),
                    "recommendation": _clean_ai_text_field(
                        raw_risk.get("recommendation"),
                        fallback="Review this risk before starting.",
                        max_length=300,
                    ),
                }
            )

    recommendations: list[str] = []
    raw_recommendations = ai_data.get("recommendations")

    if isinstance(raw_recommendations, list):
        for raw_recommendation in raw_recommendations[:5]:
            recommendations.append(
                _clean_ai_text_field(
                    raw_recommendation,
                    fallback="Review the plan before accepting it.",
                    max_length=220,
                )
            )

    message = _clean_ai_text_field(
        ai_data.get("message"),
        fallback=(
            PLAN_ALREADY_COVERS_MESSAGE
            if not tasks and allow_zero_tasks
            else "Generated AI tasks from the user idea."
        ),
        max_length=300,
    )

    return {
        "success": True,
        "message": message,
        "ai_generation_status": ai_generation_status,
        "source": "ai_provider",
        "domain": domain,
        "summary": summary,
        "rejected_generic_count": rejected_generic_count,
        "rejected_unrelated_count": rejected_unrelated_count,
        "tasks_skipped_as_duplicates": 0,
        "rejected_tasks": rejected_tasks,
        "project": {
            "project_id": project.project_id,
            "title": project.title,
            "project_type": project.project_type,
            "deadline": _to_utc(project.deadline).isoformat(),
        },
        "tasks": tasks,
        "milestones": milestones,
        "risks": risks,
        "recommendations": recommendations,
    }


def _build_ai_generated_plan(
    project: Project,
    input_prompt: str,
    task_count: int,
    include_milestones: bool,
    existing_tasks: list[Task] | None = None,
    overwrite_existing_tasks: bool = False,
    allow_local_fallback: bool = False,
) -> dict[str, Any]:
    prompt = _build_structured_ai_plan_prompt(
        project=project,
        input_prompt=input_prompt,
        task_count=task_count,
        include_milestones=include_milestones,
        existing_tasks=existing_tasks,
        overwrite_existing_tasks=overwrite_existing_tasks,
    )

    provider_reply = _generate_ai_plan_reply_from_provider(prompt)

    if provider_reply is None:
        return _build_failed_or_fallback_generated_plan(
            project=project,
            input_prompt=input_prompt,
            task_count=task_count,
            include_milestones=include_milestones,
            reason="provider_unavailable",
            allow_local_fallback=allow_local_fallback,
        )

    parsed = _parse_json_object(provider_reply)
    ai_generation_status = "generated"

    if parsed is None:
        repair_prompt = _build_json_repair_prompt(
            original_prompt=prompt,
            provider_reply=provider_reply,
        )
        repaired_reply = _generate_ai_plan_reply_from_provider(repair_prompt)

        if repaired_reply is None:
            return _build_failed_or_fallback_generated_plan(
                project=project,
                input_prompt=input_prompt,
                task_count=task_count,
                include_milestones=include_milestones,
                reason="json_repair_provider_unavailable",
                allow_local_fallback=allow_local_fallback,
            )

        parsed = _parse_json_object(repaired_reply)
        ai_generation_status = "repaired"

        if parsed is None:
            return _build_failed_or_fallback_generated_plan(
                project=project,
                input_prompt=input_prompt,
                task_count=task_count,
                include_milestones=include_milestones,
                reason="json_parse_failed_after_repair",
                allow_local_fallback=allow_local_fallback,
            )

    allow_zero_tasks = bool(existing_tasks and not overwrite_existing_tasks)

    normalized_plan = _normalize_ai_plan_response(
        ai_data=parsed,
        project=project,
        input_prompt=input_prompt,
        task_count=task_count,
        include_milestones=include_milestones,
        existing_tasks=existing_tasks,
        ai_generation_status=ai_generation_status,
        allow_zero_tasks=allow_zero_tasks,
    )

    if normalized_plan is None:
        return _build_failed_or_fallback_generated_plan(
            project=project,
            input_prompt=input_prompt,
            task_count=task_count,
            include_milestones=include_milestones,
            reason="normalized_plan_invalid",
            allow_local_fallback=allow_local_fallback,
        )

    if (
        not normalized_plan["tasks"]
        and allow_zero_tasks
        and _has_only_duplicate_rejections(normalized_plan)
    ):
        normalized_plan["message"] = PLAN_ALREADY_COVERS_MESSAGE
        normalized_plan["summary"] = PLAN_ALREADY_COVERS_MESSAGE
        return normalized_plan

    if len(normalized_plan["tasks"]) >= task_count:
        normalized_plan["tasks"] = normalized_plan["tasks"][:task_count]
        return normalized_plan

    missing_count = task_count - len(normalized_plan["tasks"])
    replacement_prompt = _build_replacement_tasks_prompt(
        original_prompt=prompt,
        project_context=_extract_user_project_context(project, input_prompt),
        accepted_tasks=list(normalized_plan["tasks"]),
        rejected_tasks=list(normalized_plan.get("rejected_tasks") or []),
        missing_count=missing_count,
    )
    replacement_reply = _generate_ai_plan_reply_from_provider(replacement_prompt)

    if replacement_reply is None:
        return _build_failed_or_fallback_generated_plan(
            project=project,
            input_prompt=input_prompt,
            task_count=task_count,
            include_milestones=include_milestones,
            reason="replacement_provider_unavailable",
            allow_local_fallback=allow_local_fallback,
            rejected_generic_count=int(normalized_plan.get("rejected_generic_count") or 0),
            rejected_unrelated_count=int(
                normalized_plan.get("rejected_unrelated_count") or 0
            ),
            rejected_tasks=list(normalized_plan.get("rejected_tasks") or []),
        )

    replacement_data = _parse_json_object(replacement_reply)

    if replacement_data is None:
        return _build_failed_or_fallback_generated_plan(
            project=project,
            input_prompt=input_prompt,
            task_count=task_count,
            include_milestones=include_milestones,
            reason="replacement_json_parse_failed",
            allow_local_fallback=allow_local_fallback,
            rejected_generic_count=int(normalized_plan.get("rejected_generic_count") or 0),
            rejected_unrelated_count=int(
                normalized_plan.get("rejected_unrelated_count") or 0
            ),
            rejected_tasks=list(normalized_plan.get("rejected_tasks") or []),
        )

    replacement_plan = _normalize_ai_plan_response(
        ai_data=replacement_data,
        project=project,
        input_prompt=input_prompt,
        task_count=missing_count,
        include_milestones=False,
        existing_tasks=existing_tasks,
        existing_generated_tasks=list(normalized_plan["tasks"]),
        ai_generation_status=ai_generation_status,
    )

    if replacement_plan is None or len(replacement_plan["tasks"]) < missing_count:
        rejected_generic_count = int(normalized_plan.get("rejected_generic_count") or 0)
        rejected_unrelated_count = int(normalized_plan.get("rejected_unrelated_count") or 0)
        rejected_tasks = list(normalized_plan.get("rejected_tasks") or [])

        if replacement_plan is not None:
            rejected_generic_count += int(
                replacement_plan.get("rejected_generic_count") or 0
            )
            rejected_unrelated_count += int(
                replacement_plan.get("rejected_unrelated_count") or 0
            )
            rejected_tasks.extend(list(replacement_plan.get("rejected_tasks") or []))

        return _build_failed_or_fallback_generated_plan(
            project=project,
            input_prompt=input_prompt,
            task_count=task_count,
            include_milestones=include_milestones,
            reason="replacement_normalized_plan_invalid",
            allow_local_fallback=allow_local_fallback,
            rejected_generic_count=rejected_generic_count,
            rejected_unrelated_count=rejected_unrelated_count,
            rejected_tasks=rejected_tasks,
        )

    normalized_plan["tasks"].extend(replacement_plan["tasks"])
    normalized_plan["rejected_generic_count"] += int(
        replacement_plan.get("rejected_generic_count") or 0
    )
    normalized_plan["rejected_unrelated_count"] += int(
        replacement_plan.get("rejected_unrelated_count") or 0
    )
    due_dates = _build_ai_due_dates(project=project, task_count=len(normalized_plan["tasks"]))

    for index, task in enumerate(normalized_plan["tasks"]):
        task["suggested_order"] = index + 1
        task["due_date"] = due_dates[index]

    return normalized_plan


def build_generated_plan(
    project: Project,
    input_prompt: str,
    task_count: int,
    include_milestones: bool = True,
    project_members: list[ProjectMember] | None = None,
    existing_tasks: list[Task] | None = None,
    overwrite_existing_tasks: bool = False,
    allow_local_fallback: bool = False,
) -> dict[str, Any]:
    project_context = (
        input_prompt.strip()
        or project.description
        or f"Create a structured project plan for {project.title}."
    )

    ai_generated_plan = _build_ai_generated_plan(
        project=project,
        input_prompt=project_context,
        task_count=task_count,
        include_milestones=include_milestones,
        existing_tasks=existing_tasks,
        overwrite_existing_tasks=overwrite_existing_tasks,
        allow_local_fallback=allow_local_fallback,
    )

    assignable_member_ids = [
        member.user_id
        for member in (project_members or [])
        if member.user_id is not None
    ]

    if project.project_type == "team" and assignable_member_ids:
        for index, task in enumerate(ai_generated_plan["tasks"]):
            task["assigned_to"] = assignable_member_ids[
                index % len(assignable_member_ids)
            ]
    else:
        for task in ai_generated_plan["tasks"]:
            task["assigned_to"] = None

    return ai_generated_plan


def _parse_due_date(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _normalize_task_title(title: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", title.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def _task_titles_are_similar(first: str, second: str) -> bool:
    first_normalized = _normalize_task_title(first)
    second_normalized = _normalize_task_title(second)

    if not first_normalized or not second_normalized:
        return False

    if first_normalized == second_normalized:
        return True

    return SequenceMatcher(
        None,
        first_normalized,
        second_normalized,
    ).ratio() >= 0.86


def _task_is_duplicate_title(
    title: str,
    existing_titles: list[str],
) -> bool:
    return any(_task_titles_are_similar(title, existing) for existing in existing_titles)


def _task_descriptions_are_similar(first: str, second: str) -> bool:
    first_normalized = _description_key(first)
    second_normalized = _description_key(second)

    if not first_normalized or not second_normalized:
        return False

    if first_normalized in second_normalized or second_normalized in first_normalized:
        return min(len(first_normalized), len(second_normalized)) >= 80

    return SequenceMatcher(
        None,
        first_normalized,
        second_normalized,
    ).ratio() >= 0.82


def _task_is_duplicate_intent(
    title: str,
    description: str | None,
    existing_titles: list[str],
    existing_descriptions: list[str],
) -> bool:
    if _task_is_duplicate_title(title, existing_titles):
        return True

    if description:
        return any(
            _task_descriptions_are_similar(description, existing_description)
            for existing_description in existing_descriptions
        )

    return False


def _get_existing_project_tasks(
    db: Session,
    project: Project,
) -> list[Task]:
    return list(
        db.execute(
            select(Task)
            .where(Task.project_id == project.project_id)
            .order_by(Task.created_at.asc(), Task.task_id.asc())
        )
        .scalars()
        .all()
    )


def _existing_tasks_context(existing_tasks: list[Task]) -> str:
    if not existing_tasks:
        return "No current tasks."

    lines: list[str] = []

    for index, task in enumerate(existing_tasks[:40], start=1):
        description = (task.description or "").strip().replace("\n", " ")
        if len(description) > 220:
            description = f"{description[:217].rstrip()}..."

        pieces = [
            f"{index}. {task.title}",
            f"status={task.status}",
            f"priority={task.priority}",
        ]

        if task.due_date is not None:
            pieces.append(f"due={_to_utc(task.due_date).date().isoformat()}")

        if description:
            pieces.append(f"description={description}")

        lines.append(" | ".join(pieces))

    return "\n".join(lines)


def _create_tasks_from_plan(
    db: Session,
    project: Project,
    current_user: User,
    generated_plan: dict[str, Any],
    existing_tasks: list[Task] | None = None,
) -> tuple[list[Task], int]:
    created_tasks: list[Task] = []
    skipped_duplicate_count = 0
    existing_titles = [
        task.title
        for task in (existing_tasks or [])
        if task.title and task.title.strip()
    ]
    existing_descriptions = [
        task.description
        for task in (existing_tasks or [])
        if task.description and task.description.strip()
    ]

    assigned_to = (
        current_user.user_id
        if project.project_type == "personal"
        else None
    )

    for task_data in generated_plan["tasks"]:
        task_title = str(task_data["title"])
        task_description = (
            str(task_data["description"])
            if task_data.get("description") is not None
            else None
        )

        if _task_is_duplicate_intent(
            title=task_title,
            description=task_description,
            existing_titles=existing_titles,
            existing_descriptions=existing_descriptions,
        ):
            skipped_duplicate_count += 1
            continue

        task = Task(
            project_id=project.project_id,
            assigned_to=assigned_to,
            created_by=current_user.user_id,
            title=task_title,
            description=task_description,
            priority=str(task_data["priority"]),
            estimated_hours=(
                float(task_data["estimated_hours"])
                if task_data.get("estimated_hours") is not None
                else None
            ),
            actual_hours=None,
            status=TaskStatus.todo.value,
            due_date=(
                _parse_due_date(str(task_data["due_date"]))
                if task_data.get("due_date") is not None
                else None
            ),
            completed_at=None,
        )

        if project.project_type == "team":
            task.assigned_to = task_data.get("assigned_to")

        db.add(task)
        db.flush()

        created_tasks.append(task)
        existing_titles.append(task.title)
        if task.description:
            existing_descriptions.append(task.description)

        create_activity_log(
            db=db,
            project=project,
            actor=current_user,
            task=task,
            event_type=ActivityLogEventType.TASK_CREATED,
            message=f"{current_user.full_name} created AI-generated task '{task.title}'.",
            metadata={
                "generated_by_ai_plan": True,
                "priority": task.priority,
                "assigned_to": task.assigned_to,
            },
            commit=False,
        )

    return created_tasks, skipped_duplicate_count


def _delete_existing_project_tasks(
    db: Session,
    project: Project,
) -> int:
    existing_tasks = _get_existing_project_tasks(db=db, project=project)

    for task in existing_tasks:
        db.delete(task)

    if existing_tasks:
        db.flush()

    return len(existing_tasks)


def _get_project_members_for_assignment(
    db: Session,
    project: Project,
) -> list[ProjectMember]:
    if project.project_type != "team":
        return []

    return list(
        db.execute(
            select(ProjectMember)
            .where(ProjectMember.project_id == project.project_id)
            .order_by(ProjectMember.joined_at.asc(), ProjectMember.member_id.asc())
        )
        .scalars()
        .all()
    )


def create_ai_plan_for_project(
    db: Session,
    project: Project,
    current_user: User,
    plan_data: AIPlanGenerateRequest,
) -> AIPlan:
    ai_plan, _created_tasks, _skipped_duplicate_count = (
        create_ai_plan_and_tasks_for_project(
            db=db,
            project=project,
            current_user=current_user,
            plan_data=plan_data,
        )
    )

    return ai_plan


def create_ai_plan_and_tasks_for_project(
    db: Session,
    project: Project,
    current_user: User,
    plan_data: AIPlanGenerateRequest,
) -> tuple[AIPlan, list[Task], int]:
    input_prompt = (
        plan_data.input_prompt.strip()
        if plan_data.input_prompt
        else f"Generate a project plan for {project.title}."
    )
    project_members = _get_project_members_for_assignment(
        db=db,
        project=project,
    )
    existing_tasks = _get_existing_project_tasks(db=db, project=project)

    generated_plan = build_generated_plan(
        project=project,
        input_prompt=input_prompt,
        task_count=plan_data.task_count,
        include_milestones=plan_data.include_milestones,
        project_members=project_members,
        existing_tasks=existing_tasks,
        overwrite_existing_tasks=plan_data.overwrite_existing_tasks,
    )

    ai_plan = AIPlan(
        project_id=project.project_id,
        generated_by=current_user.user_id,
        input_prompt=input_prompt,
        generated_plan=generated_plan,
    )

    db.add(ai_plan)
    db.flush()

    overwritten_task_count = 0
    created_tasks: list[Task] = []
    skipped_duplicate_count = 0

    if plan_data.create_tasks:
        duplicate_scope = [] if plan_data.overwrite_existing_tasks else existing_tasks

        if plan_data.overwrite_existing_tasks:
            overwritten_task_count = _delete_existing_project_tasks(
                db=db,
                project=project,
            )

        created_tasks, skipped_duplicate_count = _create_tasks_from_plan(
            db=db,
            project=project,
            current_user=current_user,
            generated_plan=generated_plan,
            existing_tasks=duplicate_scope,
        )

    created_task_ids = [task.task_id for task in created_tasks]

    ai_plan.generated_plan = {
        **generated_plan,
        "created_task_ids": created_task_ids,
        "tasks_created": len(created_task_ids),
        "tasks_skipped_as_duplicates": skipped_duplicate_count,
        "overwrite_existing_tasks": plan_data.overwrite_existing_tasks,
        "overwritten_task_count": overwritten_task_count,
        "improvement_summary": str(generated_plan.get("summary", "")),
        "rejected_generic_count": int(
            generated_plan.get("rejected_generic_count") or 0
        ),
        "rejected_unrelated_count": int(
            generated_plan.get("rejected_unrelated_count") or 0
        ),
        "success": bool(generated_plan.get("success", True)),
        "message": str(generated_plan.get("message", "")),
        "ai_generation_status": str(
            generated_plan.get("ai_generation_status", "generated")
        ),
    }

    create_activity_log(
        db=db,
        project=project,
        actor=current_user,
        event_type=ActivityLogEventType.AI_PLAN_GENERATED,
        message=f"{current_user.full_name} generated an AI plan for '{project.title}'.",
        metadata={
            "plan_id": ai_plan.plan_id,
            "created_task_count": len(created_task_ids),
            "tasks_skipped_as_duplicates": skipped_duplicate_count,
            "created_task_ids": created_task_ids,
            "overwrite_existing_tasks": plan_data.overwrite_existing_tasks,
            "overwritten_task_count": overwritten_task_count,
            "source": str(generated_plan.get("source", "unknown")),
            "rejected_generic_count": int(
                generated_plan.get("rejected_generic_count") or 0
            ),
            "rejected_unrelated_count": int(
                generated_plan.get("rejected_unrelated_count") or 0
            ),
            "success": bool(generated_plan.get("success", True)),
            "ai_generation_status": str(
                generated_plan.get("ai_generation_status", "generated")
            ),
        },
        commit=False,
    )

    db.commit()
    db.refresh(ai_plan)

    for task in created_tasks:
        db.refresh(task)

    return ai_plan, created_tasks, skipped_duplicate_count


def create_ai_plan_generation_response(
    db: Session,
    project: Project,
    current_user: User,
    plan_data: AIPlanGenerateRequest,
) -> AIPlanGenerateResponse:
    ai_plan, created_tasks, skipped_duplicate_count = create_ai_plan_and_tasks_for_project(
        db=db,
        project=project,
        current_user=current_user,
        plan_data=plan_data,
    )

    return AIPlanGenerateResponse(
        project_id=project.project_id,
        plan_id=ai_plan.plan_id,
        success=bool(ai_plan.generated_plan.get("success", True)),
        message=str(ai_plan.generated_plan.get("message", "")),
        summary=str(ai_plan.generated_plan.get("summary", "")),
        tasks_created=len(created_tasks),
        tasks_skipped_as_duplicates=skipped_duplicate_count,
        improvement_summary=str(ai_plan.generated_plan.get("improvement_summary", "")),
        rejected_generic_count=int(
            ai_plan.generated_plan.get("rejected_generic_count") or 0
        ),
        rejected_unrelated_count=int(
            ai_plan.generated_plan.get("rejected_unrelated_count") or 0
        ),
        ai_generation_status=str(
            ai_plan.generated_plan.get("ai_generation_status", "generated")
        ),
        tasks=[
            AIPlanGeneratedTaskResponse(
                task_id=task.task_id,
                title=task.title,
                description=task.description,
                priority=task.priority,
                estimated_hours=(
                    float(task.estimated_hours)
                    if task.estimated_hours is not None
                    else None
                ),
                status=task.status,
                due_date=task.due_date,
            )
            for task in created_tasks
        ],
    )


def _derive_preview_project_title(project_idea: str) -> str:
    title = (
        re.split(r"[\n.!?]", project_idea.strip(), maxsplit=1)[0]
        .strip()
    )
    title = re.sub(
        r"^\s*i\s+want\s+to\s+",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(
        r"^\s*(build|create|start|launch)\s+",
        "",
        title,
        flags=re.IGNORECASE,
    ).strip()

    if not title:
        return "AI Generated Plan"

    if len(title) > 86:
        title = f"{title[:83].rstrip()}..."

    return title[0].upper() + title[1:]


def _build_preview_description(
    preview_data: AIPlanPreviewRequest,
) -> str:
    pieces = [
        "AI planning brief",
        "",
        f"Idea: {preview_data.project_idea.strip()}",
        f"Available hours per week: {preview_data.available_hours_per_week}",
        f"Preferred task count: {preview_data.preferred_task_count}",
    ]

    requirements = (preview_data.requirements or "").strip()

    if requirements:
        pieces.append(f"Notes and constraints: {requirements}")

    return "\n".join(pieces)


def _build_preview_prompt(
    preview_data: AIPlanPreviewRequest,
) -> str:
    pieces = [
        f"Project idea and goal:\n{preview_data.project_idea.strip()}",
    ]

    requirements = (preview_data.requirements or "").strip()

    if requirements:
        pieces.append(f"Extra notes, constraints, or preferences:\n{requirements}")

    return "\n\n".join(pieces)


def _preview_task_response_from_plan_task(
    task_data: dict[str, Any],
) -> AIPlanPreviewTaskResponse:
    return AIPlanPreviewTaskResponse(
        suggested_order=int(str(task_data.get("suggested_order") or 1)),
        title=str(task_data["title"]),
        description=str(task_data["description"]),
        priority=str(task_data["priority"]),
        estimated_hours=(
            float(task_data["estimated_hours"])
            if task_data.get("estimated_hours") is not None
            else None
        ),
        status=TaskStatus.todo.value,
        due_date=_parse_due_date(str(task_data["due_date"]))
        if task_data.get("due_date") is not None
        else None,
        assigned_to=task_data.get("assigned_to"),
    )


def _preview_summary_with_task_count(
    *,
    summary: str,
    project_title: str,
    task_count: int,
) -> str:
    cleaned = summary.strip()

    if not cleaned:
        return f"Generated a practical plan for {project_title} with {task_count} tasks."

    replacement = f"{task_count} tasks"
    updated = re.sub(
        r"\b\d+\s+(?:focused\s+)?tasks?\b",
        replacement,
        cleaned,
        count=1,
        flags=re.IGNORECASE,
    )

    if updated != cleaned:
        return updated

    if "task" in cleaned.lower():
        return cleaned

    return f"{cleaned} Plan includes {task_count} tasks."


def create_ai_plan_preview(
    preview_data: AIPlanPreviewRequest,
    current_user: User,
) -> AIPlanPreviewResponse:
    project = Project(
        project_id=0,
        created_by=current_user.user_id,
        team_id=preview_data.team_id,
        title=_derive_preview_project_title(preview_data.project_idea),
        description=_build_preview_description(preview_data),
        deadline=preview_data.deadline,
        status="not_started",
        project_type=preview_data.project_type.value,
    )

    generated_plan = build_generated_plan(
        project=project,
        input_prompt=_build_preview_prompt(preview_data),
        task_count=preview_data.preferred_task_count,
        include_milestones=preview_data.include_milestones,
        project_members=None,
        allow_local_fallback=True,
    )
    ai_generation_status = str(
        generated_plan.get("ai_generation_status", "generated")
    )

    if ai_generation_status not in {"generated", "fallback"}:
        ai_generation_status = "generated"
    tasks = [
        _preview_task_response_from_plan_task(task)
        for task in generated_plan["tasks"]
    ]
    summary = _preview_summary_with_task_count(
        summary=str(generated_plan["summary"]),
        project_title=project.title,
        task_count=len(tasks),
    )

    return AIPlanPreviewResponse(
        success=bool(generated_plan.get("success", True)),
        message=str(generated_plan.get("message", "")),
        ai_generation_status=ai_generation_status,
        source=str(generated_plan["source"]),
        domain=str(generated_plan["domain"]),
        project_title=project.title,
        description=project.description,
        project_type=preview_data.project_type,
        team_id=preview_data.team_id,
        deadline=preview_data.deadline,
        summary=summary,
        tasks=tasks,
        milestones=list(generated_plan["milestones"]),
        risks=list(generated_plan["risks"]),
        recommendations=list(generated_plan["recommendations"]),
        project_idea=preview_data.project_idea,
        requirements=preview_data.requirements,
        available_hours_per_week=preview_data.available_hours_per_week,
        preferred_task_count=preview_data.preferred_task_count,
        rejected_generic_count=int(generated_plan.get("rejected_generic_count") or 0),
        rejected_unrelated_count=int(
            generated_plan.get("rejected_unrelated_count") or 0
        ),
    )


def _generated_plan_from_preview(
    project: Project,
    preview: AIPlanPreviewResponse,
) -> dict[str, Any]:
    return {
        "success": preview.success,
        "message": preview.message,
        "ai_generation_status": preview.ai_generation_status,
        "source": preview.source,
        "domain": preview.domain,
        "summary": preview.summary,
        "rejected_generic_count": preview.rejected_generic_count,
        "rejected_unrelated_count": preview.rejected_unrelated_count,
        "project": {
            "project_id": project.project_id,
            "title": project.title,
            "project_type": project.project_type,
            "deadline": _to_utc(project.deadline).isoformat(),
        },
        "tasks": [
            {
                "suggested_order": task.suggested_order,
                "title": task.title,
                "description": task.description,
                "priority": task.priority,
                "estimated_hours": task.estimated_hours,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "assigned_to": task.assigned_to,
            }
            for task in preview.tasks
        ],
        "milestones": preview.milestones,
        "risks": preview.risks,
        "recommendations": preview.recommendations,
    }


def create_ai_plan_from_accepted_preview(
    db: Session,
    project: Project,
    current_user: User,
    accept_data: AIPlanAcceptPreviewRequest,
) -> AIPlanAcceptPreviewResponse:
    preview = accept_data.preview
    input_prompt = _build_preview_prompt(
        AIPlanPreviewRequest(
            project_idea=preview.project_idea,
            deadline=preview.deadline,
            project_type=preview.project_type,
            team_id=preview.team_id,
            available_hours_per_week=preview.available_hours_per_week,
            preferred_task_count=preview.preferred_task_count,
            requirements=preview.requirements,
        )
    )
    generated_plan = _generated_plan_from_preview(
        project=project,
        preview=preview,
    )

    ai_plan = AIPlan(
        project_id=project.project_id,
        generated_by=current_user.user_id,
        input_prompt=input_prompt,
        generated_plan=generated_plan,
    )

    db.add(ai_plan)
    db.flush()

    created_tasks, skipped_duplicate_count = _create_tasks_from_plan(
        db=db,
        project=project,
        current_user=current_user,
        generated_plan=generated_plan,
        existing_tasks=[],
    )
    created_task_ids = [task.task_id for task in created_tasks]
    ai_plan.generated_plan = {
        **generated_plan,
        "created_task_ids": created_task_ids,
        "tasks_created": len(created_task_ids),
        "tasks_skipped_as_duplicates": skipped_duplicate_count,
        "overwrite_existing_tasks": False,
        "overwritten_task_count": 0,
        "improvement_summary": str(generated_plan.get("summary", "")),
        "rejected_generic_count": int(
            generated_plan.get("rejected_generic_count") or 0
        ),
        "rejected_unrelated_count": int(
            generated_plan.get("rejected_unrelated_count") or 0
        ),
        "success": bool(generated_plan.get("success", True)),
        "message": str(generated_plan.get("message", "")),
        "ai_generation_status": str(
            generated_plan.get("ai_generation_status", "generated")
        ),
    }

    create_activity_log(
        db=db,
        project=project,
        actor=current_user,
        event_type=ActivityLogEventType.AI_PLAN_GENERATED,
        message=f"{current_user.full_name} accepted an AI preview for '{project.title}'.",
        metadata={
            "plan_id": ai_plan.plan_id,
            "created_task_count": len(created_task_ids),
            "created_task_ids": created_task_ids,
            "source": preview.source,
            "rejected_generic_count": int(
                generated_plan.get("rejected_generic_count") or 0
            ),
            "rejected_unrelated_count": int(
                generated_plan.get("rejected_unrelated_count") or 0
            ),
            "success": bool(generated_plan.get("success", True)),
            "ai_generation_status": str(
                generated_plan.get("ai_generation_status", "generated")
            ),
        },
        commit=False,
    )

    db.commit()
    db.refresh(project)
    db.refresh(ai_plan)

    for task in created_tasks:
        db.refresh(task)

    return AIPlanAcceptPreviewResponse(
        project=project,
        project_id=project.project_id,
        plan_id=ai_plan.plan_id,
        success=bool(ai_plan.generated_plan.get("success", True)),
        message=str(ai_plan.generated_plan.get("message", "")),
        summary=str(ai_plan.generated_plan.get("summary", "")),
        tasks_created=len(created_tasks),
        tasks_skipped_as_duplicates=skipped_duplicate_count,
        improvement_summary=str(ai_plan.generated_plan.get("improvement_summary", "")),
        rejected_generic_count=int(
            ai_plan.generated_plan.get("rejected_generic_count") or 0
        ),
        rejected_unrelated_count=int(
            ai_plan.generated_plan.get("rejected_unrelated_count") or 0
        ),
        ai_generation_status=str(
            ai_plan.generated_plan.get("ai_generation_status", "generated")
        ),
        tasks=[
            AIPlanGeneratedTaskResponse(
                task_id=task.task_id,
                title=task.title,
                description=task.description,
                priority=task.priority,
                estimated_hours=(
                    float(task.estimated_hours)
                    if task.estimated_hours is not None
                    else None
                ),
                status=task.status,
                due_date=task.due_date,
            )
            for task in created_tasks
        ],
    )


def get_ai_plans_for_project(
    db: Session,
    project: Project,
) -> list[AIPlan]:
    stmt = (
        select(AIPlan)
        .where(AIPlan.project_id == project.project_id)
        .order_by(AIPlan.created_at.desc(), AIPlan.plan_id.desc())
    )

    return list(db.execute(stmt).scalars().all())
