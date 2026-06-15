from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_AI_REPLY_LENGTH = 30000
MAX_LOCAL_TASK_COUNT = 12

LOCAL_STOPWORDS = {
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
    "project",
    "that",
    "the",
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


def _clean_ai_text(value: str) -> str:
    cleaned = value.strip()

    if len(cleaned) > MAX_AI_REPLY_LENGTH:
        return cleaned[:MAX_AI_REPLY_LENGTH].rstrip() + "..."

    return cleaned


def _extract_gemini_text(response_data: dict[str, Any]) -> str | None:
    candidates = response_data.get("candidates", [])

    if not candidates:
        logger.warning(
            "Gemini response did not include candidates. response_keys=%s",
            sorted(response_data.keys()),
        )
        return None

    content = candidates[0].get("content", {})
    parts = content.get("parts", [])

    for part in parts:
        text = part.get("text")

        if isinstance(text, str) and text.strip():
            return _clean_ai_text(text)

    logger.warning("Gemini response did not include text parts.")

    return None


def _generate_with_gemini(
    prompt: str,
    response_mime_type: str | None = None,
) -> str | None:
    if not settings.gemini_api_key:
        logger.warning("Gemini API key is missing. Using local planner fallback.")
        return None

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )

    generation_config: dict[str, Any] = {
        "temperature": 0.25,
        "maxOutputTokens": 8192,
    }

    if response_mime_type:
        generation_config["responseMimeType"] = response_mime_type

    payload: dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt,
                    }
                ],
            }
        ],
        "generationConfig": generation_config,
    }

    params = {
        "key": settings.gemini_api_key,
    }

    try:
        with httpx.Client(timeout=settings.gemini_timeout_seconds) as client:
            response = client.post(
                url,
                params=params,
                json=payload,
            )

        logger.info("Gemini API response. status=%s", response.status_code)

        if response.status_code >= 400:
            logger.warning(
                "Gemini API error. status=%s body=%s. Using local planner fallback.",
                response.status_code,
                response.text[:800],
            )
            return None

        return _extract_gemini_text(response.json())

    except httpx.TimeoutException as exc:
        logger.warning("Gemini API timeout: %s. Using local planner fallback.", type(exc).__name__)
        return None

    except httpx.HTTPError as exc:
        logger.warning("Gemini HTTP error: %s. Using local planner fallback.", type(exc).__name__)
        return None

    except (KeyError, IndexError, TypeError, ValueError) as exc:
        logger.warning(
            "Gemini response parsing error: %s. Using local planner fallback.",
            type(exc).__name__,
        )
        return None


def _extract_task_count(prompt: str) -> int:
    patterns = (
        r"Generate exactly\s+(\d+)\s+replacement task",
        r"Generate exactly\s+(\d+)\s+tasks",
        r"preferred task count:\s*(\d+)",
    )

    for pattern in patterns:
        match = re.search(pattern, prompt, flags=re.IGNORECASE)

        if match is None:
            continue

        try:
            return max(1, min(MAX_LOCAL_TASK_COUNT, int(match.group(1))))
        except ValueError:
            continue

    return 6


def _extract_section(
    prompt: str,
    start_label: str,
    stop_labels: tuple[str, ...],
) -> str:
    start_index = prompt.lower().find(start_label.lower())

    if start_index == -1:
        return ""

    section = prompt[start_index + len(start_label) :]
    stop_indexes = [
        index
        for label in stop_labels
        if (index := section.lower().find(label.lower())) != -1
    ]

    if stop_indexes:
        section = section[: min(stop_indexes)]

    return section.strip()


def _extract_labeled_value(prompt: str, label: str) -> str:
    pattern = rf"^\s*-\s*{re.escape(label)}:\s*(.+?)\s*$"
    match = re.search(pattern, prompt, flags=re.IGNORECASE | re.MULTILINE)

    if match is None:
        return ""

    return match.group(1).strip()


def _extract_original_prompt(prompt: str) -> str:
    original_prompt = _extract_section(
        prompt=prompt,
        start_label="Original prompt:",
        stop_labels=("Invalid provider reply:",),
    )

    if original_prompt:
        return original_prompt

    original_planning_prompt = _extract_section(
        prompt=prompt,
        start_label="Original planning prompt:",
        stop_labels=("Accepted tasks to avoid duplicating:",),
    )

    if original_planning_prompt:
        return original_planning_prompt

    return prompt


