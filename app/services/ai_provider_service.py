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
    "context",
    "daily",
    "day",
    "do",
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
    "use",
    "user",
    "users",
    "want",
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
    "homework",
    "learn",
    "lesson",
    "practice test",
    "quiz",
    "read",
    "revision",
    "study",
}

SOFTWARE_KEYWORDS = {
    "api",
    "app",
    "backend",
    "bug",
    "code",
    "database",
    "feature",
    "flutter",
    "frontend",
    "mobile",
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
    "launch",
    "lead",
    "marketing",
    "pricing",
    "sales",
    "shop",
    "store",
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
    "tiktok",
    "video",
    "youtube",
}

EVENT_TRIP_KEYWORDS = {
    "conference",
    "event",
    "party",
    "trip",
    "travel",
    "vacation",
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
    "routine",
    "sleep",
    "wake",
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
        logger.warning("Gemini API key is missing.")
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
                "Gemini API error. status=%s body=%s",
                response.status_code,
                response.text[:800],
            )
            return None

        return _extract_gemini_text(response.json())

    except httpx.TimeoutException as exc:
        logger.warning("Gemini API timeout: %s", type(exc).__name__)
        return None

    except httpx.HTTPError as exc:
        logger.warning("Gemini HTTP error: %s", type(exc).__name__)
        return None

    except (KeyError, IndexError, TypeError, ValueError) as exc:
        logger.warning(
            "Gemini response parsing error: %s",
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


def _contains_any_keyword(value: str, keywords: set[str]) -> bool:
    lowered = value.lower()
    return any(keyword in lowered for keyword in keywords)


def _classify_idea_domain(idea_context: str) -> str:
    if _contains_any_keyword(idea_context, FITNESS_KEYWORDS):
        return "fitness_health"

    if _contains_any_keyword(idea_context, STUDY_KEYWORDS):
        return "study_learning"

    if _contains_any_keyword(idea_context, SOFTWARE_KEYWORDS):
        return "software_app"

    if _contains_any_keyword(idea_context, BUSINESS_KEYWORDS):
        return "business_marketing"

    if _contains_any_keyword(idea_context, CONTENT_KEYWORDS):
        return "content_creator"

    if _contains_any_keyword(idea_context, EVENT_TRIP_KEYWORDS):
        return "event_trip"

    if _contains_any_keyword(idea_context, HABIT_KEYWORDS):
        return "personal_habit"

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
    if domain == "fitness_health":
        return _fitness_focus(idea_context)

    topic = _title_topic(idea_context)
    return topic if topic != "project" else "the plan"


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


def _fitness_blueprints(focus: str) -> list[dict[str, Any]]:
    return [
        {
            "title": "Test your current max pushups",
            "goal": "Find your safe starting point before aiming for 100 pushups a day.",
            "steps": (
                "Warm up your shoulders, wrists, and chest for 5 minutes.",
                "Do one controlled max-rep set with clean form and stop before form breaks.",
                "Write down total reps, difficulty, and any discomfort.",
            ),
            "deliverable": "A baseline pushup result log.",
            "done_when": "Your max clean reps and difficulty rating are recorded.",
            "why_it_matters": "A baseline keeps the plan challenging without starting too aggressively.",
            "priority": "high",
            "estimated_hours": 0.5,
        },
        {
            "title": "Set a safe daily starting volume",
            "goal": "Choose a daily rep target that builds consistency without overloading your joints.",
            "steps": (
                "Start with 40-60% of your clean max reps spread across the day.",
                "Cap the first week below failure so soreness stays manageable.",
                "Write the exact daily target and when you will do each set.",
            ),
            "deliverable": "A safe first-week pushup target.",
            "done_when": "Your daily reps and set schedule are written down.",
            "why_it_matters": "A conservative start makes the habit easier to sustain.",
            "priority": "high",
            "estimated_hours": 0.5,
        },
        {
            "title": "Split pushups into manageable sets",
            "goal": "Break the daily total into sets you can complete with good form.",
            "steps": (
                "Choose set sizes that feel like effort level 6-7 out of 10.",
                "Place sets at least 30-60 minutes apart if needed.",
                "Keep two reps in reserve on most sets during the first week.",
            ),
            "deliverable": "A set-by-set pushup schedule.",
            "done_when": "The daily target is divided into realistic sets.",
            "why_it_matters": "Smaller sets reduce form breakdown and make 100 reps more realistic.",
            "priority": "high",
            "estimated_hours": 0.5,
        },
        {
            "title": "Practice correct pushup form",
            "goal": "Make each rep useful and reduce shoulder, wrist, and lower-back strain.",
            "steps": (
                "Keep your body in a straight line from shoulders to ankles.",
                "Lower with control until your chest is near the floor.",
                "Stop or switch to incline pushups when your hips sag or elbows flare.",
            ),
            "deliverable": "A short form checklist for every set.",
            "done_when": "You can name and check the main form cues before training.",
            "why_it_matters": "Good form turns volume into strength instead of avoidable pain.",
            "priority": "high",
            "estimated_hours": 0.75,
        },
        {
            "title": "Create a 2-week progression schedule",
            "goal": "Move toward 100 daily pushups gradually instead of jumping there at once.",
            "steps": (
                "Increase daily reps by 5-10 only after two comfortable days.",
                "Use incline or knee pushups when full pushups become sloppy.",
                "Plan one lighter day after every 3-4 harder days.",
            ),
            "deliverable": "A 14-day pushup progression calendar.",
            "done_when": "Each day has a rep target, set plan, and easier variation if needed.",
            "why_it_matters": "Progression lets your muscles and joints adapt safely.",
            "priority": "medium",
            "estimated_hours": 1.0,
        },
        {
            "title": "Add recovery and pain rules",
            "goal": "Know when to rest, reduce reps, or stop before a small issue becomes an injury.",
            "steps": (
                "Schedule at least one lighter recovery day each week.",
                "Stop the session if you feel sharp pain in wrists, elbows, shoulders, or chest.",
                "Reduce volume by 30-50% if soreness changes your form the next day.",
            ),
            "deliverable": "A recovery and pain decision checklist.",
            "done_when": "You have clear stop, reduce, and rest rules.",
            "why_it_matters": "Recovery rules protect consistency and lower injury risk.",
            "priority": "high",
            "estimated_hours": 0.5,
        },
        {
            "title": "Track reps, sets, and difficulty",
            "goal": "Measure whether the pushup habit is getting easier or too intense.",
            "steps": (
                "Record each set with reps completed and effort level.",
                "Note soreness, pain, sleep, and missed sets.",
                "Highlight days where form or recovery felt worse than expected.",
            ),
            "deliverable": "A daily pushup tracking table.",
            "done_when": "Every training day has reps, sets, effort, and notes recorded.",
            "why_it_matters": "Tracking shows when to progress and when to back off.",
            "priority": "medium",
            "estimated_hours": 0.5,
        },
        {
            "title": "Review progress after 14 days",
            "goal": "Check whether the plan is moving you toward 100 pushups safely.",
            "steps": (
                "Compare day 1 and day 14 reps, effort, and soreness notes.",
                "Retest one clean max set only if your joints feel good.",
                "Choose whether to increase, hold, or reduce the next 2-week target.",
            ),
            "deliverable": "A 14-day progress review.",
            "done_when": "You have a clear next target based on recorded progress.",
            "why_it_matters": "A checkpoint prevents blindly chasing volume when your body needs adjustment.",
            "priority": "high",
            "estimated_hours": 0.75,
        },
        {
            "title": f"Warm up before {focus} sessions",
            "goal": f"Prepare your wrists, elbows, shoulders, and chest before {focus} work.",
            "steps": (
                "Circle wrists and shoulders for 60 seconds.",
                "Do 10 slow scapular pushups or wall pushups.",
                "Start the first set easier than the rest of the workout.",
            ),
            "deliverable": "A short warmup routine.",
            "done_when": "You complete the warmup before every training session.",
            "why_it_matters": "A warmup makes the first reps smoother and safer.",
            "priority": "medium",
            "estimated_hours": 0.25,
        },
        {
            "title": f"Choose easier {focus} variations",
            "goal": "Keep training productive on days when full reps are too difficult.",
            "steps": (
                "Use incline pushups on a table or wall when form breaks.",
                "Use knee pushups only after you can keep a straight torso.",
                "Return to full pushups when the easier version feels controlled.",
            ),
            "deliverable": "A ranked list of easier pushup variations.",
            "done_when": "You know which variation to use before form breaks.",
            "why_it_matters": "Easier variations let you finish volume without practicing bad form.",
            "priority": "medium",
            "estimated_hours": 0.5,
        },
        {
            "title": f"Pair {focus} with a daily cue",
            "goal": "Make the habit easier to remember.",
            "steps": (
                "Choose a cue such as after brushing teeth or before showering.",
                "Place the first set immediately after that cue.",
                "Track whether the cue helped you start without delay.",
            ),
            "deliverable": "A cue-based training trigger.",
            "done_when": "Your first daily set has a fixed cue.",
            "why_it_matters": "A cue reduces the chance that the habit depends on motivation.",
            "priority": "low",
            "estimated_hours": 0.25,
        },
        {
            "title": f"Plan your next {focus} target",
            "goal": "Choose the next realistic step after the first checkpoint.",
            "steps": (
                "Review the last 7 days of reps, effort, and recovery.",
                "Pick a target that increases volume only if form stayed clean.",
                "Write the next target before starting the next training block.",
            ),
            "deliverable": "A next-block pushup target.",
            "done_when": "The next target is based on actual training data.",
            "why_it_matters": "A measured next target keeps progress sustainable.",
            "priority": "medium",
            "estimated_hours": 0.5,
        },
    ]


def _generic_domain_blueprints(domain: str, focus: str) -> list[dict[str, Any]]:
    if domain == "software_app":
        return [
            {
                "title": f"Define {focus} core user flow",
                "goal": f"Clarify the main user path for {focus}.",
                "steps": (
                    "Write the primary user action from start to finish.",
                    "List the screens, data, and decisions needed for that path.",
                    "Remove any feature that is not needed for the first release.",
                ),
                "deliverable": "A core flow outline.",
                "done_when": "The main user path can be explained in ordered steps.",
                "why_it_matters": "A clear flow prevents scattered development work.",
                "priority": "high",
                "estimated_hours": 2.0,
            },
            {
                "title": f"Prioritize {focus} first-release features",
                "goal": f"Choose the smallest feature set that makes {focus} usable.",
                "steps": (
                    "List must-have, should-have, and later features.",
                    "Mark dependencies between must-have features.",
                    "Pick the first release scope.",
                ),
                "deliverable": "A prioritized feature list.",
                "done_when": "Every first-release feature has a clear reason to exist.",
                "why_it_matters": "Feature priority keeps the build focused.",
                "priority": "high",
                "estimated_hours": 2.0,
            },
        ]

    if domain == "study_learning":
        return [
            {
                "title": f"Check your current {focus} level",
                "goal": f"Find what you already know and where {focus} needs practice.",
                "steps": (
                    "Take a short quiz or explain the topic from memory.",
                    "Mark weak areas that felt slow or confusing.",
                    "Choose the first three skills to practice.",
                ),
                "deliverable": "A short skills gap list.",
                "done_when": "You know the top weak areas to study first.",
                "why_it_matters": "Studying weak areas first makes each session more useful.",
                "priority": "high",
                "estimated_hours": 1.0,
            },
            {
                "title": f"Schedule focused {focus} study blocks",
                "goal": f"Create repeatable time blocks for {focus}.",
                "steps": (
                    "Choose realistic study days and session lengths.",
                    "Assign one skill or chapter to each block.",
                    "Add a short review at the end of every session.",
                ),
                "deliverable": "A study block calendar.",
                "done_when": "Each block has a topic and review action.",
                "why_it_matters": "A schedule turns learning into steady progress.",
                "priority": "medium",
                "estimated_hours": 1.0,
            },
        ]

    return [
        {
            "title": f"Clarify the next outcome for {focus}",
            "goal": f"Decide what concrete result should come next for {focus}.",
            "steps": (
                "Write the result you want in one sentence.",
                "List the constraints, resources, and open questions.",
                "Choose the next action that creates visible progress.",
            ),
            "deliverable": "A clear next-outcome note.",
            "done_when": "The next result and first action are written down.",
            "why_it_matters": "Clear outcomes make the work easier to start.",
            "priority": "high",
            "estimated_hours": 1.0,
        },
        {
            "title": f"Break {focus} into action steps",
            "goal": f"Turn {focus} into ordered work you can complete.",
            "steps": (
                "List every action needed for the next outcome.",
                "Put the actions in dependency order.",
                "Estimate the effort for each action.",
            ),
            "deliverable": "An ordered action list.",
            "done_when": "Each action has an order and estimate.",
            "why_it_matters": "Ordered actions reduce guessing and delay.",
            "priority": "medium",
            "estimated_hours": 1.5,
        },
    ]


def _expanded_domain_blueprints(
    *,
    domain: str,
    focus: str,
    task_count: int,
) -> list[dict[str, Any]]:
    blueprints = (
        _fitness_blueprints(focus)
        if domain == "fitness_health"
        else _generic_domain_blueprints(domain, focus)
    )

    while len(blueprints) < task_count:
        index = len(blueprints) + 1
        blueprints.append(
            {
                "title": f"Review {focus} checkpoint {index}",
                "goal": f"Use recent progress to choose the next practical step for {focus}.",
                "steps": (
                    "Review what was completed since the last checkpoint.",
                    "Write what is blocked, unclear, or too difficult.",
                    "Choose one adjustment for the next work session.",
                ),
                "deliverable": f"A checkpoint note for {focus}.",
                "done_when": "The next adjustment is written and ready to follow.",
                "why_it_matters": "Regular checkpoints keep the plan realistic.",
                "priority": "medium",
                "estimated_hours": 0.75,
            }
        )

    return blueprints


def _build_domain_local_tasks(
    *,
    domain: str,
    focus: str,
    task_count: int,
) -> list[dict[str, Any]]:
    blueprints = _expanded_domain_blueprints(
        domain=domain,
        focus=focus,
        task_count=task_count,
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
