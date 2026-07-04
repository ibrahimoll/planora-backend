from __future__ import annotations

import json
import logging
import re
import time
from contextvars import ContextVar
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_AI_REPLY_LENGTH = 30000
MAX_LOCAL_TASK_COUNT = 12
GEMINI_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
GEMINI_TRANSIENT_RETRY_DELAYS_SECONDS = (1.0, 2.0, 4.0)
_last_ai_provider_failure_reason: ContextVar[str | None] = ContextVar(
    "last_ai_provider_failure_reason",
    default=None,
)

LOCAL_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "context",
    "build",
    "building",
    "daily",
    "day",
    "do",
    "create",
    "creating",
    "for",
    "from",
    "goal",
    "how",
    "i",
    "idea",
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
    "prepare",
    "preparing",
    "use",
    "user",
    "users",
    "want",
    "where",
    "with",
    "you",
    "your",
}

FITNESS_KEYWORDS = {
    "5k",
    "bench",
    "bodyweight",
    "calorie",
    "cardio",
    "diet",
    "exercise",
    "fitness",
    "gym",
    "health",
    "injury",
    "km",
    "lose weight",
    "muscle",
    "plank",
    "push-up",
    "pushup",
    "reps",
    "run",
    "running",
    "sets",
    "squat",
    "strength",
    "train",
    "walk",
    "weight loss",
    "workout",
}

STUDY_KEYWORDS = {
    "assignment",
    "book",
    "course",
    "exam",
    "final",
    "homework",
    "learn",
    "lesson",
    "probability",
    "practice test",
    "quiz",
    "read",
    "revision",
    "statistics",
    "study",
    "syllabus",
}

SOFTWARE_KEYWORDS = {
    "api",
    "app",
    "backend",
    "bug",
    "code",
    "database",
    "delivery",
    "feature",
    "flutter",
    "frontend",
    "marketplace",
    "mobile",
    "payment",
    "prototype",
    "software",
    "ui",
    "website",
}

BUSINESS_KEYWORDS = {
    "brand",
    "business",
    "campaign",
    "client",
    "customer",
    "customers",
    "lebanon",
    "launch",
    "lead",
    "marketing",
    "ordering service",
    "pricing",
    "sales",
    "shop",
    "store",
    "stores",
    "whatsapp",
}

CONTENT_KEYWORDS = {
    "blog",
    "content",
    "instagram",
    "podcast",
    "post",
    "reel",
    "script",
    "shorts",
    "teaching",
    "tiktok",
    "video",
    "youtube",
}

EVENT_TRIP_KEYWORDS = {
    "attendee",
    "book swap",
    "conference",
    "community",
    "event",
    "organize",
    "participants",
    "party",
    "swap",
    "trip",
    "travel",
    "university students",
    "vacation",
    "venue",
    "visit",
    "wedding",
    "workshop",
}

HABIT_KEYWORDS = {
    "daily",
    "habit",
    "journal",
    "morning",
    "night",
    "reading habit",
    "routine",
    "sleep",
    "wake",
}


def clear_last_ai_provider_failure_reason() -> None:
    _last_ai_provider_failure_reason.set(None)


def get_last_ai_provider_failure_reason() -> str | None:
    return _last_ai_provider_failure_reason.get()


def _set_last_ai_provider_failure_reason(reason: str) -> None:
    cleaned = reason.strip()
    _last_ai_provider_failure_reason.set(cleaned or "AI provider returned no reason")


def _clean_ai_text(value: str) -> str:
    cleaned = value.strip()

    if len(cleaned) > MAX_AI_REPLY_LENGTH:
        return cleaned[:MAX_AI_REPLY_LENGTH].rstrip() + "..."

    return cleaned


def _extract_gemini_text(response_data: dict[str, Any]) -> str | None:
    candidates = response_data.get("candidates", [])

    if not candidates:
        _set_last_ai_provider_failure_reason("Gemini returned empty content")
        logger.warning(
            "Gemini provider returned empty content. reason=no_candidates response_keys=%s",
            sorted(response_data.keys()),
        )
        return None

    content = candidates[0].get("content", {})
    parts = content.get("parts", [])

    for part in parts:
        text = part.get("text")

        if isinstance(text, str) and text.strip():
            return _clean_ai_text(text)

    _set_last_ai_provider_failure_reason("Gemini returned empty content")
    logger.warning("Gemini provider returned empty content. reason=no_text_parts")

    return None