def _clean_plain_text(value: str, max_length: int = 900) -> str:
    cleaned = re.sub(r'[`*_#>"\']+', ' ', value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:\n\t")

    if len(cleaned) > max_length:
        cleaned = cleaned[: max_length - 3].rstrip() + "..."

    return cleaned


def _extract_idea_context(prompt: str) -> str:
    source_prompt = _extract_original_prompt(prompt)
    idea = _extract_section(
        prompt=source_prompt,
        start_label="User idea and requirements:",
        stop_labels=("Return JSON", "Milestones:"),
    )

    if idea:
        return _clean_plain_text(idea)

    project_context = _extract_section(
        prompt=prompt,
        start_label="Original user/project context:",
        stop_labels=("Original planning prompt:",),
    )

    if project_context:
        return _clean_plain_text(project_context)

    title = _extract_labeled_value(source_prompt, "title")
    description = _extract_labeled_value(source_prompt, "description")
    combined = " ".join(value for value in (title, description) if value)

    if combined:
        return _clean_plain_text(combined)

    return _clean_plain_text(source_prompt[:900]) or "the project"


def _extract_project_title(prompt: str, idea_context: str) -> str:
    source_prompt = _extract_original_prompt(prompt)
    title = _extract_labeled_value(source_prompt, "title")

    if title and title.lower() != "none":
        return _clean_plain_text(title, max_length=80)

    words = _topic_words(idea_context, max_words=5)
    return " ".join(words).title() if words else "Project Plan"


def _topic_words(value: str, max_words: int = 4) -> list[str]:
    words: list[str] = []

    for token in re.findall(r"[\w'-]{3,}", value.lower(), flags=re.UNICODE):
        normalized = token.strip("'-_")

        if (
            not normalized
            or normalized in LOCAL_STOPWORDS
            or normalized.isdigit()
            or normalized in words
        ):
            continue

        words.append(normalized)

        if len(words) >= max_words:
            break

    return words


def _human_topic(value: str) -> str:
    words = _topic_words(value, max_words=4)

    if not words:
        return "project"

    return " ".join(words)


def _title_topic(value: str) -> str:
    topic = _human_topic(value)
    return topic if len(topic) <= 48 else topic[:45].rstrip() + "..."


def _local_task_description(
    *,
    topic: str,
    goal: str,
    steps: tuple[str, str, str],
    deliverable: str,
    done_when: str,
    benefit: str,
) -> str:
    return (
        f"Goal: {goal}\n\n"
        "Steps:\n"
        f"1. {steps[0]}\n"
        f"2. {steps[1]}\n"
        f"3. {steps[2]}\n\n"
        f"Deliverable: {deliverable}\n\n"
        f"Done when: {done_when}\n\n"
        f"Customer benefit: {benefit}"
    ).replace("{topic}", topic)


def _build_local_tasks(topic: str, task_count: int) -> list[dict[str, Any]]:
    blueprints = [
        {
            "title": "Define {topic} success criteria",
            "goal": "Set a clear target for {topic} before spending time on execution.",
            "steps": (
                "Write the main problem {topic} should solve.",
                "List the must-have results and the nice-to-have results.",
                "Choose 3 measurable success checks for the first version.",
            ),
            "deliverable": "A short success criteria document for {topic}.",
            "done_when": "The document has one goal, at least 3 success checks, and a clear first-version scope.",
            "benefit": "The user gets a focused direction instead of building random features.",
            "priority": "high",
            "estimated_hours": 1.5,
        },
        {
            "title": "Map {topic} requirements",
            "goal": "Turn the idea into practical requirements that can be executed.",
            "steps": (
                "Separate required features, optional features, and constraints for {topic}.",
                "Mark each requirement as simple, medium, or complex.",
                "Remove anything that does not support the first useful version.",
            ),
            "deliverable": "A prioritized requirements checklist for {topic}.",
            "done_when": "Every requirement has a priority and the first version has no unclear items.",
            "benefit": "The user knows exactly what should be built first.",
            "priority": "high",
            "estimated_hours": 2.0,
        },
        {
            "title": "Create {topic} execution plan",
            "goal": "Break {topic} into a sequence that can be followed without confusion.",
            "steps": (
                "Group the requirements into setup, build, test, and release work.",
                "Place the groups in the correct order based on dependencies.",
                "Assign a realistic time estimate to each work group.",
            ),
            "deliverable": "A step-by-step execution plan for {topic}.",
            "done_when": "The plan shows what starts first, what depends on it, and what finishes the project.",
            "benefit": "The user can start work immediately with less guessing.",
            "priority": "medium",
            "estimated_hours": 2.5,
        },
        {
            "title": "Build {topic} first version",
            "goal": "Create a small usable version of {topic} that proves the idea can work.",
            "steps": (
                "Choose the minimum set of features needed for a working first version.",
                "Build or draft those features without adding polish work yet.",
                "Record anything blocked, missing, or unclear while building.",
            ),
            "deliverable": "A working first version or prototype plan for {topic}.",
            "done_when": "The core flow can be shown, tested, or explained from start to finish.",
            "benefit": "The user gets a real result instead of staying in planning mode.",
            "priority": "medium",
            "estimated_hours": 5.0,
        },
        {
            "title": "Test {topic} core flow",
            "goal": "Find problems in {topic} before presenting or depending on it.",
            "steps": (
                "Run through the main user flow from the first step to the final result.",
                "Write every bug, missing detail, or confusing part in a tracker.",
                "Choose the fixes that block the first useful version.",
            ),
            "deliverable": "A test results tracker for {topic}.",
            "done_when": "The tracker lists tested steps, found issues, and the fixes required before release.",
            "benefit": "The user can improve reliability before others use the result.",
            "priority": "medium",
            "estimated_hours": 3.0,
        },
        {
            "title": "Prepare {topic} release checklist",
            "goal": "Make sure {topic} is ready to share, submit, launch, or continue safely.",
            "steps": (
                "List the final checks needed for content, functionality, and presentation.",
                "Confirm that all high-priority issues are finished or documented.",
                "Write the next action after release, such as feedback collection or improvement work.",
            ),
            "deliverable": "A final release checklist and next-step plan for {topic}.",
            "done_when": "The checklist is complete and there is a clear decision to release, submit, or improve.",
            "benefit": "The user can finish the project with fewer last-minute surprises.",
            "priority": "high",
            "estimated_hours": 2.0,
        },
        {
            "title": "Collect {topic} feedback",
            "goal": "Use real feedback to improve {topic} instead of guessing what matters.",
            "steps": (
                "Choose 2 or 3 people who match the expected user or reviewer.",
                "Ask them to review the first version and answer specific questions.",
                "Sort the feedback into must-fix, should-fix, and optional ideas.",
            ),
            "deliverable": "A feedback table for {topic}.",
            "done_when": "At least 3 useful feedback points are recorded and prioritized.",
            "benefit": "The user improves the project based on evidence.",
            "priority": "low",
            "estimated_hours": 2.0,
        },
        {
            "title": "Improve {topic} weak points",
            "goal": "Fix the parts of {topic} that most affect usability or quality.",
            "steps": (
                "Pick the highest-impact issues from the test results and feedback table.",
                "Fix one issue at a time and record what changed.",
                "Retest the changed parts to confirm the fix worked.",
            ),
            "deliverable": "An improvement log for {topic}.",
            "done_when": "The most important weak points are fixed and retested.",
            "benefit": "The user gets a cleaner and more dependable final result.",
            "priority": "medium",
            "estimated_hours": 4.0,
        },
        {
            "title": "Write {topic} documentation",
            "goal": "Make {topic} easier to understand, maintain, or present later.",
            "steps": (
                "Write what the project does and who it helps.",
                "Document the main setup, usage, or handoff steps.",
                "Add known limitations and future improvements.",
            ),
            "deliverable": "A clear documentation page for {topic}.",
            "done_when": "Someone else can understand the project purpose and basic usage from the document.",
            "benefit": "The user can explain or continue the project with less confusion.",
            "priority": "low",
            "estimated_hours": 2.5,
        },
        {
            "title": "Review {topic} final quality",
            "goal": "Check that {topic} matches the original goal before closing the work.",
            "steps": (
                "Compare the final result against the success criteria document.",
                "Check that the deliverables are complete and easy to find.",
                "Write the final remaining improvements for the next version.",
            ),
            "deliverable": "A final quality review checklist for {topic}.",
            "done_when": "All success criteria are marked passed, failed, or moved to a future version.",
            "benefit": "The user finishes with a clear view of quality and next steps.",
            "priority": "high",
            "estimated_hours": 1.5,
        },
        {
            "title": "Schedule {topic} work sessions",
            "goal": "Protect focused time so {topic} keeps moving forward.",
            "steps": (
                "Estimate the remaining hours for each unfinished task.",
                "Place the work into realistic calendar sessions before the deadline.",
                "Reserve short review sessions after major tasks.",
            ),
            "deliverable": "A calendar schedule for completing {topic}.",
            "done_when": "Each major task has a planned work session and review slot.",
            "benefit": "The user reduces delay by knowing when the work will happen.",
            "priority": "medium",
            "estimated_hours": 1.0,
        },
        {
            "title": "Track {topic} progress",
            "goal": "Keep progress visible so delays and blockers are caught early.",
            "steps": (
                "Create a simple progress tracker with task, status, blocker, and next action columns.",
                "Update the tracker after every work session.",
                "Move blocked items into a separate urgent list.",
            ),
            "deliverable": "A progress tracker for {topic}.",
            "done_when": "Every active task has a status, blocker note, and next action.",
            "benefit": "The user can control the project instead of losing track of details.",
            "priority": "low",
            "estimated_hours": 1.5,
        },
    ]

    tasks: list[dict[str, Any]] = []

    for index, blueprint in enumerate(blueprints[:task_count]):
        title = str(blueprint["title"]).replace("{topic}", topic)
        description = _local_task_description(
            topic=topic,
            goal=str(blueprint["goal"]),
            steps=blueprint["steps"],
            deliverable=str(blueprint["deliverable"]),
            done_when=str(blueprint["done_when"]),
            benefit=str(blueprint["benefit"]),
        )
        tasks.append(
            {
                "suggested_order": index + 1,
                "title": title,
                "description": description,
                "priority": blueprint["priority"],
                "estimated_hours": blueprint["estimated_hours"],
            }
        )

    return tasks


def _generate_with_local_planner(prompt: str) -> str:
    task_count = _extract_task_count(prompt)
    idea_context = _extract_idea_context(prompt)
    project_title = _extract_project_title(prompt, idea_context)
    topic = _title_topic(f"{project_title} {idea_context}")
    include_milestones = "Return an empty milestones array" not in prompt
    tasks = _build_local_tasks(topic=topic, task_count=task_count)
    milestones = []

    if include_milestones:
        milestones = [
            {
                "name": "Scope confirmed",
                "description": f"The first-version direction for {topic} is clear and ready for execution.",
                "suggested_order": 1,
            },
            {
                "name": "First version completed",
                "description": f"The main usable version of {topic} is built or drafted.",
                "suggested_order": 2,
            },
            {
                "name": "Quality reviewed",
                "description": f"The core flow, checklist, and final issues for {topic} are reviewed.",
                "suggested_order": 3,
            },
        ]

    plan = {
        "domain": _human_topic(f"{project_title} {idea_context}"),
        "summary": f"Generated a practical fallback plan for {project_title} with {len(tasks)} focused tasks.",
        "tasks": tasks,
        "milestones": milestones,
        "risks": [
            {
                "risk": "The project idea may still be too broad for the first version.",
                "recommendation": "Keep only the requirements that directly support the first usable result.",
            },
            {
                "risk": "Testing may reveal missing details late in the process.",
                "recommendation": "Test the core flow before adding polish or optional work.",
            },
        ],
        "recommendations": [
            "Start with the success criteria task before building anything large.",
            "Keep every task tied to a visible deliverable.",
            "Review the generated plan and adjust wording before accepting it.",
        ],
    }

    return json.dumps(plan, ensure_ascii=False)


def generate_local_planner_reply(prompt: str) -> str:
    return _generate_with_local_planner(prompt)


def generate_ai_reply_from_provider(
    prompt: str,
    response_mime_type: str | None = None,
    use_local_fallback: bool = True,
) -> str | None:
    provider = settings.ai_provider.strip().lower()
    logger.info(
        "AI provider selected. provider=%s response_mime_type=%s",
        provider or "local",
        response_mime_type or "text/plain",
    )

    if provider == "gemini":
        gemini_reply = _generate_with_gemini(
            prompt,
            response_mime_type=response_mime_type,
        )

        if gemini_reply is not None:
            return gemini_reply

        if not use_local_fallback:
            logger.warning("Gemini reply unavailable. Local provider fallback disabled.")
            return None

        logger.warning("Gemini reply unavailable. Using local planner fallback.")
        return _generate_with_local_planner(prompt)

    if provider in {"", "local", "fallback"}:
        return _generate_with_local_planner(prompt)

    logger.warning("Unsupported AI provider '%s'. Using local planner fallback.", provider)
    return _generate_with_local_planner(prompt)
