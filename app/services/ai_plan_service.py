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

GENERIC_FALLBACK_TITLE_PATTERNS = (
    r"^\s*clarify\s+the\s+next\s+outcome\b",
    r"^\s*break\b.*\binto\s+small\s+actions\b",
    r"^\s*schedule\s+focused\s+time\b",
    r"^\s*prepare\s+the\s+materials\b",
    r"^\s*start\s+the\s+first\s+visible\s+step\b",
    r"^\s*track\s+progress\s+and\s+blockers\b",
    r"^\s*review\s+results\s+and\s+adjust\b",
)

ACTION_VERBS = {
    "add",
    "adjust",
    "analyze",
    "ask",
    "build",
    "celebrate",
    "check",
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
    "keep",
    "list",
    "log",
    "make",
    "map",
    "measure",
    "name",
    "pick",
    "plan",
    "practice",
    "prepare",
    "prioritize",
    "publish",
    "record",
    "remove",
    "reward",
    "review",
    "run",
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

GENERIC_CONTEXT_TOKENS = {
    "available",
    "brief",
    "constraint",
    "constraints",
    "count",
    "deadline",
    "extra",
    "hour",
    "hours",
    "notes",
    "planning",
    "preferred",
    "task",
    "tasks",
    "week",
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


def _has_meaningful_idea_token_overlap(source: str, candidate: str) -> bool:
    source_tokens = _quality_tokens(source) - GENERIC_CONTEXT_TOKENS
    candidate_tokens = _quality_tokens(candidate) - GENERIC_CONTEXT_TOKENS

    return bool(source_tokens & candidate_tokens)


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


def _looks_like_software_or_product_context(project_context: str) -> bool:
    lowered = project_context.lower()
    software_product_markers = (
        "app",
        "application",
        "software",
        "website",
        "web site",
        "api",
        "backend",
        "frontend",
        "mobile",
        "saas",
        "platform",
        "product",
        "prototype",
        "release",
        "mvp",
        "feature",
        "user flow",
    )

    return any(marker in lowered for marker in software_product_markers)


def _uses_wrong_domain_product_language(
    *,
    project_context: str,
    task_text: str,
) -> bool:
    if _looks_like_software_or_product_context(project_context):
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
        "core flow",
        "prototype",
        "release",
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


def _fallback_user_idea_text(
    project: Project,
    input_prompt: str,
) -> str:
    lines = input_prompt.splitlines()
    pieces: list[str] = []
    pieces.extend(
        _extract_section_lines(
            lines=lines,
            start_label="project idea and goal:",
            stop_labels=(
                "extra notes, constraints, or preferences:",
                "user idea and context:",
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

    if pieces:
        return "\n".join(
            dict.fromkeys(piece.strip() for piece in pieces if piece.strip())
        )

    description_lines = (project.description or "").splitlines()
    idea = _extract_labeled_value(description_lines, "Idea")
    notes = _extract_labeled_value(description_lines, "Notes and constraints")
    pieces.extend(
        value.strip()
        for value in (idea, notes, project.title)
        if value and value.strip()
    )

    return "\n".join(dict.fromkeys(pieces)) or project.title


def _fallback_plural(value: str) -> str:
    if value.endswith("s"):
        return value

    return f"{value}s"


GERUND_VERBS = {
    "add": "adding",
    "build": "building",
    "clean": "cleaning",
    "cook": "cooking",
    "create": "creating",
    "do": "doing",
    "finish": "finishing",
    "fix": "fixing",
    "grow": "growing",
    "improve": "improving",
    "learn": "learning",
    "make": "making",
    "organize": "organizing",
    "plan": "planning",
    "practice": "practicing",
    "prepare": "preparing",
    "read": "reading",
    "run": "running",
    "save": "saving",
    "start": "starting",
    "study": "studying",
    "teach": "teaching",
    "train": "training",
    "write": "writing",
}


def _pluralize_counted_terms(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        number = match.group(1)
        word = match.group(2)

        if word.endswith("s"):
            return match.group(0)

        return f"{number} {_fallback_plural(word)}"

    return re.sub(
        r"\b([2-9]\d*|1\d+)\s+([a-zA-Z][a-zA-Z'-]{2,})\b",
        replace,
        value,
    )


def _clean_display_phrase_from_idea(idea_text: str, fallback: str) -> str:
    first_line = next(
        (line.strip() for line in idea_text.splitlines() if line.strip()),
        fallback,
    )
    cleaned = re.sub(
        r"^(idea|project idea|project idea and goal|user idea and context)\s*:\s*",
        "",
        first_line,
        flags=re.IGNORECASE,
    ).strip()
    cleaned = re.sub(
        r"^(i\s+want\s+to|i\s+need\s+to|please|can\s+you)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")

    if not cleaned:
        cleaned = fallback

    lowered = cleaned[:1].lower() + cleaned[1:]
    words = lowered.split(" ", 1)
    first_word = words[0].lower()

    if first_word in GERUND_VERBS:
        remainder = words[1].strip() if len(words) > 1 else ""

        if remainder:
            remainder_words = remainder.split()

            if (
                len(remainder_words) == 1
                and remainder_words[0].isalpha()
                and remainder_words[0].lower() not in {"a", "an", "the"}
            ):
                lowered = f"{GERUND_VERBS[first_word]} a {remainder}"
            else:
                lowered = f"{GERUND_VERBS[first_word]} {remainder}"
        else:
            lowered = GERUND_VERBS[first_word]

    lowered = _pluralize_counted_terms(lowered)

    return _clean_ai_text_field(
        lowered,
        fallback=fallback.lower(),
        max_length=80,
    )


def _fallback_task_description(
    *,
    goal: str,
    steps: list[str],
    deliverable: str,
    done_when: str,
    why: str,
) -> str:
    numbered_steps = "\n".join(
        f"{index}. {step.strip()}"
        for index, step in enumerate(steps[:5], start=1)
        if step.strip()
    )

    return (
        f"Goal: {goal}\n\n"
        f"Steps:\n{numbered_steps}\n\n"
        f"Deliverable: {deliverable}\n\n"
        f"Done when: {done_when}\n\n"
        f"Why it matters: {why}"
    )


def _local_secondary_fallback_specs(display_phrase: str) -> list[dict[str, Any]]:
    return [
        {
            "title": f"Name one measurable result for {display_phrase}",
            "goal": f"Choose one small result that proves progress on {display_phrase}.",
            "steps": [
                "Write the result in one plain sentence.",
                "Add two details that make the result observable.",
                "Circle the smallest version that can be attempted first.",
            ],
            "deliverable": "A short result note with observable done signals.",
            "done_when": "The result note names one target and two observable details.",
            "why": "A narrow target keeps the fallback plan usable while AI detail is unavailable.",
        },
        {
            "title": f"List the real-world parts of {display_phrase}",
            "goal": f"Identify the people, tools, places, or signals involved in {display_phrase}.",
            "steps": [
                "Write the physical items or information you already have.",
                "Write the missing items or decisions that block the next attempt.",
                "Mark the one missing item that matters most.",
            ],
            "deliverable": "A readiness list with available, missing, and blocked items.",
            "done_when": "The readiness list shows the most important missing item.",
            "why": "Knowing what is ready prevents vague work from replacing action.",
        },
        {
            "title": f"Set one short session for {display_phrase}",
            "goal": f"Give {display_phrase} a repeatable time box instead of an open-ended effort.",
            "steps": [
                "Choose a short session length you can finish without rushing.",
                "Pick a specific day and time for the first session.",
                "Write what you will do first when the session begins.",
            ],
            "deliverable": "A dated session note with length, time, and first action.",
            "done_when": "The first session has a date, duration, and opening action.",
            "why": "Short sessions make the fallback plan easier to start and repeat.",
        },
        {
            "title": f"Run the first small attempt at {display_phrase}",
            "goal": f"Create real feedback from doing a small part of {display_phrase}.",
            "steps": [
                "Use the result note to choose one small attempt.",
                "Do only that attempt during the first session.",
                "Stop and write what worked, what was confusing, and what changed.",
            ],
            "deliverable": "A first-attempt note with worked, confusing, and changed sections.",
            "done_when": "The note records at least one observation from the attempt.",
            "why": "A small attempt gives better information than planning from memory.",
        },
        {
            "title": f"Record evidence from {display_phrase}",
            "goal": f"Track what is happening so {display_phrase} can improve over time.",
            "steps": [
                "Choose one simple measure that matches the result note.",
                "Record the measure after each attempt.",
                "Add one sentence about the next adjustment.",
            ],
            "deliverable": "A progress tracker with measure, observation, and next adjustment.",
            "done_when": "The tracker has one row for the latest attempt.",
            "why": "Evidence keeps the fallback plan from becoming generic busywork.",
        },
        {
            "title": f"Adjust the next attempt for {display_phrase}",
            "goal": f"Use the latest evidence to choose the next version of {display_phrase}.",
            "steps": [
                "Read the latest observation from the progress tracker.",
                "Choose one thing to keep the same.",
                "Choose one thing to change in the next session.",
            ],
            "deliverable": "A next-attempt note with one keep and one change.",
            "done_when": "The next-attempt note is written before the next session begins.",
            "why": "A single adjustment helps progress without adding complexity.",
        },
        {
            "title": f"Repeat the strongest action for {display_phrase}",
            "goal": f"Reinforce the part of {display_phrase} that produced the clearest progress.",
            "steps": [
                "Pick the action that worked best in the tracker.",
                "Repeat it under similar conditions.",
                "Record whether the result improved, stayed the same, or got worse.",
            ],
            "deliverable": "A comparison note for the repeated action.",
            "done_when": "The comparison note shows whether the repeated action helped.",
            "why": "Repeating what works turns one-off progress into a usable pattern.",
        },
        {
            "title": f"Review the next target for {display_phrase}",
            "goal": f"Choose a next target for {display_phrase} from actual results.",
            "steps": [
                "Review the result note, readiness list, and progress tracker.",
                "Write the strongest evidence of progress.",
                "Choose the next target that follows from that evidence.",
            ],
            "deliverable": "A review note with evidence and the next target.",
            "done_when": "The next target is selected from recorded results.",
            "why": "Review keeps the plan grounded when AI-specific detail is unavailable.",
        },
        {
            "title": f"Prepare the next session for {display_phrase}",
            "goal": f"Make the next session for {display_phrase} easy to start.",
            "steps": [
                "Copy the next target into a fresh session note.",
                "Put any needed items or information in one place.",
                "Set a start time and a stop time.",
            ],
            "deliverable": "A prepared session note with target, items, and timing.",
            "done_when": "The next session can start without searching for missing pieces.",
            "why": "Preparation protects momentum after the first review.",
        },
        {
            "title": f"Write a simple consistency rule for {display_phrase}",
            "goal": f"Keep {display_phrase} moving even when the original plan needs editing.",
            "steps": [
                "Choose the minimum session length you will still count.",
                "Choose what to do when the session is missed.",
                "Choose when to review the rule again.",
            ],
            "deliverable": "A consistency rule with minimum, missed-session, and review parts.",
            "done_when": "The consistency rule is written and visible before the next session.",
            "why": "A simple rule helps the fallback plan survive interruptions.",
        },
    ]


def _build_adaptive_fallback_tasks(
    project: Project,
    input_prompt: str,
    task_count: int,
) -> list[dict[str, Any]]:
    idea_text = _fallback_user_idea_text(project=project, input_prompt=input_prompt)
    display_phrase = _clean_display_phrase_from_idea(
        idea_text=idea_text,
        fallback=project.title,
    )
    specs = _local_secondary_fallback_specs(display_phrase)
    due_dates = _build_ai_due_dates(project=project, task_count=task_count)
    tasks: list[dict[str, Any]] = []

    for index in range(task_count):
        spec = specs[index % len(specs)]
        title = str(spec["title"])

        if index >= len(specs):
            title = f"{title} again"

        tasks.append(
            {
                "suggested_order": index + 1,
                "title": _clean_ai_text_field(
                    title,
                    fallback=f"Review next action for {display_phrase}",
                    max_length=120,
                ),
                "description": _fallback_task_description(
                    goal=str(spec["goal"]),
                    steps=[str(step) for step in spec["steps"]],
                    deliverable=str(spec["deliverable"]),
                    done_when=str(spec["done_when"]),
                    why=str(spec["why"]),
                ),
                "priority": _priority_for_index(index=index, task_count=task_count),
                "estimated_hours": _estimated_hours_for_index(index),
                "due_date": (
                    due_dates[index]
                    if index < len(due_dates)
                    else None
                ),
                "assigned_to": None,
            }
        )

    return tasks


def _build_adaptive_fallback_milestones(
    include_milestones: bool,
) -> list[dict[str, Any]]:
    if not include_milestones:
        return []

    return [
        {
            "name": "Starting point chosen",
            "description": "The first target, boundaries, and next action are clear.",
            "suggested_order": 1,
        },
        {
            "name": "Routine underway",
            "description": "The main actions are scheduled, started, and being tracked.",
            "suggested_order": 2,
        },
        {
            "name": "Progress reviewed",
            "description": "Results are reviewed and the next adjustment is chosen.",
            "suggested_order": 3,
        },
    ]


def _build_adaptive_fallback_risks() -> list[dict[str, str]]:
    return [
        {
            "risk": "The goal may be too broad or too aggressive at first.",
            "recommendation": "Start with the smallest repeatable action and adjust after real results.",
        },
        {
            "risk": "Provider-generated detail was unavailable.",
            "recommendation": "Review the fallback tasks and edit any assumptions before accepting the plan.",
        },
    ]


def _build_adaptive_fallback_recommendations() -> list[str]:
    return [
        "Start with the smallest repeatable action.",
        "Track what changes after each session.",
        "Adjust the plan when the evidence changes.",
    ]


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

    tasks = _build_adaptive_fallback_tasks(
        project=project,
        input_prompt=input_prompt,
        task_count=task_count,
    )

    logger.info(
        "AI Planner fallback used. source=adaptive_fallback_v1 task_count=%s",
        len(tasks),
    )
    return {
        "success": True,
        "message": "Generated a fallback plan from the idea.",
        "ai_generation_status": "fallback",
        "source": "adaptive_fallback_v1",
        "domain": "adaptive_plan",
        "summary": (
            f"Generated an adaptive plan for '{project.title}' with {len(tasks)} tasks."
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
        "milestones": _build_adaptive_fallback_milestones(include_milestones),
        "risks": _build_adaptive_fallback_risks(),
        "recommendations": _build_adaptive_fallback_recommendations(),
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
    logger.warning(
        "AI Planner provider failed. reason=%s project_id=%s allow_fallback=%s",
        reason,
        project.project_id,
        allow_local_fallback,
    )

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

Infer a short natural domain label from the user's words and put it in the domain field.
Generate a plan that fits the user's actual situation.
- Use software/product wording only when the idea is clearly an app, website, software tool, or product build.
- For personal goals, routines, health goals, learning goals, events, creative work, and other non-software ideas, write like a practical coach for that exact goal.
- Do not force personal ideas into features, requirements, MVPs, user flows, releases, prototypes, or customer language.
- If the idea is not clearly software or product work, do not use: requirements, features, MVP, first useful version, core flow, customer benefit, prototype, release, or idea goal.
- Use concrete nouns, tools, actions, constraints, and signals from the real-world activity in the user's idea.
- For "Train a dog", tasks should mention dog-training concepts such as commands, treats, reward timing, short sessions, leash practice, distractions, consistency, learned behaviors, sit, stay, recall, or potty routines.
- For "Do 100 pushup a day", tasks should mention pushups, reps, sets, form, daily target, progression, recovery, soreness, pain rules, or tracking.
- For any other idea, infer the real activity from the idea itself and use the vocabulary a knowledgeable human would use for that activity.

Critical output rules:
- Return valid JSON only.
- No Markdown.
- No code fences.
- No text outside JSON.
- Generate exactly {task_count} tasks.
- Task titles must start with an action verb.
- Task titles must be specific to the user's idea.
- Avoid vague titles like "Research", "Plan project", "Work on the task", "Prepare strategy", or "Finish project".
- Avoid generic fallback titles like "Clarify the next outcome", "Break into small actions", "Schedule focused time", "Prepare the materials", "Start the first visible step", "Track progress and blockers", or "Review results and adjust".
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


def _is_generic_fallback_style_title(title: str) -> bool:
    normalized = _normalize_comparison_text(title)
    return _matches_any_pattern(normalized, GENERIC_FALLBACK_TITLE_PATTERNS)


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


def _build_concrete_regeneration_prompt(
    *,
    original_prompt: str,
    project_context: str,
    rejected_tasks: list[dict[str, Any]],
    task_count: int,
    include_milestones: bool,
) -> str:
    return f"""
You are Planora AI.

The previous planner output was too generic or did not pass quality validation.
Regenerate the complete plan from the user's idea, not from reusable productivity templates.

User idea and context:
{project_context}

Original planning prompt:
{original_prompt}

Rejected task samples:
{json.dumps(rejected_tasks[:8], ensure_ascii=False, indent=2)}

Concrete activity rules:
- Understand the idea naturally and infer the real-world activity.
- Use concrete nouns, tools, actions, constraints, and signals from that activity.
- Do not assume the idea is software/product unless the user explicitly says app, website, software, platform, API, dashboard, SaaS, or similar.
- For "Train a dog", use dog-training vocabulary such as command, treat, reward marker, leash, short session, behavior, sit, stay, recall, potty, distraction, or consistency.
- For "Do 100 pushup a day", use pushup vocabulary such as reps, sets, form, daily target, progression, recovery, soreness, pain rule, or tracker.
- For every other idea, use the real vocabulary a knowledgeable human would use for that activity.
- Do not use generic titles like "Clarify the next outcome", "Break into small actions", "Schedule focused time", "Prepare the materials", "Start the first visible step", "Track progress and blockers", or "Review results and adjust".
- Do not use product-management words unless the user clearly asked for software/product work.

Return valid JSON only. No Markdown. No code fences.
Generate exactly {task_count} tasks.
Every task description must include these exact labels:
Goal:
Steps:
Deliverable:
Done when:
Why it matters:

Return JSON in exactly this shape:
{{
  "domain": "short natural label inferred from the user idea",
  "summary": "short summary that mentions {task_count} tasks",
  "tasks": [
    {{
      "suggested_order": 1,
      "title": "specific action title using real activity vocabulary",
      "description": "Goal: ...\\n\\nSteps:\\n1. ...\\n2. ...\\n3. ...\\n\\nDeliverable: ...\\n\\nDone when: ...\\n\\nWhy it matters: ...",
      "priority": "high",
      "estimated_hours": 2
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


def _try_regenerate_concrete_ai_plan(
    *,
    project: Project,
    input_prompt: str,
    original_prompt: str,
    task_count: int,
    include_milestones: bool,
    existing_tasks: list[Task] | None,
    rejected_tasks: list[dict[str, Any]],
) -> dict[str, Any] | None:
    regeneration_prompt = _build_concrete_regeneration_prompt(
        original_prompt=original_prompt,
        project_context=_extract_user_project_context(project, input_prompt),
        rejected_tasks=rejected_tasks,
        task_count=task_count,
        include_milestones=include_milestones,
    )
    logger.info(
        "AI Planner provider attempted. reason=quality_regeneration project_id=%s requested_task_count=%s",
        project.project_id,
        task_count,
    )
    regeneration_reply = _generate_ai_plan_reply_from_provider(regeneration_prompt)

    if regeneration_reply is None:
        logger.warning(
            "AI Planner regeneration provider failed. reason=provider_unavailable project_id=%s",
            project.project_id,
        )
        return None

    regeneration_data = _parse_json_object(regeneration_reply)

    if regeneration_data is None:
        logger.warning(
            "AI Planner regeneration parse failed. project_id=%s",
            project.project_id,
        )
        return None

    regenerated_plan = _normalize_ai_plan_response(
        ai_data=regeneration_data,
        project=project,
        input_prompt=input_prompt,
        task_count=task_count,
        include_milestones=include_milestones,
        existing_tasks=existing_tasks,
        ai_generation_status="generated",
    )

    if regenerated_plan is None or len(regenerated_plan["tasks"]) < task_count:
        logger.warning(
            "AI Planner regeneration failed quality validation. project_id=%s accepted_task_count=%s requested_task_count=%s",
            project.project_id,
            len(regenerated_plan["tasks"]) if regenerated_plan is not None else 0,
            task_count,
        )
        return None

    regenerated_plan["tasks"] = regenerated_plan["tasks"][:task_count]
    logger.info(
        "AI Planner regeneration succeeded. project_id=%s task_count=%s",
        project.project_id,
        len(regenerated_plan["tasks"]),
    )
    return regenerated_plan


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

    if (
        _is_low_quality_task_title(title)
        or _is_disallowed_generic_task_title(title)
        or _is_generic_fallback_style_title(title)
    ):
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

    if relevance_score < 0.18 and not _has_meaningful_idea_token_overlap(
        project_context,
        combined_task_text,
    ):
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


def _should_regenerate_full_plan(
    generated_plan: dict[str, Any],
    task_count: int,
) -> bool:
    rejected_tasks = generated_plan.get("rejected_tasks")

    if not isinstance(rejected_tasks, list):
        return False

    rejected_count = len(rejected_tasks)
    accepted_count = len(generated_plan.get("tasks") or [])

    if rejected_count < max(2, task_count // 2):
        return False

    generic_rejections = 0

    for rejected_task in rejected_tasks:
        if not isinstance(rejected_task, dict):
            continue

        reasons = rejected_task.get("reasons")

        if isinstance(reasons, list) and any(
            reason in {"generic_title", "generic_description", "not_specific_enough"}
            for reason in reasons
        ):
            generic_rejections += 1

    return generic_rejections >= accepted_count


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

    logger.info(
        "AI Planner provider attempted. project_id=%s requested_task_count=%s include_milestones=%s",
        project.project_id,
        task_count,
        include_milestones,
    )
    provider_reply = _generate_ai_plan_reply_from_provider(prompt)

    if provider_reply is None:
        regenerated_plan = _try_regenerate_concrete_ai_plan(
            project=project,
            input_prompt=input_prompt,
            original_prompt=prompt,
            task_count=task_count,
            include_milestones=include_milestones,
            existing_tasks=existing_tasks,
            rejected_tasks=[],
        )

        if regenerated_plan is not None:
            return regenerated_plan

        return _build_failed_or_fallback_generated_plan(
            project=project,
            input_prompt=input_prompt,
            task_count=task_count,
            include_milestones=include_milestones,
            reason="provider_unavailable_after_retry",
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
            regenerated_plan = _try_regenerate_concrete_ai_plan(
                project=project,
                input_prompt=input_prompt,
                original_prompt=prompt,
                task_count=task_count,
                include_milestones=include_milestones,
                existing_tasks=existing_tasks,
                rejected_tasks=[],
            )

            if regenerated_plan is not None:
                return regenerated_plan

            return _build_failed_or_fallback_generated_plan(
                project=project,
                input_prompt=input_prompt,
                task_count=task_count,
                include_milestones=include_milestones,
                reason="json_repair_provider_unavailable_after_retry",
                allow_local_fallback=allow_local_fallback,
            )

        parsed = _parse_json_object(repaired_reply)
        ai_generation_status = "repaired"

        if parsed is None:
            regenerated_plan = _try_regenerate_concrete_ai_plan(
                project=project,
                input_prompt=input_prompt,
                original_prompt=prompt,
                task_count=task_count,
                include_milestones=include_milestones,
                existing_tasks=existing_tasks,
                rejected_tasks=[],
            )

            if regenerated_plan is not None:
                return regenerated_plan

            return _build_failed_or_fallback_generated_plan(
                project=project,
                input_prompt=input_prompt,
                task_count=task_count,
                include_milestones=include_milestones,
                reason="json_parse_failed_after_repair_and_retry",
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
        regenerated_plan = _try_regenerate_concrete_ai_plan(
            project=project,
            input_prompt=input_prompt,
            original_prompt=prompt,
            task_count=task_count,
            include_milestones=include_milestones,
            existing_tasks=existing_tasks,
            rejected_tasks=[],
        )

        if regenerated_plan is not None:
            return regenerated_plan

        return _build_failed_or_fallback_generated_plan(
            project=project,
            input_prompt=input_prompt,
            task_count=task_count,
            include_milestones=include_milestones,
            reason="normalized_plan_invalid_after_retry",
            allow_local_fallback=allow_local_fallback,
        )

    if not normalized_plan["tasks"] and not allow_zero_tasks:
        regenerated_plan = _try_regenerate_concrete_ai_plan(
            project=project,
            input_prompt=input_prompt,
            original_prompt=prompt,
            task_count=task_count,
            include_milestones=include_milestones,
            existing_tasks=existing_tasks,
            rejected_tasks=list(normalized_plan.get("rejected_tasks") or []),
        )

        if regenerated_plan is not None:
            return regenerated_plan

        return _build_failed_or_fallback_generated_plan(
            project=project,
            input_prompt=input_prompt,
            task_count=task_count,
            include_milestones=include_milestones,
            reason="all_tasks_rejected_after_retry",
            allow_local_fallback=allow_local_fallback,
            rejected_generic_count=int(
                normalized_plan.get("rejected_generic_count") or 0
            ),
            rejected_unrelated_count=int(
                normalized_plan.get("rejected_unrelated_count") or 0
            ),
            rejected_tasks=list(normalized_plan.get("rejected_tasks") or []),
        )

    if (
        not normalized_plan["tasks"]
        and allow_zero_tasks
        and _has_only_duplicate_rejections(normalized_plan)
    ):
        normalized_plan["message"] = PLAN_ALREADY_COVERS_MESSAGE
        normalized_plan["summary"] = PLAN_ALREADY_COVERS_MESSAGE
        return normalized_plan

    if _should_regenerate_full_plan(normalized_plan, task_count):
        regenerated_plan = _try_regenerate_concrete_ai_plan(
            project=project,
            input_prompt=input_prompt,
            original_prompt=prompt,
            task_count=task_count,
            include_milestones=include_milestones,
            existing_tasks=existing_tasks,
            rejected_tasks=list(normalized_plan.get("rejected_tasks") or []),
        )

        if regenerated_plan is not None:
            return regenerated_plan

        return _build_failed_or_fallback_generated_plan(
            project=project,
            input_prompt=input_prompt,
            task_count=task_count,
            include_milestones=include_milestones,
            reason="mostly_generic_plan_after_retry",
            allow_local_fallback=allow_local_fallback,
            rejected_generic_count=int(
                normalized_plan.get("rejected_generic_count") or 0
            ),
            rejected_unrelated_count=int(
                normalized_plan.get("rejected_unrelated_count") or 0
            ),
            rejected_tasks=list(normalized_plan.get("rejected_tasks") or []),
        )

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
        regenerated_plan = _try_regenerate_concrete_ai_plan(
            project=project,
            input_prompt=input_prompt,
            original_prompt=prompt,
            task_count=task_count,
            include_milestones=include_milestones,
            existing_tasks=existing_tasks,
            rejected_tasks=list(normalized_plan.get("rejected_tasks") or []),
        )

        if regenerated_plan is not None:
            return regenerated_plan

        return _build_failed_or_fallback_generated_plan(
            project=project,
            input_prompt=input_prompt,
            task_count=task_count,
            include_milestones=include_milestones,
            reason="replacement_provider_unavailable_after_retry",
            allow_local_fallback=allow_local_fallback,
            rejected_generic_count=int(normalized_plan.get("rejected_generic_count") or 0),
            rejected_unrelated_count=int(
                normalized_plan.get("rejected_unrelated_count") or 0
            ),
            rejected_tasks=list(normalized_plan.get("rejected_tasks") or []),
        )

    replacement_data = _parse_json_object(replacement_reply)

    if replacement_data is None:
        regenerated_plan = _try_regenerate_concrete_ai_plan(
            project=project,
            input_prompt=input_prompt,
            original_prompt=prompt,
            task_count=task_count,
            include_milestones=include_milestones,
            existing_tasks=existing_tasks,
            rejected_tasks=list(normalized_plan.get("rejected_tasks") or []),
        )

        if regenerated_plan is not None:
            return regenerated_plan

        return _build_failed_or_fallback_generated_plan(
            project=project,
            input_prompt=input_prompt,
            task_count=task_count,
            include_milestones=include_milestones,
            reason="replacement_json_parse_failed_after_retry",
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

        regenerated_plan = _try_regenerate_concrete_ai_plan(
            project=project,
            input_prompt=input_prompt,
            original_prompt=prompt,
            task_count=task_count,
            include_milestones=include_milestones,
            existing_tasks=existing_tasks,
            rejected_tasks=rejected_tasks,
        )

        if regenerated_plan is not None:
            return regenerated_plan

        return _build_failed_or_fallback_generated_plan(
            project=project,
            input_prompt=input_prompt,
            task_count=task_count,
            include_milestones=include_milestones,
            reason="replacement_normalized_plan_invalid_after_retry",
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
    task_count_pattern = r"\b\d+\s+(?:focused\s+)?tasks?\b"

    if re.search(task_count_pattern, cleaned, flags=re.IGNORECASE):
        return re.sub(
            task_count_pattern,
            replacement,
            cleaned,
            count=1,
            flags=re.IGNORECASE,
        )

    return f"{cleaned} Plan includes {task_count} tasks."


def create_ai_plan_preview(
    preview_data: AIPlanPreviewRequest,
    current_user: User,
) -> AIPlanPreviewResponse:
    preview_prompt = _build_preview_prompt(preview_data)
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
        input_prompt=preview_prompt,
        task_count=preview_data.preferred_task_count,
        include_milestones=preview_data.include_milestones,
        project_members=None,
        allow_local_fallback=True,
    )

    if not generated_plan.get("tasks"):
        logger.warning(
            "AI Planner preview fallback forced. reason=empty_task_list project_id=%s",
            project.project_id,
        )
        generated_plan = _build_local_fallback_generated_plan(
            project=project,
            input_prompt=preview_prompt,
            task_count=preview_data.preferred_task_count,
            include_milestones=preview_data.include_milestones,
            reason="empty_task_list",
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
        preferred_task_count=len(tasks),
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