def _build_gemini_payload(
    prompt: str,
    response_mime_type: str | None = None,
) -> dict[str, Any]:
    generation_config: dict[str, Any] = {
        "temperature": 0.25,
        "maxOutputTokens": 8192,
    }

    if response_mime_type:
        generation_config["responseMimeType"] = response_mime_type

    return {
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


def _gemini_json_mime_fallback_prompt(prompt: str) -> str:
    return (
        f"{prompt}\n\n"
        "Return valid JSON only. Do not use Markdown, code fences, comments, "
        "or text outside the JSON object."
    )


def _generate_with_gemini(
    prompt: str,
    response_mime_type: str | None = None,
) -> str | None:
    logger.info(
        "Gemini provider configuration. ai_provider=%s gemini_api_key_exists=%s gemini_model=%s gemini_timeout_seconds=%s response_mime_type=%s",
        settings.ai_provider,
        bool(settings.gemini_api_key),
        settings.gemini_model,
        settings.gemini_timeout_seconds,
        response_mime_type or "text/plain",
    )

    if not settings.gemini_api_key:
        _set_last_ai_provider_failure_reason("GEMINI_API_KEY was missing")
        logger.warning("Gemini provider unavailable. reason=missing_api_key")
        return None

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    params: dict[str, str] = {}
    headers = {
        "x-goog-api-key": settings.gemini_api_key,
    }
    attempts: list[tuple[str, dict[str, Any]]] = [
        (
            response_mime_type or "text/plain",
            _build_gemini_payload(
                prompt=prompt,
                response_mime_type=response_mime_type,
            ),
        )
    ]

    if response_mime_type == "application/json":
        attempts.append(
            (
                "text/plain",
                _build_gemini_payload(
                    prompt=_gemini_json_mime_fallback_prompt(prompt),
                    response_mime_type=None,
                ),
            )
        )

    try:
        with httpx.Client(timeout=settings.gemini_timeout_seconds) as client:
            last_error_status: int | None = None

            for attempt_index, (attempt_mime_type, payload) in enumerate(
                attempts,
                start=1,
            ):
                response: httpx.Response | Any | None = None

                for retry_index, delay_seconds in enumerate(
                    (*GEMINI_TRANSIENT_RETRY_DELAYS_SECONDS, None),
                    start=1,
                ):
                    logger.info(
                        "Gemini provider call started. model=%s timeout_seconds=%s response_mime_type=%s attempt=%s retry=%s",
                        settings.gemini_model,
                        settings.gemini_timeout_seconds,
                        attempt_mime_type,
                        attempt_index,
                        retry_index,
                    )

                    try:
                        response = client.post(
                            url,
                            params=params,
                            headers=headers,
                            json=payload,
                        )
                    except httpx.TimeoutException as exc:
                        _set_last_ai_provider_failure_reason("Gemini timed out")
                        logger.warning(
                            "Gemini provider failed. reason=timeout error_type=%s response_mime_type=%s attempt=%s retry=%s",
                            type(exc).__name__,
                            attempt_mime_type,
                            attempt_index,
                            retry_index,
                        )

                        if delay_seconds is None:
                            return None

                        logger.info(
                            "Gemini transient retry scheduled. reason=timeout delay_seconds=%s response_mime_type=%s attempt=%s retry=%s",
                            delay_seconds,
                            attempt_mime_type,
                            attempt_index,
                            retry_index,
                        )
                        time.sleep(delay_seconds)
                        continue

                    logger.info(
                        "Gemini provider response status. status=%s response_mime_type=%s attempt=%s retry=%s",
                        response.status_code,
                        attempt_mime_type,
                        attempt_index,
                        retry_index,
                    )

                    if (
                        response.status_code in GEMINI_TRANSIENT_STATUS_CODES
                        and delay_seconds is not None
                    ):
                        last_error_status = response.status_code
                        _set_last_ai_provider_failure_reason(
                            f"Gemini returned HTTP {response.status_code}"
                        )
                        logger.warning(
                            "Gemini transient API error. status=%s response_mime_type=%s attempt=%s retry=%s",
                            response.status_code,
                            attempt_mime_type,
                            attempt_index,
                            retry_index,
                        )
                        logger.info(
                            "Gemini transient retry scheduled. status=%s delay_seconds=%s response_mime_type=%s attempt=%s retry=%s",
                            response.status_code,
                            delay_seconds,
                            attempt_mime_type,
                            attempt_index,
                            retry_index,
                        )
                        time.sleep(delay_seconds)
                        continue

                    break

                if response is None:
                    return None

                if response.status_code < 400:
                    try:
                        response_data = response.json()
                    except ValueError:
                        _set_last_ai_provider_failure_reason(
                            "Gemini response JSON parse failed"
                        )
                        logger.warning(
                            "Gemini provider failed. reason=response_json_parse_failed response_mime_type=%s attempt=%s",
                            attempt_mime_type,
                            attempt_index,
                        )
                        return None

                    text = _extract_gemini_text(response_data)

                    if text is None:
                        logger.warning(
                            "Gemini provider returned empty/None. status=%s response_mime_type=%s attempt=%s",
                            response.status_code,
                            attempt_mime_type,
                            attempt_index,
                        )
                    else:
                        clear_last_ai_provider_failure_reason()

                    return text

                last_error_status = response.status_code
                _set_last_ai_provider_failure_reason(
                    f"Gemini returned HTTP {response.status_code}"
                )
                logger.warning(
                    "Gemini API error. status=%s response_mime_type=%s body=%s",
                    response.status_code,
                    attempt_mime_type,
                    response.text[:800],
                )

                if (
                    response.status_code == 400
                    and response_mime_type == "application/json"
                    and attempt_index == 1
                    and len(attempts) > 1
                ):
                    logger.warning(
                        "Gemini JSON MIME request failed. Retrying without responseMimeType. status=%s",
                        response.status_code,
                    )
                    continue

                return None

        logger.warning(
            "Gemini provider returned empty/None. reason=all_attempts_failed last_status=%s",
            last_error_status,
        )
        return None

    except httpx.TimeoutException as exc:
        _set_last_ai_provider_failure_reason("Gemini timed out")
        logger.warning("Gemini provider failed. reason=timeout error_type=%s", type(exc).__name__)
        return None

    except httpx.HTTPError as exc:
        _set_last_ai_provider_failure_reason("Gemini request failed")
        logger.warning("Gemini provider failed. reason=http_error error_type=%s", type(exc).__name__)
        return None

    except (KeyError, IndexError, TypeError, ValueError) as exc:
        _set_last_ai_provider_failure_reason("Gemini response parse failed")
        logger.warning(
            "Gemini provider failed. reason=response_parse_error error_type=%s",
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
    cleaned = re.sub(
        r"\b(Project idea and goal|User idea and context|User idea and requirements|"
        r"Extra notes, constraints, or preferences|Requirements, features, constraints, and notes|"
        r"Requirements and constraints|Notes and constraints|Project context|Idea)\s*:",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:\n\t")

    if len(cleaned) > max_length:
        cleaned = cleaned[: max_length - 3].rstrip() + "..."

    return cleaned


def _extract_idea_context(prompt: str) -> str:
    source_prompt = _extract_original_prompt(prompt)
    idea = _extract_section(
        prompt=source_prompt,
        start_label="User idea and context:",
        stop_labels=("Return JSON", "Milestones:"),
    )

    if not idea:
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


def _compact_label(value: str, fallback: str = "project") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9 +&/-]+", " ", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -/")
    return cleaned[:64].rstrip() or fallback


def _first_matching_phrase(value: str, phrases: tuple[str, ...]) -> str | None:
    lowered = value.lower()

    for phrase in phrases:
        if phrase in lowered:
            return phrase

    return None


def _infer_focus_from_context(idea_context: str, domain: str) -> str:
    lowered = idea_context.lower()

    if domain == "fitness_health":
        return _fitness_focus(idea_context)

    if domain == "software_app":
        if "marketplace" in lowered and ("baker" in lowered or "bakery" in lowered):
            return "mobile bakery marketplace" if "mobile" in lowered else "bakery marketplace"

        if "marketplace" in lowered:
            return "mobile marketplace" if "mobile" in lowered else "marketplace app"

        if "dashboard" in lowered:
            return "dashboard app"

        if "website" in lowered:
            return "website"

        if "mobile" in lowered or "flutter" in lowered:
            return "mobile app"

        if "api" in lowered:
            return "API-backed app"

        return _compact_label(_title_topic(idea_context), "software app")

    if domain == "study_learning":
        if "probability" in lowered and "stat" in lowered:
            return "probability statistics final exam" if "exam" in lowered else "probability statistics"

        subject_match = re.search(
            r"(?:prepare for|study for|learn)\s+(?:a|an|the)?\s*([a-z0-9 &/-]+?)(?:\s+in\s+\d+|\s+within|\s+by|\.|$)",
            lowered,
        )

        if subject_match:
            return _compact_label(subject_match.group(1), "study goal")

        return _compact_label(_title_topic(idea_context), "study goal")

    if domain == "business_marketing":
        if "whatsapp" in lowered and "order" in lowered:
            return "WhatsApp ordering service"

        if "clothing" in lowered and "store" in lowered:
            return "clothing store launch"

        if "subscription box" in lowered:
            return "subscription box launch"

        return _compact_label(_title_topic(idea_context), "business launch")

    if domain == "content_creator":
        if "youtube" in lowered and "python" in lowered:
            return "YouTube Python channel"

        phrase = _first_matching_phrase(
            idea_context,
            ("youtube channel", "tiktok series", "podcast", "blog", "newsletter"),
        )

        if phrase:
            return phrase

        return _compact_label(_title_topic(idea_context), "content project")

    if domain == "event_trip":
        if "book swap" in lowered:
            return "community book swap"

        phrase = _first_matching_phrase(
            idea_context,
            ("workshop", "conference", "wedding", "trip", "event"),
        )

        if phrase:
            return phrase

        return _compact_label(_title_topic(idea_context), "event")

    if domain == "personal_habit":
        if "morning" in lowered and "reading" in lowered:
            return "morning reading habit"

        if "reading" in lowered:
            return "reading habit"

        phrase = _first_matching_phrase(
            idea_context,
            ("morning routine", "sleep routine", "daily habit", "journal habit"),
        )

        if phrase:
            return phrase

        return _compact_label(_title_topic(idea_context), "personal habit")

    if "laboratory equipment" in lowered and ("lend" in lowered or "borrow" in lowered):
        return "laboratory equipment lending system"

    if "dog" in lowered:
        return "dog training"

    if "book swap" in lowered:
        return "book swap"

    return _compact_label(_title_topic(idea_context), "project")


def _contains_any_keyword(value: str, keywords: set[str]) -> bool:
    lowered = value.lower()

    for keyword in keywords:
        normalized = keyword.lower()

        if " " in normalized or "-" in normalized:
            if normalized in lowered:
                return True
            continue

        if re.search(rf"\b{re.escape(normalized)}s?\b", lowered):
            return True

    return False


def _classify_idea_domain(idea_context: str) -> str:
    if _contains_any_keyword(idea_context, FITNESS_KEYWORDS):
        return "fitness_health"

    if _contains_any_keyword(idea_context, HABIT_KEYWORDS):
        return "personal_habit"

    if _contains_any_keyword(idea_context, EVENT_TRIP_KEYWORDS):
        return "event_trip"

    if _contains_any_keyword(idea_context, CONTENT_KEYWORDS):
        return "content_creator"

    if _contains_any_keyword(idea_context, SOFTWARE_KEYWORDS):
        return "software_app"

    if _contains_any_keyword(idea_context, BUSINESS_KEYWORDS):
        return "business_marketing"

    if _contains_any_keyword(idea_context, STUDY_KEYWORDS):
        return "study_learning"

    return "generic_project"


def _fitness_focus(idea_context: str) -> str:
    lowered = idea_context.lower()

    if "push-up" in lowered or "pushup" in lowered:
        return "pushups"

    if "5k" in lowered or "5 km" in lowered or "5km" in lowered:
        return "5K running"

    if "run" in lowered or "running" in lowered:
        return "running"

    if "lose weight" in lowered or "weight loss" in lowered:
        return "weight loss"

    if "muscle" in lowered:
        return "muscle building"

    if "plank" in lowered:
        return "planks"

    if "squat" in lowered:
        return "squats"

    return "fitness goal"


def _focus_from_context(idea_context: str, domain: str) -> str:
    return _infer_focus_from_context(idea_context, domain)


def _domain_task_description(
    *,
    goal: str,
    steps: tuple[str, str, str],
    deliverable: str,
    done_when: str,
    why_it_matters: str,
) -> str:
    return (
        f"Goal: {goal}\n\n"
        "Steps:\n"
        f"1. {steps[0]}\n"
        f"2. {steps[1]}\n"
        f"3. {steps[2]}\n\n"
        f"Deliverable: {deliverable}\n\n"
        f"Done when: {done_when}\n\n"
        f"Why it matters: {why_it_matters}"
    )


def _task_blueprint(
    *,
    title: str,
    goal: str,
    steps: tuple[str, str, str],
    deliverable: str,
    done_when: str,
    why_it_matters: str,
    priority: str = "medium",
    estimated_hours: float = 2.0,
) -> dict[str, Any]:
    return {
        "title": title,
        "goal": goal,
        "steps": steps,
        "deliverable": deliverable,
        "done_when": done_when,
        "why_it_matters": why_it_matters,
        "priority": priority,
        "estimated_hours": estimated_hours,
    }


def _fitness_blueprints(focus: str) -> list[dict[str, Any]]:
    return [
        _task_blueprint(
            title=f"Assess {focus} starting baseline",
            goal=f"Measure the current safe starting point for {focus}.",
            steps=(
                "Warm up for 5 minutes before testing effort.",
                "Complete one controlled baseline set, distance, or session without pushing through pain.",
                "Record reps, time, distance, difficulty, and any discomfort.",
            ),
            deliverable=f"A baseline log for {focus}.",
            done_when="The starting measurement and effort notes are written down.",
            why_it_matters="A baseline keeps training realistic and safer.",
            priority="high",
            estimated_hours=0.75,
        ),
        _task_blueprint(
            title=f"Set {focus} weekly target",
            goal=f"Choose a realistic first-week target for {focus}.",
            steps=(
                "Use the baseline to pick a target that feels challenging but repeatable.",
                "Set a weekly total for sessions, reps, minutes, or distance.",
                "Write the easier version you will use on low-energy days.",
            ),
            deliverable=f"A first-week {focus} target.",
            done_when="The weekly target and easier backup are visible before training starts.",
            why_it_matters="A clear target helps consistency without overloading the body.",
            priority="high",
            estimated_hours=0.5,
        ),
        _task_blueprint(
            title=f"Schedule {focus} workout blocks",
            goal=f"Place {focus} sessions into the week with enough recovery.",
            steps=(
                "Choose training days that fit sleep, work, and school demands.",
                "Add rest or lighter days between harder sessions.",
                "Write the exact start time and session length for each block.",
            ),
            deliverable=f"A weekly {focus} training calendar.",
            done_when="Every planned workout has a date, time, and length.",
            why_it_matters="Scheduled sessions are easier to protect and repeat.",
            priority="medium",
            estimated_hours=0.75,
        ),
        _task_blueprint(
            title=f"Practice {focus} technique cues",
            goal=f"Improve form so {focus} builds skill instead of strain.",
            steps=(
                "Choose three form cues that matter for the movement or activity.",
                "Practice slowly before adding volume or speed.",
                "Stop and adjust when the cues break down.",
            ),
            deliverable=f"A short {focus} technique checklist.",
            done_when="The checklist can be followed during every session.",
            why_it_matters="Better technique makes progress more dependable.",
            priority="high",
            estimated_hours=1.0,
        ),
        _task_blueprint(
            title=f"Build {focus} progression plan",
            goal=f"Increase {focus} workload gradually over the next two weeks.",
            steps=(
                "Choose one variable to increase, such as reps, minutes, load, or distance.",
                "Increase only after two comfortable sessions.",
                "Mark one lighter day after each harder training block.",
            ),
            deliverable=f"A two-week {focus} progression table.",
            done_when="Each session has a target and a lighter fallback.",
            why_it_matters="Gradual progression helps the body adapt.",
            priority="medium",
            estimated_hours=1.0,
        ),
        _task_blueprint(
            title=f"Add {focus} warmup routine",
            goal=f"Prepare joints, muscles, and breathing before {focus}.",
            steps=(
                "Choose 3-5 warmup movements linked to the activity.",
                "Practice the warmup before the main session.",
                "Adjust any movement that causes pain or feels too intense.",
            ),
            deliverable=f"A repeatable {focus} warmup routine.",
            done_when="The warmup is listed and completed before training.",
            why_it_matters="A warmup makes sessions smoother and safer.",
            priority="medium",
            estimated_hours=0.5,
        ),
        _task_blueprint(
            title=f"Define {focus} recovery rules",
            goal=f"Know when to rest, reduce intensity, or stop {focus}.",
            steps=(
                "Write pain signals that mean the session should stop.",
                "Set a soreness rule for reducing the next session.",
                "Plan sleep, hydration, and rest support around hard days.",
            ),
            deliverable=f"A recovery and pain-rule checklist for {focus}.",
            done_when="Stop, reduce, and rest rules are written clearly.",
            why_it_matters="Recovery rules protect consistency and reduce injury risk.",
            priority="high",
            estimated_hours=0.5,
        ),
        _task_blueprint(
            title=f"Track {focus} training metrics",
            goal=f"Record whether {focus} is improving or becoming too intense.",
            steps=(
                "Log each session with the main metric and difficulty rating.",
                "Add notes about soreness, energy, sleep, and pain.",
                "Highlight patterns that affect performance.",
            ),
            deliverable=f"A {focus} training tracker.",
            done_when="Every session has metrics and recovery notes.",
            why_it_matters="Tracking shows when to progress and when to back off.",
            priority="medium",
            estimated_hours=0.5,
        ),
        _task_blueprint(
            title=f"Complete {focus} checkpoint session",
            goal=f"Test progress after the first training block for {focus}.",
            steps=(
                "Repeat the baseline test under similar conditions.",
                "Compare the new result with the starting measurement.",
                "Write what improved, stayed stuck, or felt uncomfortable.",
            ),
            deliverable=f"A checkpoint result for {focus}.",
            done_when="The new result is compared with the baseline.",
            why_it_matters="A checkpoint turns effort into useful training decisions.",
            priority="high",
            estimated_hours=0.75,
        ),
        _task_blueprint(
            title=f"Adjust {focus} next block",
            goal=f"Choose the next realistic target for {focus}.",
            steps=(
                "Review the tracker, checkpoint result, and recovery notes.",
                "Increase, hold, or reduce the target based on evidence.",
                "Write the next two-week block before the next session.",
            ),
            deliverable=f"A next-block plan for {focus}.",
            done_when="The next target follows from recorded training data.",
            why_it_matters="Evidence-based adjustments keep progress sustainable.",
            priority="medium",
            estimated_hours=0.75,
        ),
        _task_blueprint(
            title=f"Prepare {focus} training setup",
            goal=f"Make each {focus} session easy to begin.",
            steps=(
                "List clothing, equipment, water, timer, or route needs.",
                "Put the setup in place before the planned session time.",
                "Remove one friction point that usually delays training.",
            ),
            deliverable=f"A ready-to-use {focus} setup list.",
            done_when="The next session can start without searching for items.",
            why_it_matters="A prepared setup lowers the chance of skipping sessions.",
            priority="low",
            estimated_hours=0.5,
        ),
        _task_blueprint(
            title=f"Review {focus} health constraints",
            goal=f"Check whether {focus} needs professional guidance or safer limits.",
            steps=(
                "List any prior injuries, pain patterns, or medical constraints.",
                "Choose movements or intensity limits that respect those constraints.",
                "Ask a qualified professional if pain or health risks are unclear.",
            ),
            deliverable=f"A health-constraint note for {focus}.",
            done_when="Known risks and safety limits are documented.",
            why_it_matters="Safety checks keep the plan practical for real life.",
            priority="high",
            estimated_hours=0.5,
        ),
    ]


def _generic_project_blueprints(
    *,
    focus: str,
    idea_context: str,
) -> list[dict[str, Any]]:
    lowered = idea_context.lower()

    if "dog" in lowered:
        return [
            _task_blueprint(
                title="Choose the first dog command",
                goal="Select one useful behavior to teach before adding more commands.",
                steps=(
                    "Choose one command such as sit, stay, come, or leave it.",
                    "Write the exact word and hand signal everyone will use.",
                    "Pick a quiet place for the first practice session.",
                ),
                deliverable="A first-command training note.",
                done_when="The command, cue, and practice location are written down.",
                why_it_matters="One clear command prevents confusing the dog with mixed signals.",
                priority="high",
                estimated_hours=0.75,
            ),
            _task_blueprint(
                title="Prepare dog reward supplies",
                goal="Make reinforcement ready before training starts.",
                steps=(
                    "Choose small treats or toys the dog finds motivating.",
                    "Pick a reward marker such as yes or a clicker.",
                    "Keep rewards reachable during every short session.",
                ),
                deliverable="A prepared treat and reward-marker setup.",
                done_when="Rewards and the marker are ready before practice begins.",
                why_it_matters="Fast rewards help the dog connect the command with the behavior.",
                priority="high",
                estimated_hours=0.5,
            ),
            _task_blueprint(
                title="Run short dog training sessions",
                goal="Practice consistently without tiring or frustrating the dog.",
                steps=(
                    "Schedule 5-10 minute sessions once or twice a day.",
                    "Practice only the selected command during each session.",
                    "End while the dog is still engaged and successful.",
                ),
                deliverable="A short daily dog-training schedule.",
                done_when="The first week of sessions is scheduled and started.",
                why_it_matters="Short sessions build learning without overload.",
                priority="medium",
                estimated_hours=1.0,
            ),
            _task_blueprint(
                title="Practice in a quiet space",
                goal="Help the dog learn the command before distractions are added.",
                steps=(
                    "Remove toys, noise, and other pets from the practice area.",
                    "Give the cue once and reward the correct behavior immediately.",
                    "Repeat a few successful reps, then stop the session.",
                ),
                deliverable="A low-distraction practice routine.",
                done_when="The dog responds correctly several times in the quiet space.",
                why_it_matters="A calm setting makes the first behavior easier to learn.",
                priority="medium",
                estimated_hours=1.0,
            ),
            _task_blueprint(
                title="Add distractions gradually",
                goal="Teach the dog to respond outside the easiest training setting.",
                steps=(
                    "Add one mild distraction such as distance, a toy, or another room.",
                    "Reward correct responses and return to easier practice when needed.",
                    "Avoid adding multiple distractions in the same session.",
                ),
                deliverable="A distraction ladder for the command.",
                done_when="The dog responds with one new distraction present.",
                why_it_matters="Gradual challenge helps the behavior transfer to real life.",
                priority="medium",
                estimated_hours=1.0,
            ),
            _task_blueprint(
                title="Track dog behavior progress",
                goal="Record what the dog can do reliably and what still needs practice.",
                steps=(
                    "Log each session with command, location, distractions, and success rate.",
                    "Note treats used and any behavior problems.",
                    "Pick the next practice adjustment from the log.",
                ),
                deliverable="A dog-training progress tracker.",
                done_when="Each session has a short result note.",
                why_it_matters="Tracking reveals whether training is improving or stuck.",
                priority="medium",
                estimated_hours=0.5,
            ),
            _task_blueprint(
                title="Keep cues consistent",
                goal="Make sure everyone teaches the same dog behavior in the same way.",
                steps=(
                    "Share the command word, hand signal, and reward timing.",
                    "Ask family members to avoid alternate words for the same behavior.",
                    "Correct inconsistent cues before the next practice session.",
                ),
                deliverable="A shared command and cue rule.",
                done_when="Everyone uses the same cue and reward timing.",
                why_it_matters="Consistency helps the dog learn faster.",
                priority="high",
                estimated_hours=0.5,
            ),
            _task_blueprint(
                title="Review problem dog behaviors",
                goal="Identify behaviors that interfere with training progress.",
                steps=(
                    "List moments when the dog jumps, barks, pulls, ignores, or gets distracted.",
                    "Write what happened right before each behavior.",
                    "Choose one prevention step for the next session.",
                ),
                deliverable="A problem-behavior review note.",
                done_when="One behavior has a clear trigger and prevention step.",
                why_it_matters="Training improves faster when blockers are understood.",
                priority="medium",
                estimated_hours=0.75,
            ),
            _task_blueprint(
                title="Practice dog leash manners",
                goal="Teach calmer walking behavior during short leash sessions.",
                steps=(
                    "Choose a quiet route with few distractions.",
                    "Reward the dog for walking near you without pulling.",
                    "Stop or change direction when pulling starts.",
                ),
                deliverable="A leash-practice routine.",
                done_when="The dog completes a short walk with repeated calm moments.",
                why_it_matters="Leash manners make everyday practice safer and easier.",
                priority="medium",
                estimated_hours=1.0,
            ),
            _task_blueprint(
                title="Teach dog recall practice",
                goal="Build a reliable come command in controlled settings.",
                steps=(
                    "Practice recall indoors or in a secure enclosed area.",
                    "Use a happy cue and reward the dog immediately for coming.",
                    "Increase distance only after several successful repetitions.",
                ),
                deliverable="A recall practice log.",
                done_when="The dog comes reliably at the current distance.",
                why_it_matters="Recall is one of the most useful safety behaviors.",
                priority="high",
                estimated_hours=1.0,
            ),
            _task_blueprint(
                title="Generalize dog commands outside",
                goal="Help learned commands work beyond the original room.",
                steps=(
                    "Practice the command in a doorway, hallway, yard, or quiet outdoor spot.",
                    "Use easier expectations when the setting is new.",
                    "Record which location still needs more practice.",
                ),
                deliverable="A location practice checklist.",
                done_when="The dog responds in at least two different settings.",
                why_it_matters="Dogs need practice in multiple places to generalize behavior.",
                priority="medium",
                estimated_hours=1.0,
            ),
            _task_blueprint(
                title="Plan next dog command",
                goal="Choose the next behavior after the first command is reliable.",
                steps=(
                    "Review the command tracker and problem-behavior notes.",
                    "Pick one next command that supports daily life.",
                    "Write the cue, reward, and first practice location.",
                ),
                deliverable="A next-command plan.",
                done_when="The next command has a cue, reward, and practice setup.",
                why_it_matters="A measured next command keeps training focused.",
                priority="low",
                estimated_hours=0.5,
            ),
        ]

    if "laboratory equipment" in lowered or "lending" in lowered or "borrow" in lowered:
        equipment_label = "laboratory equipment"
        audience = "university students" if "student" in lowered else "borrowers"

        return [
            _task_blueprint(
                title="Catalog laboratory equipment items",
                goal=f"Create a clear inventory before {audience} can borrow equipment.",
                steps=(
                    "List each item with name, quantity, condition, and storage location.",
                    "Add a unique ID or label for every lendable item.",
                    "Mark items that should not be loaned out.",
                ),
                deliverable="A labeled laboratory equipment inventory.",
                done_when="Every lendable item has an ID, condition, and location.",
                why_it_matters="A lending system cannot work without a trusted inventory.",
                priority="high",
                estimated_hours=3.0,
            ),
            _task_blueprint(
                title="Define student lending eligibility",
                goal=f"Decide who can borrow {equipment_label} and under what conditions.",
                steps=(
                    "List eligible student groups, courses, or lab sections.",
                    "Decide what identification or approval is required.",
                    "Write limits for quantity, duration, and repeat borrowing.",
                ),
                deliverable="A student eligibility and borrowing-limit policy.",
                done_when="Eligibility and limits are written in plain language.",
                why_it_matters="Clear eligibility prevents confusion and unfair access.",
                priority="high",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title="Set checkout and return rules",
                goal=f"Protect {equipment_label} while keeping borrowing simple for {audience}.",
                steps=(
                    "Define pickup, due-date, extension, and return steps.",
                    "Write what happens for late, damaged, or missing equipment.",
                    "Add inspection steps for checkout and return.",
                ),
                deliverable="A checkout and return rule sheet.",
                done_when="Rules cover pickup, return, late items, and damage.",
                why_it_matters="Rules reduce loss and make the process predictable.",
                priority="high",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title="Create equipment request form",
                goal=f"Collect the information needed to approve {equipment_label} loans.",
                steps=(
                    "Add fields for student details, item requested, course, dates, and purpose.",
                    "Include agreement checkboxes for care, return, and damage rules.",
                    "Test the form with one sample request.",
                ),
                deliverable="A working equipment request form.",
                done_when="A sample request can be submitted with all required fields.",
                why_it_matters="A form standardizes requests and reduces missing details.",
                priority="medium",
                estimated_hours=2.5,
            ),
            _task_blueprint(
                title="Build equipment tracking sheet",
                goal=f"Track where each {equipment_label} item is during lending.",
                steps=(
                    "Create columns for item ID, borrower, checkout date, due date, and status.",
                    "Add condition notes for pickup and return.",
                    "Flag overdue and damaged items clearly.",
                ),
                deliverable="A lending tracker for laboratory equipment.",
                done_when="Every active loan can be found by item ID and student.",
                why_it_matters="Tracking prevents lost equipment and missed returns.",
                priority="high",
                estimated_hours=3.0,
            ),
            _task_blueprint(
                title="Assign storage inspection owners",
                goal=f"Make responsibility clear for storing and checking {equipment_label}.",
                steps=(
                    "Choose who can approve requests, hand out items, and inspect returns.",
                    "Write handoff steps for days when the main owner is unavailable.",
                    "Place the owner list near the storage area or tracker.",
                ),
                deliverable="An owner and handoff responsibility list.",
                done_when="Each lending step has a named owner or backup.",
                why_it_matters="Named ownership keeps the process from stalling.",
                priority="medium",
                estimated_hours=1.5,
            ),
            _task_blueprint(
                title="Pilot lending with students",
                goal=f"Test the {equipment_label} process with a small group of {audience}.",
                steps=(
                    "Choose a small set of items and students for the pilot.",
                    "Run checkout, usage, return, and inspection exactly as documented.",
                    "Record delays, confusion, missing fields, and damaged-item risks.",
                ),
                deliverable="A completed pilot lending log.",
                done_when="At least one full checkout and return cycle is recorded.",
                why_it_matters="A pilot exposes process problems before wider use.",
                priority="medium",
                estimated_hours=4.0,
            ),
            _task_blueprint(
                title="Record overdue damage issues",
                goal=f"Create a response process for overdue or damaged {equipment_label}.",
                steps=(
                    "List issue types such as late return, missing part, damage, or no-show pickup.",
                    "Write the first response for each issue type.",
                    "Add escalation rules for repeated or serious issues.",
                ),
                deliverable="An overdue and damage response checklist.",
                done_when="Each common issue has a response and escalation path.",
                why_it_matters="Issue handling protects equipment and keeps trust high.",
                priority="medium",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title="Publish borrowing instructions",
                goal=f"Help {audience} understand how to borrow {equipment_label}.",
                steps=(
                    "Write simple instructions for requesting, pickup, use, and return.",
                    "Add eligibility, loan length, and damage rules.",
                    "Share the instructions where students will actually see them.",
                ),
                deliverable="A student-facing borrowing guide.",
                done_when="The guide is published with the request-form link.",
                why_it_matters="Clear instructions reduce support questions and misuse.",
                priority="medium",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title="Collect student lending feedback",
                goal=f"Improve the {equipment_label} system using student experience.",
                steps=(
                    "Ask borrowers about request clarity, pickup speed, and return steps.",
                    "Ask staff or lab owners about tracking and inspection workload.",
                    "Sort feedback into must-fix and later improvements.",
                ),
                deliverable="A prioritized lending feedback list.",
                done_when="Feedback from students and owners is grouped by priority.",
                why_it_matters="Real feedback shows what blocks adoption.",
                priority="low",
                estimated_hours=1.5,
            ),
            _task_blueprint(
                title="Adjust equipment inventory limits",
                goal=f"Tune {equipment_label} availability after the pilot.",
                steps=(
                    "Review which items were requested, overdue, damaged, or unused.",
                    "Change loan limits for high-risk or high-demand items.",
                    "Update the inventory and borrowing guide with the changes.",
                ),
                deliverable="Updated lending limits and inventory notes.",
                done_when="Loan limits reflect pilot evidence and equipment risk.",
                why_it_matters="Inventory limits keep the system useful and sustainable.",
                priority="medium",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title="Prepare semester lending handoff",
                goal=f"Keep the {equipment_label} system running beyond the first pilot.",
                steps=(
                    "Document tracker maintenance, storage checks, and approval routines.",
                    "Name the next owner or backup for the coming semester.",
                    "Archive pilot decisions and unresolved issues.",
                ),
                deliverable="A semester handoff document.",
                done_when="A new owner can run lending from the documented process.",
                why_it_matters="A handoff prevents the system from depending on one person.",
                priority="low",
                estimated_hours=2.0,
            ),
        ]

    return [
        _task_blueprint(
            title=f"Define {focus} success outcome",
            goal=f"Choose the concrete result that {focus} should produce.",
            steps=(
                "Write the main result in one sentence.",
                "List the people, items, places, or decisions involved.",
                "Choose three checks that prove the result is useful.",
            ),
            deliverable=f"A success outcome note for {focus}.",
            done_when="The outcome, involved resources, and success checks are written.",
            why_it_matters="A concrete outcome keeps the work tied to the idea.",
            priority="high",
            estimated_hours=1.0,
        ),
        _task_blueprint(
            title=f"Map {focus} participants",
            goal=f"Identify who is involved in making {focus} work.",
            steps=(
                "List users, helpers, approvers, owners, or affected people.",
                "Write what each person needs to give, receive, approve, or decide.",
                "Mark the first person who must be contacted.",
            ),
            deliverable=f"A participant and responsibility map for {focus}.",
            done_when="Every key person has a role and first contact action.",
            why_it_matters="Projects move faster when ownership is visible.",
            priority="high",
            estimated_hours=1.5,
        ),
        _task_blueprint(
            title=f"Set {focus} operating rules",
            goal=f"Create simple rules that make {focus} fair and repeatable.",
            steps=(
                "List decisions that could cause confusion or conflict.",
                "Write clear rules for access, timing, responsibilities, and exceptions.",
                "Check the rules against the original goal and constraints.",
            ),
            deliverable=f"An operating rule sheet for {focus}.",
            done_when="Rules cover the most likely questions and exceptions.",
            why_it_matters="Rules reduce avoidable back-and-forth during execution.",
            priority="high",
            estimated_hours=2.0,
        ),
        _task_blueprint(
            title=f"Create {focus} intake form",
            goal=f"Capture the details needed to run {focus} reliably.",
            steps=(
                "List the information needed before action can happen.",
                "Turn each required detail into a short form question.",
                "Test the form with one realistic example.",
            ),
            deliverable=f"A usable intake form for {focus}.",
            done_when="A sample entry can be submitted with no missing critical detail.",
            why_it_matters="Good intake prevents incomplete requests and rework.",
            priority="medium",
            estimated_hours=2.0,
        ),
        _task_blueprint(
            title=f"Build {focus} tracking sheet",
            goal=f"Make the status of {focus} visible.",
            steps=(
                "Create columns for item, owner, status, date, blocker, and next action.",
                "Add the first real entries from the project.",
                "Highlight overdue, blocked, or urgent rows.",
            ),
            deliverable=f"A live tracking sheet for {focus}.",
            done_when="Every active item has a status, owner, and next action.",
            why_it_matters="Tracking keeps details from disappearing.",
            priority="medium",
            estimated_hours=2.5,
        ),
        _task_blueprint(
            title=f"Prepare {focus} materials",
            goal=f"Gather the physical or digital materials needed for {focus}.",
            steps=(
                "List documents, tools, supplies, links, locations, or permissions needed.",
                "Mark what is ready, missing, or blocked.",
                "Get the highest-priority missing material first.",
            ),
            deliverable=f"A readiness list for {focus}.",
            done_when="Critical materials are ready or assigned to an owner.",
            why_it_matters="Preparation prevents avoidable delays during execution.",
            priority="medium",
            estimated_hours=2.0,
        ),
        _task_blueprint(
            title=f"Pilot {focus} with real users",
            goal=f"Test {focus} with a small real scenario before expanding it.",
            steps=(
                "Choose a small pilot group or realistic sample case.",
                "Run the process from request to completion.",
                "Record confusion, delays, missing information, and successful steps.",
            ),
            deliverable=f"A pilot log for {focus}.",
            done_when="One full pilot cycle is completed and documented.",
            why_it_matters="A pilot reveals problems while they are still cheap to fix.",
            priority="medium",
            estimated_hours=4.0,
        ),
        _task_blueprint(
            title=f"Record {focus} issues",
            goal=f"Capture the problems that appear while running {focus}.",
            steps=(
                "Write each issue with when it happened and who was affected.",
                "Group issues by policy, communication, materials, timing, or ownership.",
                "Choose the fixes that block repeat use.",
            ),
            deliverable=f"An issue log for {focus}.",
            done_when="Every major pilot issue has a category and fix decision.",
            why_it_matters="Issue logs turn messy feedback into practical improvements.",
            priority="medium",
            estimated_hours=1.5,
        ),
        _task_blueprint(
            title=f"Publish {focus} instructions",
            goal=f"Make {focus} understandable to the people who need to use it.",
            steps=(
                "Write step-by-step instructions in plain language.",
                "Add rules, contact points, deadlines, and examples.",
                "Share the instructions in the most visible channel.",
            ),
            deliverable=f"A published instruction guide for {focus}.",
            done_when="Users can find the guide and follow the process without explanation.",
            why_it_matters="Clear instructions make the system usable by others.",
            priority="medium",
            estimated_hours=2.0,
        ),
        _task_blueprint(
            title=f"Collect {focus} feedback",
            goal=f"Learn whether {focus} actually works for the intended people.",
            steps=(
                "Ask users what was clear, slow, confusing, or missing.",
                "Ask owners what was hard to maintain.",
                "Sort feedback into urgent fixes and later improvements.",
            ),
            deliverable=f"A feedback summary for {focus}.",
            done_when="Feedback is collected and prioritized.",
            why_it_matters="Feedback keeps improvements tied to real use.",
            priority="low",
            estimated_hours=1.5,
        ),
        _task_blueprint(
            title=f"Improve {focus} weak points",
            goal=f"Fix the highest-impact problems found in {focus}.",
            steps=(
                "Pick the top three issues from the feedback and issue logs.",
                "Apply one fix at a time and record the change.",
                "Retest the changed step with a realistic case.",
            ),
            deliverable=f"An improvement log for {focus}.",
            done_when="The most important weak points are fixed and retested.",
            why_it_matters="Focused improvement makes the result more reliable.",
            priority="medium",
            estimated_hours=3.0,
        ),
        _task_blueprint(
            title=f"Prepare {focus} handoff",
            goal=f"Make {focus} easy to continue after the first version.",
            steps=(
                "Document owners, routines, links, rules, and unresolved decisions.",
                "Write the next maintenance or review date.",
                "Share the handoff with the person responsible for continuing it.",
            ),
            deliverable=f"A handoff document for {focus}.",
            done_when="Someone else can continue the work from the handoff.",
            why_it_matters="Handoff prevents the project from fading after launch.",
            priority="low",
            estimated_hours=2.0,
        ),
    ]


def _generic_domain_blueprints(
    domain: str,
    focus: str,
    idea_context: str = "",
) -> list[dict[str, Any]]:
    if domain == "software_app":
        return [
            _task_blueprint(
                title=f"Define {focus} user flow",
                goal=f"Map the main path a user must complete in {focus}.",
                steps=(
                    "Write the primary user journey from first visit to successful outcome.",
                    "List the screens, actions, and decisions in that journey.",
                    "Mark optional steps that can wait until after the first release.",
                ),
                deliverable=f"A user-flow outline for {focus}.",
                done_when="The main user path can be explained in ordered screens and actions.",
                why_it_matters="A clear flow prevents scattered development work.",
                priority="high",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title=f"Choose {focus} MVP scope",
                goal=f"Decide the smallest usable version of {focus}.",
                steps=(
                    "List must-have, should-have, and later capabilities.",
                    "Keep only capabilities needed for the first complete user flow.",
                    "Write what the MVP will deliberately exclude.",
                ),
                deliverable=f"An MVP scope list for {focus}.",
                done_when="The first release has clear included and excluded capabilities.",
                why_it_matters="Scope control keeps the build finishable.",
                priority="high",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title=f"Design {focus} data model",
                goal=f"Define the data {focus} needs to store and relate.",
                steps=(
                    "List core entities, such as users, listings, orders, payments, or messages.",
                    "Add required fields and relationships for each entity.",
                    "Check the model against the main user flow.",
                ),
                deliverable=f"A data model sketch for {focus}.",
                done_when="Core entities, fields, and relationships are documented.",
                why_it_matters="A solid data model reduces backend rewrites.",
                priority="high",
                estimated_hours=3.0,
            ),
            _task_blueprint(
                title=f"Define {focus} API contracts",
                goal=f"Specify how the frontend and backend will exchange {focus} data.",
                steps=(
                    "List endpoints needed by the main user flow.",
                    "Write request fields, response fields, and error cases for each endpoint.",
                    "Confirm authentication and authorization needs per endpoint.",
                ),
                deliverable=f"An API contract document for {focus}.",
                done_when="Each core endpoint has request, response, and error details.",
                why_it_matters="API contracts prevent frontend and backend mismatch.",
                priority="high",
                estimated_hours=3.0,
            ),
            _task_blueprint(
                title=f"Build {focus} authentication",
                goal=f"Let the right users sign in and access protected {focus} actions.",
                steps=(
                    "Choose sign-up, login, logout, and password-reset behavior.",
                    "Implement session or token handling on the backend.",
                    "Add frontend screens and protected-route checks.",
                ),
                deliverable=f"Working authentication for {focus}.",
                done_when="A user can sign up, sign in, sign out, and access protected screens.",
                why_it_matters="Authentication unlocks real user workflows.",
                priority="high",
                estimated_hours=6.0,
            ),
            _task_blueprint(
                title=f"Implement {focus} core screens",
                goal=f"Build the frontend screens needed for the first {focus} flow.",
                steps=(
                    "Create screen layouts for browsing, detail view, creation, and confirmation.",
                    "Connect forms to local validation and loading states.",
                    "Add empty, error, and success states for each core screen.",
                ),
                deliverable=f"Core frontend screens for {focus}.",
                done_when="The primary flow can be clicked through in the frontend.",
                why_it_matters="Screens turn the product flow into something users can test.",
                priority="medium",
                estimated_hours=6.0,
            ),
            _task_blueprint(
                title=f"Connect {focus} frontend backend",
                goal=f"Make frontend actions use real backend data for {focus}.",
                steps=(
                    "Wire API clients for authentication and core resources.",
                    "Replace mock data with backend responses.",
                    "Handle loading, validation, and server errors in the UI.",
                ),
                deliverable=f"An integrated {focus} frontend and backend flow.",
                done_when="The main flow saves and reads real data through the API.",
                why_it_matters="Integration proves the app works beyond static screens.",
                priority="high",
                estimated_hours=5.0,
            ),
            _task_blueprint(
                title=f"Test {focus} critical flows",
                goal=f"Find breakages in the most important {focus} behavior.",
                steps=(
                    "Write test cases for sign-up, core creation, browsing, checkout, and error states.",
                    "Run manual or automated tests against a clean test account.",
                    "Log bugs with reproduction steps and expected results.",
                ),
                deliverable=f"A critical-flow test report for {focus}.",
                done_when="Core flows are tested and blocking bugs are listed or fixed.",
                why_it_matters="Testing protects the first user experience.",
                priority="high",
                estimated_hours=4.0,
            ),
            _task_blueprint(
                title=f"Configure {focus} deployment",
                goal=f"Prepare {focus} to run outside the local development machine.",
                steps=(
                    "Choose hosting for the frontend, backend, database, and storage.",
                    "Configure environment variables and production secrets.",
                    "Deploy a staging build and run the main flow there.",
                ),
                deliverable=f"A staging deployment for {focus}.",
                done_when="The deployed app can complete the primary flow.",
                why_it_matters="Deployment reveals environment and configuration issues early.",
                priority="medium",
                estimated_hours=4.0,
            ),
            _task_blueprint(
                title=f"Prepare {focus} release checklist",
                goal=f"Confirm {focus} is ready to share with initial users.",
                steps=(
                    "Check authentication, data persistence, privacy, and error handling.",
                    "Write known limitations and support contact details.",
                    "Decide the release audience and rollback plan.",
                ),
                deliverable=f"A release checklist for {focus}.",
                done_when="Launch-critical checks are passed or explicitly deferred.",
                why_it_matters="A checklist reduces avoidable launch surprises.",
                priority="high",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title=f"Collect {focus} beta feedback",
                goal=f"Learn what early users need changed in {focus}.",
                steps=(
                    "Invite a small group that matches the target audience.",
                    "Ask them to complete the main flow and report friction.",
                    "Sort feedback into bugs, usability fixes, and later ideas.",
                ),
                deliverable=f"A beta feedback list for {focus}.",
                done_when="Feedback is grouped and prioritized after real use.",
                why_it_matters="Beta feedback guides the next build decisions.",
                priority="medium",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title=f"Improve {focus} launch blockers",
                goal=f"Fix the issues that most block real use of {focus}.",
                steps=(
                    "Choose the highest-impact bugs and usability issues.",
                    "Fix one blocker at a time and record the change.",
                    "Retest the affected flow after each fix.",
                ),
                deliverable=f"A launch-blocker fix log for {focus}.",
                done_when="The main flow has no known launch-blocking issue.",
                why_it_matters="Focused fixes make the app safer to release.",
                priority="high",
                estimated_hours=5.0,
            ),
        ]

    if domain == "study_learning":
        return [
            _task_blueprint(
                title=f"Assess {focus} current level",
                goal=f"Find strengths and weak areas before studying {focus}.",
                steps=(
                    "Take a short diagnostic quiz or explain key topics from memory.",
                    "Mark questions or concepts that feel slow or confusing.",
                    "Rank the top weak areas by exam impact.",
                ),
                deliverable=f"A skills gap list for {focus}.",
                done_when="The top weak areas are ranked and ready to study.",
                why_it_matters="Studying weak areas first makes each session more useful.",
                priority="high",
                estimated_hours=1.5,
            ),
            _task_blueprint(
                title=f"Divide {focus} syllabus topics",
                goal=f"Turn {focus} material into studyable topic groups.",
                steps=(
                    "List chapters, lecture units, assignments, and exam topics.",
                    "Group related formulas, concepts, and problem types together.",
                    "Mark topics as strong, medium, or weak.",
                ),
                deliverable=f"A topic map for {focus}.",
                done_when="Every exam topic has a strength rating.",
                why_it_matters="A topic map shows what must be covered before the deadline.",
                priority="high",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title=f"Gather {focus} study resources",
                goal=f"Prepare the materials needed to study {focus} efficiently.",
                steps=(
                    "Collect lecture notes, textbook sections, practice sets, and past exams.",
                    "Match each resource to a syllabus topic.",
                    "Remove duplicate or low-quality resources.",
                ),
                deliverable=f"A resource list organized by {focus} topic.",
                done_when="Each weak topic has at least one trusted resource.",
                why_it_matters="Prepared resources prevent wasting study time searching.",
                priority="medium",
                estimated_hours=1.5,
            ),
            _task_blueprint(
                title=f"Schedule {focus} study blocks",
                goal=f"Fit {focus} study into the weeks before the deadline.",
                steps=(
                    "Choose study days and session lengths that match available hours.",
                    "Assign one topic and one practice set to each session.",
                    "Reserve review and mock-exam days near the end.",
                ),
                deliverable=f"A weekly study calendar for {focus}.",
                done_when="Every week has topics, practice, and review time assigned.",
                why_it_matters="A schedule turns exam prep into steady progress.",
                priority="high",
                estimated_hours=1.0,
            ),
            _task_blueprint(
                title=f"Learn weakest {focus} topic",
                goal=f"Start with the {focus} topic most likely to cost marks.",
                steps=(
                    "Read the relevant notes or textbook section slowly.",
                    "Write formulas, definitions, and common question patterns.",
                    "Solve a few untimed examples while checking each step.",
                ),
                deliverable=f"Study notes for the weakest {focus} topic.",
                done_when="The topic has notes and solved examples.",
                why_it_matters="Early weak-topic work gives the biggest improvement.",
                priority="high",
                estimated_hours=3.0,
            ),
            _task_blueprint(
                title=f"Solve {focus} practice questions",
                goal=f"Build exam skill through active {focus} problem solving.",
                steps=(
                    "Choose a mixed set of practice questions for the current topic.",
                    "Solve without looking at solutions first.",
                    "Mark mistakes by concept, calculation, wording, or time pressure.",
                ),
                deliverable=f"A completed {focus} practice set with error notes.",
                done_when="Practice answers are checked and mistakes are categorized.",
                why_it_matters="Practice exposes gaps that reading alone hides.",
                priority="medium",
                estimated_hours=3.0,
            ),
            _task_blueprint(
                title=f"Complete timed {focus} assessment",
                goal=f"Test {focus} readiness under exam-like time pressure.",
                steps=(
                    "Choose a past exam, mock paper, or mixed timed set.",
                    "Set a timer and avoid notes during the attempt.",
                    "Score the attempt and note where time was lost.",
                ),
                deliverable=f"A timed {focus} assessment score sheet.",
                done_when="The assessment is scored with timing and mistake notes.",
                why_it_matters="Timed practice reveals readiness more honestly.",
                priority="high",
                estimated_hours=2.5,
            ),
            _task_blueprint(
                title=f"Review {focus} errors",
                goal=f"Turn {focus} mistakes into a targeted revision list.",
                steps=(
                    "Review every wrong or guessed answer from practice.",
                    "Write the correct method next to the original mistake.",
                    "Group errors into concepts that need revision.",
                ),
                deliverable=f"An error log for {focus}.",
                done_when="Each mistake has a cause and correction.",
                why_it_matters="Error review prevents repeating the same mistakes.",
                priority="high",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title=f"Revise weak {focus} areas",
                goal=f"Close the gaps found during {focus} practice.",
                steps=(
                    "Pick the highest-frequency error category.",
                    "Review the concept and solve three similar questions.",
                    "Update the formula or concept sheet with the correction.",
                ),
                deliverable=f"A revised weak-area note for {focus}.",
                done_when="The selected weak area has fresh examples solved correctly.",
                why_it_matters="Targeted revision improves exam performance faster.",
                priority="medium",
                estimated_hours=2.5,
            ),
            _task_blueprint(
                title=f"Create {focus} formula sheet",
                goal=f"Condense key {focus} facts into a final review aid.",
                steps=(
                    "List formulas, definitions, assumptions, and common traps.",
                    "Add one example or warning beside difficult items.",
                    "Keep the sheet short enough to review quickly.",
                ),
                deliverable=f"A concise {focus} formula and concept sheet.",
                done_when="The sheet covers high-value concepts without clutter.",
                why_it_matters="A compact sheet makes final revision easier.",
                priority="medium",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title=f"Take final {focus} mock exam",
                goal=f"Confirm final readiness for the {focus} exam.",
                steps=(
                    "Choose a full mock or past paper.",
                    "Complete it under exam conditions.",
                    "Score it and choose the final revision priorities.",
                ),
                deliverable=f"A final mock exam result for {focus}.",
                done_when="The mock is scored and final revision topics are chosen.",
                why_it_matters="A final mock turns preparation into a clear readiness check.",
                priority="high",
                estimated_hours=3.0,
            ),
            _task_blueprint(
                title=f"Plan {focus} exam-day review",
                goal=f"Use the last day before {focus} without panic studying.",
                steps=(
                    "Choose the formula sheet, error log, and two light practice sets.",
                    "Set a stop time for studying and a sleep target.",
                    "Prepare exam materials, calculator, ID, and location details.",
                ),
                deliverable=f"An exam-day review and materials checklist for {focus}.",
                done_when="Review materials and exam logistics are ready.",
                why_it_matters="A calm final routine protects performance.",
                priority="medium",
                estimated_hours=1.0,
            ),
        ]

    if domain == "business_marketing":
        return [
            _task_blueprint(
                title=f"Define {focus} target customer",
                goal=f"Identify who is most likely to buy or use {focus}.",
                steps=(
                    "Write the customer segment, pain point, budget, and buying trigger.",
                    "List where those customers already communicate or shop.",
                    "Choose the first segment to contact.",
                ),
                deliverable=f"A target-customer profile for {focus}.",
                done_when="The first customer segment and buying trigger are clear.",
                why_it_matters="A focused customer makes marketing less random.",
                priority="high",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title=f"Validate {focus} customer problem",
                goal=f"Check whether customers actually need {focus}.",
                steps=(
                    "Write five short validation questions.",
                    "Interview or message potential customers from the target segment.",
                    "Record exact objections, current alternatives, and buying interest.",
                ),
                deliverable=f"A validation notes table for {focus}.",
                done_when="Customer responses show the problem, alternatives, and interest level.",
                why_it_matters="Validation reduces the chance of launching an unwanted offer.",
                priority="high",
                estimated_hours=3.0,
            ),
            _task_blueprint(
                title=f"Research {focus} competitors",
                goal=f"Understand how similar offers win customers.",
                steps=(
                    "List direct and indirect competitors in the same market.",
                    "Compare pricing, ordering steps, delivery, quality, and messaging.",
                    "Write one gap your offer can own.",
                ),
                deliverable=f"A competitor comparison for {focus}.",
                done_when="Competitors are compared and one market gap is selected.",
                why_it_matters="Competitor research helps position the offer clearly.",
                priority="medium",
                estimated_hours=2.5,
            ),
            _task_blueprint(
                title=f"Define {focus} offer",
                goal=f"Turn {focus} into a clear offer customers can understand.",
                steps=(
                    "Write what customers get, how ordering works, and what is included.",
                    "Separate the launch offer from later additions.",
                    "Add proof, guarantee, delivery, or support details where relevant.",
                ),
                deliverable=f"A one-page offer description for {focus}.",
                done_when="The offer states who it helps, what it includes, and how to buy.",
                why_it_matters="A clear offer is easier to sell and test.",
                priority="high",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title=f"Calculate {focus} pricing",
                goal=f"Choose a price that fits costs, value, and customer expectations.",
                steps=(
                    "List direct costs, time, fees, delivery, and support effort.",
                    "Compare customer willingness to pay with competitor pricing.",
                    "Choose launch pricing and the minimum acceptable margin.",
                ),
                deliverable=f"A pricing calculation for {focus}.",
                done_when="Launch price and margin logic are documented.",
                why_it_matters="Pricing must support both sales and sustainability.",
                priority="high",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title=f"Create {focus} sales channel",
                goal=f"Set up the first reliable way customers can order {focus}.",
                steps=(
                    "Choose the channel, such as WhatsApp, Instagram, phone, web form, or referral.",
                    "Write the order steps and response template.",
                    "Test the channel with a sample customer request.",
                ),
                deliverable=f"A working sales channel for {focus}.",
                done_when="A sample order can move from inquiry to confirmation.",
                why_it_matters="A sales channel turns interest into measurable demand.",
                priority="high",
                estimated_hours=3.0,
            ),
            _task_blueprint(
                title=f"Prepare {focus} launch material",
                goal=f"Create the messages and visuals needed to announce {focus}.",
                steps=(
                    "Write a short announcement, offer description, and call to action.",
                    "Prepare images, examples, catalog items, or proof points.",
                    "Adapt the message for the chosen sales channel.",
                ),
                deliverable=f"A launch message pack for {focus}.",
                done_when="Launch copy and visuals are ready to publish or send.",
                why_it_matters="Good launch material makes the offer easy to understand quickly.",
                priority="medium",
                estimated_hours=3.0,
            ),
            _task_blueprint(
                title=f"Contact first {focus} customers",
                goal=f"Start real sales conversations for {focus}.",
                steps=(
                    "Create a list of likely first customers or partners.",
                    "Send a personalized launch message with a clear next step.",
                    "Track replies, objections, follow-ups, and orders.",
                ),
                deliverable=f"A first-customer outreach tracker for {focus}.",
                done_when="The first outreach batch is sent and tracked.",
                why_it_matters="Direct outreach creates the first demand signal.",
                priority="high",
                estimated_hours=3.0,
            ),
            _task_blueprint(
                title=f"Measure {focus} conversion",
                goal=f"See whether interest is turning into orders or commitments.",
                steps=(
                    "Track messages sent, replies, serious leads, orders, and lost deals.",
                    "Calculate reply rate and order conversion.",
                    "Identify the biggest drop-off in the buying process.",
                ),
                deliverable=f"A conversion report for {focus}.",
                done_when="Conversion metrics and main drop-off are recorded.",
                why_it_matters="Measurement shows what to improve next.",
                priority="medium",
                estimated_hours=1.5,
            ),
            _task_blueprint(
                title=f"Collect {focus} buyer feedback",
                goal=f"Learn what customers liked, doubted, or needed from {focus}.",
                steps=(
                    "Ask buyers and non-buyers why they did or did not order.",
                    "Record price, trust, timing, quality, and convenience feedback.",
                    "Choose the feedback that should change the offer first.",
                ),
                deliverable=f"A buyer feedback summary for {focus}.",
                done_when="Feedback is grouped into offer, price, channel, and trust issues.",
                why_it_matters="Customer feedback improves the next sales cycle.",
                priority="medium",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title=f"Adjust {focus} fulfillment process",
                goal=f"Make delivery or service execution smoother after first orders.",
                steps=(
                    "Map each step from order confirmation to completion.",
                    "Find delays, handoffs, mistakes, or unclear responsibilities.",
                    "Update the process and templates for the next orders.",
                ),
                deliverable=f"An improved fulfillment checklist for {focus}.",
                done_when="The next order can follow the updated checklist.",
                why_it_matters="Reliable fulfillment protects repeat business.",
                priority="medium",
                estimated_hours=2.5,
            ),
            _task_blueprint(
                title=f"Plan next {focus} outreach",
                goal=f"Use launch data to decide the next customer batch.",
                steps=(
                    "Review which segment responded best.",
                    "Refine the message, offer, or price based on evidence.",
                    "Create the next outreach list and date.",
                ),
                deliverable=f"A next outreach plan for {focus}.",
                done_when="The next batch, message, and timing are chosen.",
                why_it_matters="A measured next batch builds momentum after launch.",
                priority="low",
                estimated_hours=1.5,
            ),
        ]

    if domain == "content_creator":
        return [
            _task_blueprint(
                title=f"Define {focus} audience",
                goal=f"Choose exactly who {focus} should help or entertain.",
                steps=(
                    "Write the viewer level, goal, pain point, and preferred format.",
                    "List questions the audience already asks.",
                    "Choose the promise for the first content series.",
                ),
                deliverable=f"An audience profile for {focus}.",
                done_when="The audience, promise, and first questions are documented.",
                why_it_matters="Audience clarity makes content easier to choose and judge.",
                priority="high",
                estimated_hours=1.5,
            ),
            _task_blueprint(
                title=f"Research {focus} content gaps",
                goal=f"Find topics where {focus} can be useful and distinct.",
                steps=(
                    "Review similar channels, posts, or creators.",
                    "List beginner questions, confusing explanations, and missing examples.",
                    "Choose the first gap your content will address.",
                ),
                deliverable=f"A content gap list for {focus}.",
                done_when="At least five topic gaps or viewer questions are listed.",
                why_it_matters="Research helps content answer real demand.",
                priority="medium",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title=f"Choose {focus} content pillars",
                goal=f"Create repeatable themes for planning {focus}.",
                steps=(
                    "Group topic ideas into three or four recurring pillars.",
                    "Define what belongs and does not belong in each pillar.",
                    "Pick the first pillar for the launch batch.",
                ),
                deliverable=f"A content pillar map for {focus}.",
                done_when="The channel has recurring themes and a first launch pillar.",
                why_it_matters="Pillars keep content consistent without becoming repetitive.",
                priority="high",
                estimated_hours=1.5,
            ),
            _task_blueprint(
                title=f"Draft first {focus} scripts",
                goal=f"Turn topic ideas into recordable content.",
                steps=(
                    "Choose the first three topics from the launch pillar.",
                    "Write a hook, teaching points, example, and call to action for each.",
                    "Cut anything that distracts from the beginner outcome.",
                ),
                deliverable=f"Three draft scripts for {focus}.",
                done_when="Each script has a clear hook, body, example, and ending.",
                why_it_matters="Scripts make recording faster and clearer.",
                priority="high",
                estimated_hours=4.0,
            ),
            _task_blueprint(
                title=f"Record {focus} pilot lesson",
                goal=f"Create the first real piece of {focus} content.",
                steps=(
                    "Set up audio, screen, camera, or notes for the chosen format.",
                    "Record one pilot lesson from script to ending.",
                    "Note what felt unclear, too long, or hard to explain.",
                ),
                deliverable=f"A recorded pilot lesson for {focus}.",
                done_when="One pilot recording exists and has review notes.",
                why_it_matters="A pilot reveals production problems before a full batch.",
                priority="high",
                estimated_hours=3.0,
            ),
            _task_blueprint(
                title=f"Edit {focus} upload template",
                goal=f"Create a repeatable editing and publishing format for {focus}.",
                steps=(
                    "Choose intro length, captions, examples, and ending structure.",
                    "Edit the pilot into the target length and style.",
                    "Save reusable title, description, tags, or asset templates.",
                ),
                deliverable=f"An edited pilot and upload template for {focus}.",
                done_when="The pilot is ready to publish and the template is reusable.",
                why_it_matters="A template speeds up future content production.",
                priority="medium",
                estimated_hours=4.0,
            ),
            _task_blueprint(
                title=f"Create {focus} thumbnail style",
                goal=f"Make the content recognizable and clickable.",
                steps=(
                    "Choose a simple visual style, title pattern, and contrast rules.",
                    "Create thumbnails or cover images for the first pieces.",
                    "Check readability on a small mobile screen.",
                ),
                deliverable=f"A thumbnail or cover template for {focus}.",
                done_when="The first content piece has a readable thumbnail or cover.",
                why_it_matters="Packaging affects whether the right audience clicks.",
                priority="medium",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title=f"Publish first {focus} video",
                goal=f"Release the first content piece and start collecting signals.",
                steps=(
                    "Upload the edited content with title, description, thumbnail, and tags.",
                    "Check playback, links, captions, and formatting after publishing.",
                    "Share it in one relevant channel or community.",
                ),
                deliverable=f"A published first piece for {focus}.",
                done_when="The content is live, checked, and shared once.",
                why_it_matters="Publishing creates real feedback and momentum.",
                priority="high",
                estimated_hours=1.5,
            ),
            _task_blueprint(
                title=f"Schedule {focus} content calendar",
                goal=f"Plan a realistic publishing rhythm for {focus}.",
                steps=(
                    "Choose a cadence that matches available production time.",
                    "Assign topics, script dates, recording dates, and publish dates.",
                    "Leave buffer time for editing and unexpected delays.",
                ),
                deliverable=f"A four-week content calendar for {focus}.",
                done_when="The next pieces have production and publish dates.",
                why_it_matters="A calendar turns a channel idea into a repeatable process.",
                priority="medium",
                estimated_hours=1.5,
            ),
            _task_blueprint(
                title=f"Collect {focus} viewer feedback",
                goal=f"Learn what viewers understood, skipped, or wanted next.",
                steps=(
                    "Read comments, questions, retention signals, and direct messages.",
                    "Ask two viewers what was clear and what was confusing.",
                    "Turn feedback into specific improvements for the next piece.",
                ),
                deliverable=f"A viewer feedback note for {focus}.",
                done_when="Feedback is grouped into clarity, topic, and format improvements.",
                why_it_matters="Viewer feedback improves teaching and topic selection.",
                priority="medium",
                estimated_hours=1.5,
            ),
            _task_blueprint(
                title=f"Improve next {focus} lesson",
                goal=f"Apply feedback before creating more {focus} content.",
                steps=(
                    "Choose one script, one recording, and one editing improvement.",
                    "Update the next script and template with those changes.",
                    "Compare the next piece against the pilot notes.",
                ),
                deliverable=f"An improved next lesson plan for {focus}.",
                done_when="The next lesson includes the selected improvements.",
                why_it_matters="Small iteration makes every upload stronger.",
                priority="medium",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title=f"Track {focus} channel metrics",
                goal=f"Measure whether {focus} is reaching and helping the audience.",
                steps=(
                    "Track views, watch time, retention, clicks, comments, and subscriber changes.",
                    "Compare metrics by topic and format.",
                    "Choose the next content decision from the strongest signal.",
                ),
                deliverable=f"A simple metrics dashboard for {focus}.",
                done_when="Each published piece has metrics and a next-content decision.",
                why_it_matters="Metrics help separate useful signals from guesses.",
                priority="low",
                estimated_hours=1.5,
            ),
        ]

    if domain == "event_trip":
        return [
            _task_blueprint(
                title=f"Confirm {focus} venue",
                goal=f"Secure the place and timing needed for {focus}.",
                steps=(
                    "List venue options, capacity, access rules, and available dates.",
                    "Confirm permission, booking, or reservation requirements.",
                    "Write the final date, time, location, and contact person.",
                ),
                deliverable=f"A confirmed venue note for {focus}.",
                done_when="The venue, date, time, and owner are confirmed.",
                why_it_matters="A confirmed venue anchors every other event task.",
                priority="high",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title=f"Define {focus} participation rules",
                goal=f"Set fair and clear rules for everyone joining {focus}.",
                steps=(
                    "Write who can attend and what they should bring or prepare.",
                    "Define limits, safety rules, acceptance criteria, or etiquette.",
                    "Prepare answers for likely participant questions.",
                ),
                deliverable=f"A participation rule sheet for {focus}.",
                done_when="Rules are ready to share with participants.",
                why_it_matters="Rules reduce confusion before and during the event.",
                priority="high",
                estimated_hours=1.5,
            ),
            _task_blueprint(
                title=f"Build {focus} registration form",
                goal=f"Collect participant details before {focus}.",
                steps=(
                    "Add fields for name, contact, attendance, preferences, and constraints.",
                    "Include any consent, item, meal, transport, or accessibility needs.",
                    "Test the form with one sample submission.",
                ),
                deliverable=f"A registration form for {focus}.",
                done_when="A sample registration submits successfully.",
                why_it_matters="Registration gives the event team reliable numbers.",
                priority="medium",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title=f"Collect {focus} preferences",
                goal=f"Understand participant needs before final preparation.",
                steps=(
                    "Review registration answers for categories, quantities, and special requests.",
                    "Group preferences into setup, materials, communication, and support needs.",
                    "Adjust the event plan using the strongest patterns.",
                ),
                deliverable=f"A participant preference summary for {focus}.",
                done_when="Preferences are summarized and reflected in the event plan.",
                why_it_matters="Participant data makes the event more useful.",
                priority="medium",
                estimated_hours=1.5,
            ),
            _task_blueprint(
                title=f"Recruit {focus} volunteers",
                goal=f"Assign enough help to run {focus} smoothly.",
                steps=(
                    "List roles such as setup, welcome, stations, guidance, and cleanup.",
                    "Invite volunteers and confirm their availability.",
                    "Send each volunteer a role, time, and responsibility.",
                ),
                deliverable=f"A volunteer roster for {focus}.",
                done_when="Every critical role has an assigned volunteer.",
                why_it_matters="Clear volunteer roles prevent event-day chaos.",
                priority="high",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title=f"Prepare {focus} station supplies",
                goal=f"Gather the items needed to run {focus} on site.",
                steps=(
                    "List tables, signs, labels, pens, bags, check-in sheets, or equipment.",
                    "Assign each supply to a person or source.",
                    "Pack supplies by station or event area.",
                ),
                deliverable=f"A packed supply checklist for {focus}.",
                done_when="Critical supplies are packed and assigned to stations.",
                why_it_matters="Prepared supplies keep the event moving on the day.",
                priority="medium",
                estimated_hours=2.0,
            ),
            _task_blueprint(
                title=f"Publish {focus} announcement",
                goal=f"Tell the right audience how to join {focus}.",
                steps=(
                    "Write the announcement with date, location, rules, and registration link.",
                    "Share it through the most relevant channels.",
                    "Send one reminder before the registration deadline.",
                ),
                deliverable=f"A published announcement for {focus}.",
                done_when="The announcement is live and the registration link works.",
                why_it_matters="Good communication drives attendance and preparedness.",
                priority="high",
                estimated_hours=1.5,
            ),
            _task_blueprint(
                title=f"Run {focus} event",
                goal=f"Execute {focus} according to the prepared plan.",
                steps=(
                    "Set up venue areas, signage, registration, and stations before arrivals.",
                    "Brief volunteers and handle participant flow during the event.",
                    "Close the event with cleanup, lost items, and final counts.",
                ),
                deliverable=f"A completed {focus} event.",
                done_when="The event is completed and the space is cleaned up.",
                why_it_matters="Execution turns planning into the actual participant experience.",
                priority="high",
                estimated_hours=5.0,
            ),
            _task_blueprint(
                title=f"Record {focus} attendance",
                goal=f"Capture what happened during {focus}.",
                steps=(
                    "Count attendees, no-shows, supplies used, and remaining items.",
                    "Record incidents, questions, delays, and positive moments.",
                    "Save photos or documents needed for reporting.",
                ),
                deliverable=f"An event results log for {focus}.",
                done_when="Attendance and outcome numbers are recorded.",
                why_it_matters="Event records help evaluate success and plan follow-up.",
                priority="medium",
                estimated_hours=1.0,
            ),
            _task_blueprint(
                title=f"Thank {focus} participants",
                goal=f"Close the loop with everyone who helped or attended {focus}.",
                steps=(
                    "Send thank-you messages to volunteers, hosts, and participants.",
                    "Share useful outcomes, remaining items, or next steps.",
                    "Invite feedback while the event is still fresh.",
                ),
                deliverable=f"A follow-up message for {focus}.",
                done_when="Thank-you and feedback messages are sent.",
                why_it_matters="Follow-up builds goodwill for future events.",
                priority="low",
                estimated_hours=1.0,
            ),
            _task_blueprint(
                title=f"Review {focus} feedback",
                goal=f"Learn what should change before repeating {focus}.",
                steps=(
                    "Collect comments from participants, volunteers, and venue contacts.",
                    "Sort feedback into logistics, communication, rules, and supplies.",
                    "Choose the top improvements for next time.",
                ),
                deliverable=f"A feedback review for {focus}.",
                done_when="Top improvements are documented with owners.",
                why_it_matters="Feedback makes the next event easier and better.",
                priority="medium",
                estimated_hours=1.5,
            ),
            _task_blueprint(
                title=f"Plan {focus} follow-up",
                goal=f"Decide whether and how {focus} should continue.",
                steps=(
                    "Review attendance, feedback, remaining demand, and available helpers.",
                    "Choose whether to repeat, expand, or close the event series.",
                    "Write the next date, owner, or closure message.",
                ),
                deliverable=f"A follow-up decision note for {focus}.",
                done_when="The next event decision and owner are clear.",
                why_it_matters="A follow-up decision keeps momentum from fading.",
                priority="low",
                estimated_hours=1.0,
            ),
        ]

    if domain == "personal_habit":
        return [
            _task_blueprint(
                title=f"Define {focus} daily cue",
                goal=f"Attach {focus} to a reliable moment in the day.",
                steps=(
                    "Choose the exact cue that will start the habit.",
                    "Write what happens immediately before and after the habit.",
                    "Place a reminder where the cue happens.",
                ),
                deliverable=f"A cue plan for {focus}.",
                done_when="The habit has a fixed cue and visible reminder.",
                why_it_matters="A cue makes the habit easier to start automatically.",
                priority="high",
                estimated_hours=0.5,
            ),
            _task_blueprint(
                title=f"Choose {focus} first material",
                goal=f"Make the first week of {focus} easy to begin.",
                steps=(
                    "Pick material that matches the desired difficulty and time limit.",
                    "Prepare enough for the first week.",
                    "Remove material that feels too hard or uninteresting.",
                ),
                deliverable=f"A first-week material list for {focus}.",
                done_when="The first week can start without choosing what to use each day.",
                why_it_matters="Prepared material lowers decision friction.",
                priority="high",
                estimated_hours=0.75,
            ),
            _task_blueprint(
                title=f"Set {focus} time block",
                goal=f"Protect a realistic daily slot for {focus}.",
                steps=(
                    "Choose the exact start time and duration.",
                    "Check it against sleep, work, school, and family demands.",
                    "Write a shorter fallback version for busy days.",
                ),
                deliverable=f"A daily time-block rule for {focus}.",
                done_when="The standard and fallback durations are written.",
                why_it_matters="A protected block makes consistency more likely.",
                priority="high",
                estimated_hours=0.5,
            ),
            _task_blueprint(
                title=f"Prepare {focus} environment",
                goal=f"Set up the space so {focus} can start with less resistance.",
                steps=(
                    "Choose the location and remove obvious distractions.",
                    "Place the needed material, timer, notebook, or water nearby.",
                    "Make the setup ready the night before when possible.",
                ),
                deliverable=f"A ready environment for {focus}.",
                done_when="The habit space is prepared before the next session.",
                why_it_matters="Environment design reduces reliance on motivation.",
                priority="medium",
                estimated_hours=0.5,
            ),
            _task_blueprint(
                title=f"Start {focus} first week",
                goal=f"Complete the first seven days of {focus} with a realistic target.",
                steps=(
                    "Do the habit at the planned cue and time.",
                    "Use the fallback version instead of skipping when the day is hard.",
                    "Mark each completed day immediately.",
                ),
                deliverable=f"A first-week streak log for {focus}.",
                done_when="Seven days are attempted and logged.",
                why_it_matters="The first week proves the routine can fit real life.",
                priority="high",
                estimated_hours=2.5,
            ),
            _task_blueprint(
                title=f"Track {focus} minutes",
                goal=f"Measure consistency and actual time spent on {focus}.",
                steps=(
                    "Record minutes completed each day.",
                    "Note mood, energy, distractions, and missed-day reasons.",
                    "Highlight patterns that help or hurt consistency.",
                ),
                deliverable=f"A daily tracker for {focus}.",
                done_when="Each day has minutes and a short note.",
                why_it_matters="Tracking shows what makes the habit sustainable.",
                priority="medium",
                estimated_hours=0.5,
            ),
            _task_blueprint(
                title=f"Remove {focus} blockers",
                goal=f"Reduce the obstacles that make {focus} harder to repeat.",
                steps=(
                    "Review missed or difficult days from the tracker.",
                    "Choose the top blocker, such as phone use, tiredness, or unclear material.",
                    "Add one prevention step before the next session.",
                ),
                deliverable=f"A blocker removal note for {focus}.",
                done_when="The biggest blocker has a prevention step.",
                why_it_matters="Removing friction is more reliable than trying harder.",
                priority="medium",
                estimated_hours=0.75,
            ),
            _task_blueprint(
                title=f"Plan {focus} missed-day reset",
                goal=f"Keep {focus} alive after an imperfect day.",
                steps=(
                    "Write what counts as a minimum successful session.",
                    "Decide exactly what to do after a missed day.",
                    "Place the reset rule next to the tracker.",
                ),
                deliverable=f"A missed-day reset rule for {focus}.",
                done_when="A missed day has a clear next action.",
                why_it_matters="Reset rules prevent one miss from becoming a full stop.",
                priority="medium",
                estimated_hours=0.5,
            ),
            _task_blueprint(
                title=f"Review {focus} weekly notes",
                goal=f"Learn what is working in the habit routine.",
                steps=(
                    "Review completed minutes, missed days, and notes.",
                    "Write what helped most and what got in the way.",
                    "Choose one adjustment for the next week.",
                ),
                deliverable=f"A weekly habit review for {focus}.",
                done_when="The next-week adjustment is written.",
                why_it_matters="Review keeps the habit realistic as life changes.",
                priority="medium",
                estimated_hours=0.75,
            ),
            _task_blueprint(
                title=f"Adjust {focus} difficulty",
                goal=f"Keep {focus} challenging enough without becoming heavy.",
                steps=(
                    "Check whether the current duration or material feels too easy or too hard.",
                    "Adjust time, difficulty, or environment by one small step.",
                    "Test the change for three sessions before changing again.",
                ),
                deliverable=f"A difficulty adjustment plan for {focus}.",
                done_when="One small difficulty change is selected and tested.",
                why_it_matters="Right-sized difficulty protects consistency.",
                priority="low",
                estimated_hours=0.5,
            ),
            _task_blueprint(
                title=f"Reward {focus} consistency",
                goal=f"Make progress on {focus} satisfying enough to continue.",
                steps=(
                    "Choose a small reward for completing a week.",
                    "Connect the reward to the tracker result.",
                    "Avoid rewards that undermine the habit.",
                ),
                deliverable=f"A weekly reward rule for {focus}.",
                done_when="The reward is tied to a clear consistency target.",
                why_it_matters="Positive reinforcement makes repetition more appealing.",
                priority="low",
                estimated_hours=0.5,
            ),
            _task_blueprint(
                title=f"Extend {focus} next month",
                goal=f"Decide how {focus} should continue after the first month.",
                steps=(
                    "Review the month of minutes, notes, and missed-day resets.",
                    "Choose whether to keep, increase, or simplify the habit.",
                    "Pick the next material, cue, and monthly target.",
                ),
                deliverable=f"A next-month plan for {focus}.",
                done_when="The next month has a cue, target, and material ready.",
                why_it_matters="A monthly plan turns a starter habit into a durable routine.",
                priority="medium",
                estimated_hours=1.0,
            ),
        ]

    return _generic_project_blueprints(focus=focus, idea_context=idea_context)


def _expanded_domain_blueprints(
    *,
    domain: str,
    focus: str,
    task_count: int,
    idea_context: str = "",
) -> list[dict[str, Any]]:
    blueprints = (
        _fitness_blueprints(focus)
        if domain == "fitness_health"
        else _generic_domain_blueprints(domain, focus, idea_context)
    )

    while len(blueprints) < task_count:
        index = len(blueprints) + 1
        blueprints.append(
            _task_blueprint(
                title=f"Document {focus} handoff step {index}",
                goal=f"Capture the next operational detail needed to continue {focus}.",
                steps=(
                    "Write the next real action that is not already covered.",
                    "Name the owner, input, and expected output for that action.",
                    "Add the action to the tracker or handoff notes.",
                ),
                deliverable=f"A handoff action note for {focus}.",
                done_when="The new action has an owner, input, and output.",
                why_it_matters="Documented handoff steps keep execution from stalling.",
                priority="low",
                estimated_hours=1.0,
            )
        )

    return blueprints


def _build_domain_local_tasks(
    *,
    domain: str,
    focus: str,
    task_count: int,
    idea_context: str = "",
) -> list[dict[str, Any]]:
    blueprints = _expanded_domain_blueprints(
        domain=domain,
        focus=focus,
        task_count=task_count,
        idea_context=idea_context,
    )
    tasks: list[dict[str, Any]] = []

    for index, blueprint in enumerate(blueprints[:task_count]):
        tasks.append(
            {
                "suggested_order": index + 1,
                "title": str(blueprint["title"]),
                "description": _domain_task_description(
                    goal=str(blueprint["goal"]),
                    steps=blueprint["steps"],
                    deliverable=str(blueprint["deliverable"]),
                    done_when=str(blueprint["done_when"]),
                    why_it_matters=str(blueprint["why_it_matters"]),
                ),
                "priority": blueprint["priority"],
                "estimated_hours": blueprint["estimated_hours"],
            }
        )

    return tasks


def _domain_milestones(
    *,
    domain: str,
    focus: str,
    include_milestones: bool,
) -> list[dict[str, Any]]:
    if not include_milestones:
        return []

    if domain == "fitness_health":
        return [
            {
                "name": "Baseline recorded",
                "description": f"The starting point for {focus} is measured safely.",
                "suggested_order": 1,
            },
            {
                "name": "Routine started",
                "description": f"The first week of {focus} training is scheduled and tracked.",
                "suggested_order": 2,
            },
            {
                "name": "Progress reviewed",
                "description": f"Training volume, form, and recovery are reviewed after 14 days.",
                "suggested_order": 3,
            },
        ]

    return [
        {
            "name": "Direction confirmed",
            "description": f"The next outcome for {focus} is clear.",
            "suggested_order": 1,
        },
        {
            "name": "Execution underway",
            "description": f"The main actions for {focus} are started and tracked.",
            "suggested_order": 2,
        },
        {
            "name": "Progress reviewed",
            "description": f"The current result for {focus} is reviewed and adjusted.",
            "suggested_order": 3,
        },
    ]


def _domain_risks(domain: str) -> list[dict[str, str]]:
    if domain == "fitness_health":
        return [
            {
                "risk": "Doing too many reps too soon can irritate wrists, elbows, or shoulders.",
                "recommendation": "Increase volume gradually and stop if sharp pain appears.",
            },
            {
                "risk": "Poor form can turn daily pushups into strain instead of progress.",
                "recommendation": "Use easier variations whenever full pushups lose control.",
            },
        ]

    return [
        {
            "risk": "The plan may be too broad to finish comfortably.",
            "recommendation": "Keep the next outcome small enough to complete and review.",
        },
        {
            "risk": "Progress may stall without a tracking habit.",
            "recommendation": "Record the result of each work session before moving on.",
        },
    ]


def _domain_recommendations(domain: str) -> list[str]:
    if domain == "fitness_health":
        return [
            "Start below your maximum and build volume gradually.",
            "Prioritize clean form over hitting the daily number at any cost.",
            "Use pain, soreness, and effort notes to adjust the next target.",
        ]

    return [
        "Start with the highest-priority action before adding optional work.",
        "Keep every task tied to a visible result.",
        "Review the plan after the first checkpoint and adjust it.",
    ]


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
        f"Why it matters: {benefit}"
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
                "Remove anything that does not support the next practical result.",
            ),
            "deliverable": "A prioritized planning checklist for {topic}.",
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
                "Choose the fixes that block the next useful result.",
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
    domain = _classify_idea_domain(f"{project_title} {idea_context}")
    focus = _focus_from_context(idea_context, domain)
    include_milestones = "Return an empty milestones array" not in prompt
    tasks = _build_domain_local_tasks(
        domain=domain,
        focus=focus,
        task_count=task_count,
        idea_context=idea_context,
    )

    plan = {
        "domain": domain,
        "summary": (
            f"Generated a {domain.replace('_', ' ')} plan for "
            f"{project_title} with {len(tasks)} tasks."
        ),
        "tasks": tasks,
        "milestones": _domain_milestones(
            domain=domain,
            focus=focus,
            include_milestones=include_milestones,
        ),
        "risks": _domain_risks(domain),
        "recommendations": _domain_recommendations(domain),
    }

    return json.dumps(plan, ensure_ascii=False)


def generate_local_planner_reply(prompt: str) -> str:
    return _generate_with_local_planner(prompt)


def generate_ai_reply_from_provider(
    prompt: str,
    response_mime_type: str | None = None,
    use_local_fallback: bool = True,
) -> str | None:
    clear_last_ai_provider_failure_reason()
    provider = settings.ai_provider.strip().lower()
    logger.info(
        "AI provider selected. ai_provider=%s gemini_api_key_exists=%s gemini_model=%s gemini_timeout_seconds=%s response_mime_type=%s use_local_fallback=%s",
        provider or "local",
        bool(settings.gemini_api_key),
        settings.gemini_model,
        settings.gemini_timeout_seconds,
        response_mime_type or "text/plain",
        use_local_fallback,
    )

    if provider == "gemini":
        gemini_reply = _generate_with_gemini(
            prompt,
            response_mime_type=response_mime_type,
        )

        if gemini_reply is not None:
            return gemini_reply

        if not use_local_fallback:
            logger.warning(
                "Gemini provider returned empty/None. Local provider fallback disabled."
            )
            return None

        logger.warning(
            "Gemini provider returned empty/None. Using local planner fallback."
        )
        return _generate_with_local_planner(prompt)

    if provider in {"", "local", "fallback"}:
        _set_last_ai_provider_failure_reason("AI_PROVIDER was local")
        logger.warning(
            "AI provider is local. reason=ai_provider_not_gemini ai_provider=%s",
            provider or "local",
        )
        if not use_local_fallback:
            return None

        return _generate_with_local_planner(prompt)

    _set_last_ai_provider_failure_reason(f"Unsupported AI_PROVIDER {provider}")
    logger.warning(
        "Unsupported AI provider. reason=unsupported_ai_provider ai_provider=%s",
        provider,
    )
    if not use_local_fallback:
        return None

    return _generate_with_local_planner(prompt)
