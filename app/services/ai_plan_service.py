from __future__ import annotations

import json
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
from app.services.ai_provider_service import generate_ai_reply_from_provider


TASK_TITLE_TEMPLATES = [
    "Write the exact outcome and progress measure",
    "Choose the first realistic checkpoint",
    "Gather the tools and resources needed",
    "Schedule focused work blocks",
    "Complete the first practical action",
    "Track progress for one week",
    "Remove the biggest blocker",
    "Review what worked and adjust",
    "Prepare the next small milestone",
    "Share progress with someone helpful",
    "Finish the most important remaining step",
    "Review results and plan next actions",
]

BUSINESS_TASK_TITLE_TEMPLATES = [
    "Define clothing niche and target customer",
    "Compare 3 local clothing competitors and prices",
    "Estimate low-budget startup costs and pricing",
    "Choose brand name and visual identity",
    "Compare 3 suppliers or production options",
    "Plan the first clothing product collection",
    "Create social media content plan",
    "Set up online sales channel",
    "Plan delivery, payment, and returns",
    "Prepare launch campaign",
    "Prepare inventory and order tracking",
    "Review launch readiness and backup plan",
]

GENERAL_BUSINESS_TASK_TITLE_TEMPLATES = [
    "Define the customer problem and offer",
    "Compare 3 competitors and their prices",
    "Estimate startup costs and simple pricing",
    "Choose the first sales channel",
    "Write the first customer message",
    "Contact 10 potential customers and track replies",
    "Prepare the payment and delivery process",
    "Improve the offer based on customer feedback",
]

CUSTOMER_ACQUISITION_TASK_TITLE_TEMPLATES = [
    "Define the ideal customer and offer",
    "Choose 3 customer acquisition channels",
    "Write a simple outreach message",
    "Contact 10 potential customers and track replies",
    "Track responses and common objections",
    "Improve the offer based on replies",
    "Ask interested leads for the next step",
    "Review the best channel and repeat",
]

SOFTWARE_TASK_TITLE_TEMPLATES = [
    "Define product scope and success criteria",
    "Analyze user requirements and constraints",
    "Design the app architecture and data model",
    "Prepare the implementation roadmap",
    "Build the core product features",
    "Test key user flows",
    "Fix issues and improve quality",
    "Prepare release notes and documentation",
    "Evaluate technical risks and backup plan",
    "Finalize presentation material",
    "Collect feedback and iterate",
    "Submit final version",
]

STUDENT_HOMEWORK_APP_TASK_TITLE_TEMPLATES = [
    "Define student homework app users and success criteria",
    "Map homework subjects, due dates, and reminder needs",
    "Sketch the homework dashboard and task screens",
    "Build the first homework tracking prototype",
    "Test the add-homework and reminder flow",
    "Collect feedback from 3 students",
    "Prepare the student homework app launch checklist",
    "Review feedback and choose the next feature",
]

FITNESS_TASK_TITLE_TEMPLATES = [
    "Set a realistic daily step baseline",
    "Choose walking time blocks",
    "Track steps for 7 days",
    "Increase step count gradually",
    "Prepare recovery and hydration routine",
    "Review weekly progress",
    "Plan a bad-weather walking backup",
    "Add a short mobility warmup",
    "Pick routes that fit your schedule",
    "Celebrate consistency and reset the target",
]

HOME_WORKOUT_TASK_TITLE_TEMPLATES = [
    "Choose a realistic home workout goal",
    "Pick 5 beginner-friendly exercises",
    "Create a weekly home workout schedule",
    "Prepare a safe warmup and cooldown routine",
    "Complete the first 3 workout sessions",
    "Track reps, effort, and recovery",
    "Adjust the routine for the next week",
    "Plan a busy-day backup workout",
]

STUDY_TASK_TITLE_TEMPLATES = [
    "List exam topics and weak areas",
    "Build a weekly study timetable",
    "Create active recall practice cards",
    "Complete one focused practice session",
    "Review mistakes and update notes",
    "Take a timed mini mock test",
    "Schedule spaced revision blocks",
    "Prepare a final review checklist",
]

MARKETING_EXAM_STUDY_TASK_TITLE_TEMPLATES = [
    "List marketing exam topics and weak areas",
    "Create a 7-day marketing study schedule",
    "Make active recall cards for key marketing terms",
    "Complete one focused marketing practice session",
    "Review marketing mistakes and update notes",
    "Take a timed marketing mini mock test",
    "Prepare the final marketing review checklist",
]

EVENT_TASK_TITLE_TEMPLATES = [
    "Define the event goal and guest list",
    "Set the budget and spending limits",
    "Choose the venue or online format",
    "Build the event schedule",
    "Confirm vendors and materials",
    "Send invitations and track replies",
    "Prepare the day-of checklist",
    "Collect feedback after the event",
]

BIRTHDAY_EVENT_TASK_TITLE_TEMPLATES = [
    "Confirm the birthday goal and guest list",
    "Set the birthday budget and spending limits",
    "Choose the venue or home setup",
    "Build the birthday event schedule",
    "Plan food, drinks, music, and activities",
    "Send invitations and track replies",
    "Prepare the day-of birthday checklist",
    "Collect feedback and photos after the event",
]

CONTENT_TASK_TITLE_TEMPLATES = [
    "Define the audience and content promise",
    "Choose content pillars",
    "Plan the first posting schedule",
    "Draft the first three posts or videos",
    "Prepare visuals and captions",
    "Publish and track engagement",
    "Review audience feedback",
    "Adjust the next content batch",
]

GAMING_TIKTOK_TASK_TITLE_TEMPLATES = [
    "Define the gaming TikTok audience and promise",
    "Choose 3 gaming content pillars",
    "Plan the first TikTok posting schedule",
    "Draft 5 short gaming video ideas",
    "Prepare hooks, clips, captions, and hashtags",
    "Publish the first videos and track engagement",
    "Review watch time, comments, and saves",
    "Adjust the next gaming content batch",
]

PRODUCTIVITY_TASK_TITLE_TEMPLATES = [
    "Choose the one measurable habit target",
    "Break the habit into a daily action",
    "Set reminders and friction reducers",
    "Track completion for 7 days",
    "Review missed days without judgment",
    "Adjust the routine to fit real life",
    "Add one accountability check",
    "Plan the next weekly target",
]

UNIVERSAL_TASK_PHASES = [
    "Clarify the exact outcome",
    "Identify who this is for",
    "List the needed resources",
    "Define the first simple version",
    "Create the first working result",
    "Test it with real feedback",
    "Improve the weak points",
    "Prepare the final version",
    "Share or launch it",
    "Track results and next actions",
]

INSTRUCTION_PREFIXES = (
    "create a complete planora project plan",
    "project type:",
    "deadline:",
    "available hours per week:",
    "preferred task count:",
    "create tasks that directly depend",
    "do not default to software",
    "for a clothing business, include",
    "do not suggest extreme physical asset tasks",
    "return a practical plan",
)

BUSINESS_PATTERNS = (
    r"\bbusiness\b",
    r"\bclothing\b",
    r"\bfashion\b",
    r"\bapparel\b",
    r"\bbrand\b",
    r"\bboutique\b",
    r"\bshop\b",
    r"\bstore\b",
    r"\bsell(?:ing)?\b",
    r"\bsupplier(?:s)?\b",
    r"\binventory\b",
    r"\bdelivery\b",
    r"\bpayment(?:s)?\b",
    r"\breturns?\b",
    r"\be-?commerce\b",
    r"\bonline\s+(?:business|store|shop|sales|brand)\b",
    r"\bproduct\s+collection\b",
    r"\bsocial\s+media\b",
    r"\bcustomers?\b",
    r"\bclients?\b",
    r"\bleads?\b",
    r"\bsales?\b",
    r"\brevenue\b",
    r"\bmarketing\b",
    r"\boutreach\b",
    r"\boffer\b",
    r"\bservice(?:s)?\b",
    r"\bbookings?\b",
)

SOFTWARE_PATTERNS = (
    r"\bsoftware\b",
    r"\bmobile\s+app\b",
    r"\bweb\s+app\b",
    r"\bwebsite\b",
    r"\bplatform\b",
    r"\bflutter\b",
    r"\bbackend\b",
    r"\bfrontend\b",
    r"\bapi\b",
    r"\bcode\b",
    r"\bcoding\b",
    r"\bapplication\b",
    r"\bgame\b",
    r"\bclicking\s+game\b",
    r"\bclicker\b",
    r"\b(?:build|create|develop|design|launch|make)\s+"
    r"(?:an?\s+)?(?:mobile\s+)?(?:app|game|website|platform|software)\b",
    r"\bapp\s+(?:for|to)\b",
)

FITNESS_PATTERNS = (
    r"\bfitness\b",
    r"\bhealth\b",
    r"\bhabit\b",
    r"\bdaily\s+goal\b",
    r"\bwalk(?:ing)?\b",
    r"\brun(?:ning)?\b",
    r"\bworkout\b",
    r"\bworking\s+out\b",
    r"\bexercise\b",
    r"\bsteps?\b",
    r"\b10\s?k\s+steps?\b",
    r"\bten\s+thousand\s+steps?\b",
    r"\bhydration\b",
    r"\brecovery\b",
)

STUDY_PATTERNS = (
    r"\bstudy\b",
    r"\blearn(?:ing)?\b",
    r"\bexam\b",
    r"\btest\b",
    r"\bquiz\b",
    r"\bcourse\b",
    r"\bclass\b",
    r"\bhomework\b",
    r"\bpractice\s+questions?\b",
    r"\brevision\b",
)

EVENT_PATTERNS = (
    r"\bevent\b",
    r"\bparty\b",
    r"\bwedding\b",
    r"\bconference\b",
    r"\bworkshop\b",
    r"\bmeetup\b",
    r"\bceremony\b",
    r"\bguests?\b",
    r"\bvenue\b",
)

CONTENT_PATTERNS = (
    r"\bcontent\b",
    r"\bsocial\s+media\b",
    r"\bpost(?:ing)?\b",
    r"\breels?\b",
    r"\bvideos?\b",
    r"\byoutube\b",
    r"\btiktok\b",
    r"\binstagram\b",
    r"\bnewsletter\b",
    r"\bblog\b",
    r"\bpodcast\b",
)

PRODUCTIVITY_PATTERNS = (
    r"\bproductivity\b",
    r"\borganize\b",
    r"\broutine\b",
    r"\bhabits?\b",
    r"\bdeclutter\b",
    r"\btime\s+management\b",
    r"\bfocus\b",
    r"\bpersonal\s+goal\b",
)

GENERIC_TASK_TITLE_PATTERNS = (
    r"\bdefine\s+(?:the\s+)?scope\b",
    r"\bscope\s+and\s+success\s+criteria\b",
    r"\banaly[sz]e\s+requirements\b",
    r"\brequirements\s+and\s+constraints\b",
    r"\bdesign\s+(?:the\s+)?project\s+structure\b",
    r"\bprepare\s+(?:the\s+)?implementation\s+plan\b",
    r"\bcomplete\s+(?:the\s+)?core\s+project\s+work\b",
    r"\bfix\s+issues\s+and\s+improve\s+quality\b",
    r"\bprepare\s+final\s+delivery\b",
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
    "make",
    "map",
    "measure",
    "pick",
    "plan",
    "prepare",
    "publish",
    "remove",
    "review",
    "schedule",
    "send",
    "set",
    "share",
    "sketch",
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
    "customer benefit:",
)


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
                "requirements, features, constraints, and notes:",
                "requirements and constraints:",
            ),
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


def _detect_project_domain(project_context: str) -> str:
    is_business = _matches_any_pattern(project_context, BUSINESS_PATTERNS)
    is_explicit_software = _matches_any_pattern(project_context, SOFTWARE_PATTERNS)
    is_fitness = _matches_any_pattern(project_context, FITNESS_PATTERNS)
    is_study = _matches_any_pattern(project_context, STUDY_PATTERNS)
    is_event = _matches_any_pattern(project_context, EVENT_PATTERNS)
    is_content = _matches_any_pattern(project_context, CONTENT_PATTERNS)
    is_productivity = _matches_any_pattern(project_context, PRODUCTIVITY_PATTERNS)

    explicit_software_build = re.search(
        r"\b(?:build|create|develop|design|make|launch)\s+"
        r"(?:an?\s+)?(?:flutter\s+)?(?:mobile\s+)?"
        r"(?:app|application|game|clicking\s+game|clicker|web\s+app|website|platform|software|backend|frontend|api)\b",
        project_context,
        flags=re.IGNORECASE,
    )

    if explicit_software_build or is_explicit_software:
        return "software"

    if is_fitness:
        return "fitness"

    if is_study:
        return "study"

    if is_event:
        return "event"

    if is_business and (
        _is_clothing_business_context(project_context)
        or _is_customer_acquisition_context(project_context)
        or not is_content
    ):
        return "business"

    if is_content:
        return "content"

    if is_business:
        return "business"

    if is_productivity:
        return "productivity"

    return "general"


def _is_clothing_business_context(project_context: str) -> bool:
    return _matches_any_pattern(
        project_context,
        (
            r"\bclothing\b",
            r"\bfashion\b",
            r"\bapparel\b",
            r"\bbrand\b",
            r"\bboutique\b",
            r"\bshirts?\b",
            r"\bhoodies?\b",
            r"\bdresses?\b",
            r"\bcollection\b",
        ),
    )


def _is_customer_acquisition_context(project_context: str) -> bool:
    return _matches_any_pattern(
        project_context,
        (
            r"\bmore\s+customers?\b",
            r"\bnew\s+customers?\b",
            r"\battract\s+customers?\b",
            r"\bget\s+(?:more\s+)?(?:clients?|leads?|customers?)\b",
            r"\bleads?\b",
            r"\boutreach\b",
            r"\bacquisition\b",
            r"\bsales?\b",
        ),
    )


def _select_task_title_templates(
    domain: str,
    project_context: str = "",
) -> list[str]:
    if domain == "business":
        if _is_customer_acquisition_context(project_context):
            return CUSTOMER_ACQUISITION_TASK_TITLE_TEMPLATES

        if _is_clothing_business_context(project_context):
            return BUSINESS_TASK_TITLE_TEMPLATES

        return GENERAL_BUSINESS_TASK_TITLE_TEMPLATES

    if domain == "software" and _matches_any_pattern(
        project_context,
        (r"\bstudents?\b", r"\bhomework\b", r"\bassignments?\b"),
    ):
        return STUDENT_HOMEWORK_APP_TASK_TITLE_TEMPLATES

    if domain == "study" and _matches_any_pattern(
        project_context,
        (r"\bmarketing\b",),
    ):
        return MARKETING_EXAM_STUDY_TASK_TITLE_TEMPLATES

    if domain == "event" and _matches_any_pattern(
        project_context,
        (r"\bbirthday\b",),
    ):
        return BIRTHDAY_EVENT_TASK_TITLE_TEMPLATES

    if domain == "content" and _matches_any_pattern(
        project_context,
        (r"\btiktok\b.*\bgaming\b", r"\bgaming\b.*\btiktok\b"),
    ):
        return GAMING_TIKTOK_TASK_TITLE_TEMPLATES

    if domain == "fitness" and _matches_any_pattern(
        project_context,
        (r"\bhome\b", r"\bworkout\b", r"\bworking\s+out\b", r"\bexercise\b"),
    ):
        return HOME_WORKOUT_TASK_TITLE_TEMPLATES

    if domain == "software":
        return SOFTWARE_TASK_TITLE_TEMPLATES

    if domain == "fitness":
        return FITNESS_TASK_TITLE_TEMPLATES

    if domain == "study":
        return STUDY_TASK_TITLE_TEMPLATES

    if domain == "event":
        return EVENT_TASK_TITLE_TEMPLATES

    if domain == "content":
        return CONTENT_TASK_TITLE_TEMPLATES

    if domain == "productivity":
        return PRODUCTIVITY_TASK_TITLE_TEMPLATES

    return TASK_TITLE_TEMPLATES


def _business_task_description(
    title: str,
) -> str:
    normalized = title.lower()

    if "ideal customer" in normalized or "customer problem" in normalized or "offer" in normalized:
        return (
            "Clarify who you want to help, what result you can offer, and why "
            "they should care enough to reply."
        )

    if "niche" in normalized or "target customer" in normalized:
        return (
            "Decide what product category you will start with, who your ideal "
            "customer is, your style or value angle, and why people would buy from you."
        )

    if "acquisition channel" in normalized:
        return (
            "Choose a few realistic ways to reach customers before spending time "
            "on channels that do not match the offer."
        )

    if "outreach" in normalized or "message" in normalized:
        return (
            "Create a simple message that explains the offer clearly and makes "
            "it easy for a potential customer to respond."
        )

    if "contact 10" in normalized or "potential customers" in normalized:
        return (
            "Talk to a small measurable number of real prospects so the plan is "
            "based on replies, not guesses."
        )

    if "competitor" in normalized or "market" in normalized:
        return (
            "Review similar businesses, their prices, products, content, customer "
            "comments, and signs of demand."
        )

    if "budget" in normalized or "pricing" in normalized:
        return (
            "List expected costs for samples, stock, packaging, ads, delivery, "
            "platform fees, and target profit margin."
        )

    if "brand name" in normalized or "visual identity" in normalized:
        return (
            "Choose a memorable name and define colors, tone, logo direction, "
            "and the feeling customers should remember."
        )

    if "supplier" in normalized or "production" in normalized or "manufacturing" in normalized:
        return (
            "Compare at least 3 suppliers or production options and note prices, "
            "minimum order quantity, quality, and delivery time."
        )

    if "collection" in normalized:
        return (
            "Choose the first products to launch, possible variants, sample needs, "
            "and a small starting quantity to test demand."
        )

    if "social media" in normalized or "content" in normalized:
        return (
            "Plan posts, product photos, short videos, launch messages, offers, "
            "and how customers will contact or order."
        )

    if "sales channel" in normalized or "online" in normalized:
        return (
            "Choose how customers will buy, such as social DMs, marketplace, "
            "simple online store, payment links, or a website."
        )

    if "delivery" in normalized or "payment" in normalized or "returns" in normalized:
        return (
            "Define payment methods, delivery options, shipping fees, return rules, "
            "and customer confirmation messages."
        )

    if "launch campaign" in normalized:
        return (
            "Create a simple launch plan with first posts, offers, outreach, launch "
            "date, and customer follow-up."
        )

    if "inventory" in normalized or "tracking" in normalized:
        return (
            "Set up a simple tracker for products, quantities, costs, sales, "
            "and reorder alerts."
        )

    return (
        "Turn this business step into a small, measurable action with a clear output, "
        "deadline, and next step."
    )


def _software_task_description(
    title: str,
) -> str:
    normalized = title.lower()

    if "student homework" in normalized or "homework" in normalized:
        return (
            "Turn the homework app idea into a clear first version that helps "
            "students track assignments, due dates, and reminders."
        )

    if "scope" in normalized:
        return (
            "Define target users, core use cases, success metrics, and the first "
            "version's must-have features."
        )

    if "requirements" in normalized:
        return (
            "Write the user stories, constraints, dependencies, and acceptance "
            "criteria needed before implementation."
        )

    if "architecture" in normalized or "data model" in normalized:
        return (
            "Design the technical structure, data entities, integrations, and main "
            "screens or services."
        )

    if "roadmap" in normalized:
        return (
            "Break the build into milestones, estimate the work, and order tasks "
            "around the deadline."
        )

    if "features" in normalized:
        return (
            "Implement the smallest complete set of features that proves the main "
            "product workflow."
        )

    if "test" in normalized:
        return (
            "Test the critical user journeys, edge cases, and expected error states "
            "before release."
        )

    return (
        "Complete this software delivery step with a clear output, owner, and testable "
        "result."
    )


def _fitness_task_description(title: str) -> str:
    normalized = title.lower()

    if "baseline" in normalized:
        return "Check your current step average so the 10k goal starts from a realistic point."

    if "time blocks" in normalized or "routes" in normalized:
        return "Choose walking windows and routes that fit your normal day instead of relying on motivation."

    if "track" in normalized:
        return "Record daily steps long enough to see patterns, easy days, and the times you fall short."

    if "increase" in normalized:
        return "Raise the target gradually so the habit grows without soreness or burnout."

    if "recovery" in normalized or "hydration" in normalized:
        return "Prepare water, shoes, stretching, and recovery habits that make daily walking sustainable."

    return "Turn the health goal into one small, measurable habit action you can repeat this week."


def _study_task_description(title: str) -> str:
    normalized = title.lower()

    if "topics" in normalized or "weak" in normalized:
        return "Map what must be learned and identify the areas that need the most practice."

    if "timetable" in normalized or "revision" in normalized or "schedule" in normalized:
        return "Place study blocks on real calendar times so revision happens before the deadline."

    if "recall" in normalized or "practice" in normalized:
        return "Use active recall and exercises to test understanding instead of rereading passively."

    if "mistakes" in normalized:
        return "Turn wrong answers into a short review list that guides the next session."

    if "mock" in normalized:
        return "Practice under time pressure so the final test feels familiar."

    return "Create a concrete learning output that proves progress on the topic."


def _event_task_description(title: str) -> str:
    normalized = title.lower()

    if "goal" in normalized or "guest" in normalized:
        return "Clarify who the event is for, what should happen, and who needs to attend."

    if "budget" in normalized:
        return "Set spending limits before booking vendors or buying materials."

    if "venue" in normalized or "format" in normalized:
        return "Choose the place or online setup that fits the guest count, budget, and event goal."

    if "schedule" in normalized or "day-of" in normalized:
        return "Create a timeline so setup, activities, and follow-up happen smoothly."

    return "Prepare one visible piece of the event plan so the event becomes easier to run."


def _content_task_description(title: str) -> str:
    normalized = title.lower()

    if "audience" in normalized or "promise" in normalized:
        return "Decide who the content helps and what viewers should expect from your page."

    if "pillars" in normalized:
        return "Choose recurring themes so posts feel consistent and easier to plan."

    if "schedule" in normalized:
        return "Pick realistic publishing times and formats for the first batch."

    if "posts" in normalized or "videos" in normalized:
        return "Draft concrete content pieces that can be published or refined."

    if "engagement" in normalized or "feedback" in normalized:
        return "Review comments, saves, views, and questions to improve the next batch."

    return "Create a specific content asset or publishing decision for the current audience."


def _productivity_task_description(title: str) -> str:
    normalized = title.lower()

    if "target" in normalized:
        return "Choose one measurable behavior so progress is easy to see."

    if "daily action" in normalized:
        return "Make the habit small enough to do on a normal busy day."

    if "reminders" in normalized or "friction" in normalized:
        return "Set up cues and remove obstacles so the habit is easier to start."

    if "track" in normalized:
        return "Record completion for a week to see what helps and what interrupts the routine."

    if "accountability" in normalized:
        return "Add a simple check-in that keeps the goal visible."

    return "Make one practical change to the routine and measure whether it works."


def _general_task_description(
    title: str,
) -> str:
    normalized = title.lower()

    if "scope" in normalized or "requirements" in normalized:
        return (
            "Clarify the expected outcome, constraints, resources, and what success "
            "will look like."
        )

    if "review" in normalized or "test" in normalized:
        return (
            "Check the work against the success criteria, collect feedback, and list "
            "the fixes needed."
        )

    if "final" in normalized or "submit" in normalized:
        return (
            "Prepare the final version, confirm all required pieces are complete, "
            "and package it for delivery."
        )

    return (
        "Complete this step with a specific outcome, short checklist, and deadline."
    )


def _build_task_description_for_domain(
    domain: str,
    title: str,
    project_context: str = "",
) -> str:
    if domain == "business":
        return _business_task_description(title)

    if domain == "software":
        return _software_task_description(title)

    if domain == "fitness":
        return _fitness_task_description(title)

    if domain == "study":
        return _study_task_description(title)

    if domain == "event":
        return _event_task_description(title)

    if domain == "content":
        return _content_task_description(title)

    if domain == "productivity":
        return _productivity_task_description(title)

    return _general_task_description(title)


def _short_context_snippet(project_context: str, max_length: int = 170) -> str:
    cleaned = re.sub(r"\s+", " ", project_context.strip())

    if len(cleaned) <= max_length:
        return cleaned

    return cleaned[: max_length - 3].rstrip() + "..."


def _sentence(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value.strip())

    if not cleaned:
        return "This task turns the idea into one practical result."

    if cleaned[-1] not in ".!?":
        cleaned = f"{cleaned}."

    return cleaned


def _build_contextual_assumption(
    project_context: str,
    domain: str,
) -> str | None:
    if domain == "business" and _is_customer_acquisition_context(project_context):
        if not _matches_any_pattern(
            project_context,
            (
                r"\bproduct\b",
                r"\bservice\b",
                r"\boffer\b",
                r"\bstore\b",
                r"\bshop\b",
                r"\bbrand\b",
            ),
        ):
            return (
                "You already have a basic product or service to offer; "
                "adjust the offer details if you are still choosing one."
            )

    return None


def _build_business_steps(title: str, project_context: str) -> list[str]:
    normalized = title.lower()

    if "ideal customer" in normalized or "target customer" in normalized:
        return [
            "Write the exact customer type, location, budget level, and problem you want to solve.",
            "Describe your offer in one sentence with the result, price range, or main promise.",
            "List 3 reasons this customer would choose you instead of another option.",
        ]

    if "acquisition channel" in normalized or "sales channel" in normalized:
        return [
            "List the channels where your customer already spends time, such as Instagram, referrals, local groups, or search.",
            "Choose 3 channels you can start using this week with little or no cost.",
            "Define one first action and one success number for each channel.",
        ]

    if "outreach" in normalized or "message" in normalized:
        return [
            "Write a short message that names the customer problem and the result you can help with.",
            "Create 2 variations: one friendly direct message and one slightly more formal version.",
            "Save the final message with blanks for the customer name, need, and follow-up date.",
        ]

    if "contact 10" in normalized or "potential customers" in normalized:
        return [
            "Create a list of 10 realistic leads with name, contact method, and why they fit your offer.",
            "Send or prepare the outreach message for each lead without changing the core promise.",
            "Record each reply, no-reply, objection, and next action in one tracker.",
        ]

    if "responses" in normalized or "objections" in normalized:
        return [
            "Create columns for lead name, reply status, objection, interest level, and next step.",
            "Group replies into patterns such as price concern, timing, unclear offer, or not the right customer.",
            "Choose the 2 most common patterns to fix in your offer or message.",
        ]

    if "improve the offer" in normalized:
        return [
            "Review the replies and write what people understood, liked, ignored, or questioned.",
            "Change one part of the offer, such as price, bundle, proof, wording, or call to action.",
            "Send the improved version to 3 new or interested leads and compare the response.",
        ]

    if "competitor" in normalized:
        return [
            "Find 3 realistic competitors in the same area, price range, or audience.",
            "Record their prices, best-selling items or services, strongest posts, and customer comments.",
            "Write one gap you can use, such as faster delivery, lower starting price, better style, or clearer service.",
        ]

    if "budget" in normalized or "pricing" in normalized or "cost" in normalized:
        return [
            "List every expected cost, including samples, tools, packaging, delivery, platform fees, and ads.",
            "Set a low-budget starting limit and mark which costs can wait until demand is proven.",
            "Calculate a simple price range that covers cost and leaves a realistic profit.",
        ]

    if "brand name" in normalized or "visual identity" in normalized:
        return [
            "Shortlist 5 brand names that match the customer, style, and budget position.",
            "Check basic availability on social media and remove confusing or hard-to-spell names.",
            "Choose colors, tone, and a simple logo direction that can work on posts and packaging.",
        ]

    if "supplier" in normalized or "production" in normalized:
        return [
            "List 3 supplier or production options you can contact without committing money yet.",
            "Ask each option for price, minimum quantity, sample cost, delivery time, and quality proof.",
            "Compare the answers in one table and choose the safest first sample option.",
        ]

    if "collection" in normalized:
        return [
            "Choose 3 to 5 first products that match the customer and can be produced on a low budget.",
            "Define size, color, quantity, target price, and sample needs for each product.",
            "Remove items that are expensive, hard to deliver, or not needed for the first demand test.",
        ]

    if "social media" in normalized or "content" in normalized:
        return [
            "Pick the main platform and list the product photos, short videos, and customer questions needed for launch.",
            "Write 5 post ideas with a hook, product angle, and clear order or inquiry action.",
            "Schedule the posts around the launch date and prepare captions before publishing.",
        ]

    if "delivery" in normalized or "payment" in normalized or "returns" in normalized:
        return [
            "Choose payment methods, delivery areas, fees, and expected delivery times.",
            "Write simple return and exchange rules that are fair and easy to explain.",
            "Create the customer confirmation message for order, payment, delivery, and follow-up.",
        ]

    return [
        "Write the concrete decision or output this business task must produce.",
        "Add numbers, names, prices, customer details, or dates so the task is not vague.",
        "Save the result in a document, tracker, checklist, message, or simple plan you can use next.",
    ]


def _build_software_steps(title: str, project_context: str) -> list[str]:
    normalized = title.lower()
    homework_context = _matches_any_pattern(
        project_context,
        (r"\bstudents?\b", r"\bhomework\b", r"\bassignments?\b"),
    )

    if homework_context:
        if "users" in normalized or "success" in normalized or "scope" in normalized:
            return [
                "Write who will use the homework app and what problem it solves during a school week.",
                "Choose the success measure, such as assignments added, overdue work reduced, or reminders used.",
                "Define the smallest first version that helps one student manage one week of homework.",
            ]

        if "subjects" in normalized or "due dates" in normalized or "reminder" in normalized:
            return [
                "List the homework details a student must enter, such as subject, task name, due date, priority, and notes.",
                "Decide when reminders should appear and what the reminder should say.",
                "Separate must-have fields from optional fields so the first version stays simple.",
            ]

        if "dashboard" in normalized or "screens" in normalized:
            return [
                "Sketch the main dashboard with homework due today, upcoming work, and completed work.",
                "Sketch the add-homework screen with only the fields needed for the first version.",
                "Draw how a student moves from dashboard to add, edit, complete, and filter homework.",
            ]

        if "prototype" in normalized:
            return [
                "Build or mock the add-homework flow with subject, due date, priority, and completion status.",
                "Add sample homework items so the dashboard looks realistic.",
                "Save notes for missing features, confusing parts, and what needs to be tested next.",
            ]

        if "test" in normalized or "flow" in normalized:
            return [
                "Add one normal homework item, one urgent item, and one completed item.",
                "Check that the dashboard, due dates, reminder state, and completion status update correctly.",
                "Record every confusing step or broken behavior with the screen name and expected result.",
            ]

        if "feedback" in normalized:
            return [
                "Show the homework flow to 3 students or people who understand student routines.",
                "Ask what feels useful, confusing, missing, or too much for a first version.",
                "Group their feedback into must-fix, later, and ignore for now.",
            ]

    if "requirements" in normalized or "needs" in normalized:
        return [
            "Write 3 to 5 user stories from the user's point of view.",
            "Add acceptance checks for each story so you know when it works.",
            "Mark must-have features separately from nice-to-have ideas that can wait.",
        ]

    if "screen" in normalized or "dashboard" in normalized or "architecture" in normalized:
        return [
            "Sketch the main screens or modules needed for the first usable workflow.",
            "List the data each screen needs to show, save, edit, or delete.",
            "Connect the screens or modules in the order a real user would use them.",
        ]

    if "prototype" in normalized or "build" in normalized or "features" in normalized:
        return [
            "Build or mock the smallest complete workflow that proves the main idea.",
            "Use real-looking sample data so the result can be tested honestly.",
            "Save notes for missing pieces, bugs, and decisions needed before the next build step.",
        ]

    if "test" in normalized:
        return [
            "List the 3 most important user flows that must work before release.",
            "Run each flow with normal data and one edge case.",
            "Record every issue with the expected result, actual result, and fix priority.",
        ]

    return [
        "Define the specific user result this software task must create.",
        "Break the work into screens, data, logic, or test checks that can be completed now.",
        "Create or update the smallest usable version and verify it with sample data.",
    ]


def _build_study_steps(title: str, project_context: str) -> list[str]:
    normalized = title.lower()

    if "topics" in normalized or "weak" in normalized:
        return [
            "List every topic, chapter, slide deck, or question type expected in the exam.",
            "Mark each topic as strong, medium, or weak based on your current confidence.",
            "Choose the 3 weakest topics to study first because they can raise your score fastest.",
        ]

    if "schedule" in normalized or "timetable" in normalized:
        return [
            "Count the days until the exam and block realistic study sessions on your calendar.",
            "Assign weak topics, practice questions, and review sessions to specific time blocks.",
            "Leave one short buffer session for missed work or final review.",
        ]

    if "cards" in normalized or "recall" in normalized:
        return [
            "Turn key definitions, formulas, examples, or frameworks into question-and-answer cards.",
            "Add one example question for each difficult topic.",
            "Review the cards without looking at notes and mark the ones you miss.",
        ]

    if "practice" in normalized or "mock" in normalized:
        return [
            "Choose a small set of realistic questions or past exercises.",
            "Answer them under a timer without checking notes.",
            "Score your answers and write exactly what to review next.",
        ]

    return [
        "Choose the exact study output this task must create.",
        "Practice actively instead of only rereading notes.",
        "Review mistakes and update your next study block from what you missed.",
    ]


def _build_event_steps(title: str, project_context: str) -> list[str]:
    normalized = title.lower()

    if "guest" in normalized or "goal" in normalized:
        return [
            "Write the event purpose, guest count, and the experience you want people to have.",
            "Create the guest list with names, contact method, and invite status.",
            "Mark must-invite people and anyone who needs special timing, seating, or food notes.",
        ]

    if "budget" in normalized:
        return [
            "Set the maximum amount you can spend without stress.",
            "Split the budget across venue, food, cake, decoration, music, transport, and backup costs.",
            "Remove or reduce anything that is nice to have but not needed for the event goal.",
        ]

    if "venue" in normalized or "home setup" in normalized:
        return [
            "Choose the location option that fits the guest count, budget, weather, and setup time.",
            "Check seating, food space, music rules, parking, and cleanup needs.",
            "Confirm the chosen setup with one backup option in case something changes.",
        ]

    if "schedule" in normalized or "day-of" in normalized:
        return [
            "Write the event timeline from setup to guest arrival, activities, food, cake, and cleanup.",
            "Assign each activity a time, owner, and needed material.",
            "Prepare a final checklist you can follow on the event day.",
        ]

    return [
        "Write the exact event decision or material this task must produce.",
        "Add names, times, quantities, vendors, or materials so the plan is usable.",
        "Confirm the result with anyone who depends on it before moving to the next task.",
    ]


def _build_content_steps(title: str, project_context: str) -> list[str]:
    normalized = title.lower()

    if "audience" in normalized or "promise" in normalized:
        return [
            "Describe the viewer you want to attract, including interest level, platform habits, and what they enjoy.",
            "Write the page promise in one sentence so people know why to follow.",
            "Choose one style, such as tips, reactions, rankings, challenges, reviews, or short stories.",
        ]

    if "pillars" in normalized:
        return [
            "Choose 3 repeatable topics that match your audience and are easy to produce.",
            "Write 5 example ideas under each pillar.",
            "Remove ideas that need expensive tools, too much editing, or do not match the page promise.",
        ]

    if "video" in normalized or "post" in normalized or "clips" in normalized:
        return [
            "Write each content idea with a hook, main moment, caption angle, and call to action.",
            "Prepare the clips, screenshots, captions, hashtags, or visuals needed for the first batch.",
            "Check that every piece can be created with your current time, tools, and skill level.",
        ]

    if "publish" in normalized or "engagement" in normalized or "feedback" in normalized:
        return [
            "Publish or schedule the content at realistic times for your audience.",
            "Track views, watch time, comments, saves, shares, and repeated questions.",
            "Choose what to repeat, stop, or change in the next content batch.",
        ]

    return [
        "Choose the exact content output this task must produce.",
        "Add hook, format, topic, caption, and publishing details.",
        "Save the result so it can be published, reviewed, or reused in the next batch.",
    ]


def _build_fitness_steps(title: str, project_context: str) -> list[str]:
    normalized = title.lower()

    if "goal" in normalized or "baseline" in normalized:
        return [
            "Write your current fitness level, available days, space, equipment, and any limits.",
            "Choose one starting goal that can be completed at home this week.",
            "Set a simple progress measure, such as sessions completed, minutes, reps, or step count.",
        ]

    if "exercise" in normalized:
        return [
            "Pick safe beginner exercises that match your space and equipment.",
            "Write sets, reps, rest time, and easier alternatives for each exercise.",
            "Test the routine once at low intensity and remove anything painful or unrealistic.",
        ]

    if "schedule" in normalized:
        return [
            "Choose 3 realistic workout days and times for the coming week.",
            "Assign a short routine to each day with estimated minutes and needed equipment.",
            "Add one rest or recovery day so the plan is easier to keep.",
        ]

    if "warmup" in normalized or "cooldown" in normalized:
        return [
            "Choose 3 warmup moves that prepare the body without tiring you out.",
            "Choose 3 cooldown or stretching moves that help recovery.",
            "Write when to stop or reduce intensity if something feels unsafe.",
        ]

    if "sessions" in normalized:
        return [
            "Complete the planned sessions at a beginner effort level.",
            "Write what exercises you completed, what you skipped, and why.",
            "Mark each session as done only after cooldown and recovery notes are recorded.",
        ]

    if "track" in normalized or "recovery" in normalized:
        return [
            "Record each session date, exercises, reps, effort, and how your body felt afterward.",
            "Note what made the workout easier or harder, such as time of day, sleep, or soreness.",
            "Adjust the next week by adding only one small increase or one helpful recovery change.",
        ]

    if "adjust" in normalized:
        return [
            "Review the first week and mark which exercises felt too easy, too hard, or just right.",
            "Change only one variable, such as reps, sets, rest time, or workout length.",
            "Write the updated routine for the next week before starting it.",
        ]

    return [
        "Choose the smallest fitness action you can repeat this week.",
        "Prepare the space, time, and equipment before the session starts.",
        "Track completion and adjust the next step from real energy and recovery.",
    ]


def _build_productivity_steps(title: str, project_context: str) -> list[str]:
    normalized = title.lower()

    if "target" in normalized or "daily action" in normalized:
        return [
            "Choose one behavior you can measure without guessing.",
            "Make the action small enough to do on a busy day.",
            "Write where, when, and how you will record completion.",
        ]

    if "track" in normalized or "review" in normalized:
        return [
            "Record completion daily for one week without changing the target midway.",
            "Mark missed days and write the real reason they happened.",
            "Choose one adjustment that makes the habit easier next week.",
        ]

    return [
        "Write the exact routine change this task must create.",
        "Set reminders, cues, or friction reducers that make the action easier.",
        "Track the result and use it to choose the next small improvement.",
    ]


def _build_general_steps(title: str, project_context: str) -> list[str]:
    context = _short_context_snippet(project_context, max_length=120)
    context_hint = f" for this idea: {context}" if context else ""

    return [
        f"Write the exact output needed for '{title}'{context_hint}.",
        "List the concrete people, numbers, resources, dates, or decisions needed to complete it.",
        "Create the smallest usable version of the output and save it where you can reuse it.",
        "Check the output against the original goal and remove anything that belongs to a later version.",
    ]


def _build_task_steps(
    domain: str,
    title: str,
    project_context: str,
) -> list[str]:
    if domain == "business":
        return _build_business_steps(title=title, project_context=project_context)

    if domain == "software":
        return _build_software_steps(title=title, project_context=project_context)

    if domain == "study":
        return _build_study_steps(title=title, project_context=project_context)

    if domain == "event":
        return _build_event_steps(title=title, project_context=project_context)

    if domain == "content":
        return _build_content_steps(title=title, project_context=project_context)

    if domain == "fitness":
        return _build_fitness_steps(title=title, project_context=project_context)

    if domain == "productivity":
        return _build_productivity_steps(title=title, project_context=project_context)

    return _build_general_steps(title=title, project_context=project_context)


def _build_task_deliverable(title: str, domain: str) -> str:
    normalized = title.lower()

    if "message" in normalized or "outreach" in normalized:
        return "A ready-to-send outreach message with a clear offer and follow-up note."

    if "contact 10" in normalized or "potential customers" in normalized:
        return "A lead tracker with at least 10 contacts, message status, replies, and next actions."

    if "track" in normalized or "responses" in normalized:
        return "A tracker that shows progress, replies, blockers, and the next decision."

    if "schedule" in normalized or "timetable" in normalized:
        return "A dated schedule with specific sessions, topics, or actions assigned to real time blocks."

    if "prototype" in normalized or "screen" in normalized or "app" in normalized:
        return "A saved prototype, sketch, or working first version that can be tested by a real user."

    if "budget" in normalized or "pricing" in normalized or "cost" in normalized:
        return "A simple budget and price table with totals, limits, and decisions clearly marked."

    if "guest" in normalized:
        return "A guest list with invite status, contact details, and important notes."

    if "content" in normalized or "post" in normalized or "video" in normalized:
        return "A prepared content batch or publishing plan with hooks, formats, captions, and dates."

    if domain == "fitness":
        return "A written workout or habit tracker with sessions, measures, and recovery notes."

    return f"A saved checklist, document, tracker, prototype, or plan for '{title}'."


def _build_task_done_when(title: str) -> str:
    normalized = title.lower()

    if "contact 10" in normalized:
        return "10 potential customers are listed, contacted or ready to contact, and every reply field is tracked."

    if "choose 3" in normalized:
        return "3 options are selected, each with one first action and one measurable success number."

    if "5" in normalized and ("posts" in normalized or "video" in normalized):
        return "5 content ideas are written with hook, format, caption angle, and publishing notes."

    if "3 students" in normalized:
        return "3 students have reviewed the idea or prototype and their feedback is recorded."

    return "The deliverable is saved, includes at least 3 concrete details, and can guide the next task."


def _build_task_customer_benefit(domain: str, title: str) -> str:
    if domain == "business":
        return "This helps turn the idea into customer-facing actions that can create real replies or sales."

    if domain == "software":
        return "This helps the customer build the useful first version instead of getting stuck in vague app ideas."

    if domain == "study":
        return "This makes study progress visible and focuses effort on the exam work that matters most."

    if domain == "event":
        return "This reduces last-minute stress by turning the event idea into confirmed details."

    if domain == "content":
        return "This helps the customer publish consistently and learn what the audience actually wants."

    if domain == "fitness":
        return "This makes the habit realistic enough to start and keep doing at home."

    if domain == "productivity":
        return "This makes progress measurable without making the routine too heavy."

    return "This gives the customer a concrete result that moves the original goal forward."


def _build_milestones(
    domain: str,
    include_milestones: bool,
) -> list[dict[str, Any]]:
    if not include_milestones:
        return []

    if domain == "business":
        return [
            {
                "name": "Business concept validated",
                "description": "Niche, budget, suppliers, and brand direction are clear.",
                "suggested_order": 1,
            },
            {
                "name": "Launch setup completed",
                "description": "Product collection, channels, delivery, and operations are ready.",
                "suggested_order": 2,
            },
            {
                "name": "Go-to-market reviewed",
                "description": "Launch plan, legal checks, and risk backup are finalized.",
                "suggested_order": 3,
            },
        ]

    if domain == "software":
        return [
            {
                "name": "Product scope approved",
                "description": "Users, features, constraints, and success criteria are clear.",
                "suggested_order": 1,
            },
            {
                "name": "Core product built",
                "description": "Main technical workflow is implemented and ready to test.",
                "suggested_order": 2,
            },
            {
                "name": "Release readiness completed",
                "description": "Testing, fixes, documentation, and release notes are done.",
                "suggested_order": 3,
            },
        ]

    if domain == "fitness":
        return [
            {
                "name": "Baseline measured",
                "description": "Current step average and walking windows are clear.",
                "suggested_order": 1,
            },
            {
                "name": "7-day consistency streak",
                "description": "Steps are tracked for one full week with recovery habits in place.",
                "suggested_order": 2,
            },
            {
                "name": "Weekly target reviewed",
                "description": "Progress is reviewed and the next step target is adjusted.",
                "suggested_order": 3,
            },
        ]

    if domain == "study":
        return [
            {
                "name": "Study map completed",
                "description": "Topics, weak areas, and schedule are clear.",
                "suggested_order": 1,
            },
            {
                "name": "Practice loop running",
                "description": "Active recall, exercises, and mistake review are happening.",
                "suggested_order": 2,
            },
            {
                "name": "Exam readiness checked",
                "description": "A timed review or mock test shows what remains to improve.",
                "suggested_order": 3,
            },
        ]

    if domain == "event":
        return [
            {
                "name": "Event plan approved",
                "description": "Goal, guest list, budget, and format are decided.",
                "suggested_order": 1,
            },
            {
                "name": "Logistics confirmed",
                "description": "Schedule, vendors, materials, and invitations are ready.",
                "suggested_order": 2,
            },
            {
                "name": "Day-of checklist ready",
                "description": "The event can run from a clear checklist.",
                "suggested_order": 3,
            },
        ]

    if domain == "content":
        return [
            {
                "name": "Content direction set",
                "description": "Audience, promise, and content pillars are clear.",
                "suggested_order": 1,
            },
            {
                "name": "First batch prepared",
                "description": "Initial posts or videos are drafted with visuals and captions.",
                "suggested_order": 2,
            },
            {
                "name": "Performance reviewed",
                "description": "Engagement and feedback inform the next batch.",
                "suggested_order": 3,
            },
        ]

    if domain == "productivity":
        return [
            {
                "name": "Habit target selected",
                "description": "The routine has one measurable target and daily action.",
                "suggested_order": 1,
            },
            {
                "name": "First week tracked",
                "description": "Completion, missed days, and blockers are visible.",
                "suggested_order": 2,
            },
            {
                "name": "Routine adjusted",
                "description": "The habit is updated to fit real life better.",
                "suggested_order": 3,
            },
        ]

    return [
        {
            "name": "Outcome clarified",
            "description": "The exact target, first checkpoint, and resources are clear.",
            "suggested_order": 1,
        },
        {
            "name": "First progress cycle completed",
            "description": "The first practical action has been completed and tracked.",
            "suggested_order": 2,
        },
        {
            "name": "Next actions reviewed",
            "description": "Results are reviewed and the next milestone is chosen.",
            "suggested_order": 3,
        },
    ]


def _build_risks(domain: str) -> list[dict[str, str]]:
    if domain == "business":
        return [
            {
                "risk": "Supplier or inventory delays",
                "recommendation": "Compare multiple suppliers and order samples before committing.",
            },
            {
                "risk": "Unclear niche or pricing",
                "recommendation": "Validate demand, budget, and pricing before the launch spend.",
            },
        ]

    if domain == "software":
        return [
            {
                "risk": "Scope creep",
                "recommendation": "Keep the first version small and defer nonessential features.",
            },
            {
                "risk": "Technical unknowns",
                "recommendation": "Prototype risky integrations before committing to the full build.",
            },
        ]

    if domain == "fitness":
        return [
            {
                "risk": "Starting too aggressively",
                "recommendation": "Increase steps gradually and include recovery days when needed.",
            },
            {
                "risk": "Schedule interruptions",
                "recommendation": "Prepare short backup walks for busy or bad-weather days.",
            },
        ]

    if domain == "study":
        return [
            {
                "risk": "Passive studying without recall",
                "recommendation": "Use practice questions and explain answers from memory.",
            },
            {
                "risk": "Leaving weak topics too late",
                "recommendation": "Review mistakes after every session and schedule extra practice.",
            },
        ]

    if domain == "event":
        return [
            {
                "risk": "Budget overruns",
                "recommendation": "Set limits before booking and keep a simple spending tracker.",
            },
            {
                "risk": "Missing day-of details",
                "recommendation": "Use one checklist for setup, contacts, materials, and timing.",
            },
        ]

    if domain == "content":
        return [
            {
                "risk": "Inconsistent posting",
                "recommendation": "Prepare a small batch before committing to a schedule.",
            },
            {
                "risk": "Content does not match the audience",
                "recommendation": "Review audience feedback and adjust the next batch.",
            },
        ]

    if domain == "productivity":
        return [
            {
                "risk": "Trying to change too many habits",
                "recommendation": "Keep one target until it feels stable.",
            },
            {
                "risk": "Missing days causes the plan to stop",
                "recommendation": "Use missed days as data and restart with a smaller action.",
            },
        ]

    return [
        {
            "risk": "Deadline pressure",
            "recommendation": "Start high-priority tasks early and review progress daily.",
        },
        {
            "risk": "Target becomes too vague",
            "recommendation": "Keep one measurable checkpoint and review it weekly.",
        },
    ]


def _build_recommendations(domain: str) -> list[str]:
    if domain == "business":
        return [
            "Validate the niche and pricing before buying inventory.",
            "Compare suppliers and order samples before committing.",
            "Keep the launch channel simple until demand is proven.",
        ]

    if domain == "software":
        return [
            "Confirm the first version scope before implementation begins.",
            "Prototype risky technical pieces early.",
            "Test the main user flows before release.",
        ]

    if domain == "fitness":
        return [
            "Start from your real step baseline, not the ideal number.",
            "Use short walks when the day is busy.",
            "Review consistency weekly before raising the target.",
        ]

    if domain == "study":
        return [
            "Practice recall before rereading notes.",
            "Review mistakes after each session.",
            "Use timed practice before the final deadline.",
        ]

    if domain == "event":
        return [
            "Confirm budget, people, and location before buying materials.",
            "Keep one day-of checklist.",
            "Track replies and vendor confirmations in one place.",
        ]

    if domain == "content":
        return [
            "Prepare a small content batch before publishing.",
            "Track which topics earn useful engagement.",
            "Adjust the next batch from real audience feedback.",
        ]

    if domain == "productivity":
        return [
            "Keep the first habit action small enough for busy days.",
            "Track one week before changing the routine.",
            "Restart with a smaller target after missed days.",
        ]

    return [
        "Start with the first measurable checkpoint.",
        "Track progress for one week before making the plan larger.",
        "Adjust tasks based on what worked in real life.",
    ]


def _strip_json_code_fence(value: str) -> str:
    cleaned = value.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").strip()

    elif cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").strip()

    if cleaned.endswith("```"):
        cleaned = cleaned.removesuffix("```").strip()

    return cleaned


def _parse_json_object(value: str) -> dict[str, Any] | None:
    cleaned = _strip_json_code_fence(value)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")

        if first_brace == -1 or last_brace == -1 or last_brace <= first_brace:
            return None

        try:
            data = json.loads(cleaned[first_brace : last_brace + 1])
        except json.JSONDecodeError:
            return None

    return data if isinstance(data, dict) else None


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

Do not rely on fixed categories.
Do not assume the project is software unless the user clearly asks for software, app, website, code, game, backend, frontend, or platform.
Do not assume the project is a business unless the user clearly wants to sell, launch, earn money, attract customers, or operate a service.
Handle any practical idea type, including business ideas, software/app ideas, study plans, personal productivity, events, content creation, fitness or habit goals, services, small local businesses, vague customer goals, spelling mistakes, and missing details.

Critical output rules:
- Return valid JSON only.
- No Markdown.
- No code fences.
- No text outside JSON.
- Generate exactly {task_count} tasks.
- Task titles must start with an action verb.
- Task titles must be specific to the user's idea.
- Avoid vague titles like "Research", "Plan project", "Improve business", "Work on app", "Create content", "Start marketing", or "Finish project".
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

Customer benefit:
Explain in one short sentence how the task helps the customer reach the original goal.

Important:
- The task must teach the user what to do.
- The task must not be only a reminder.
- The task must not be generic.
- The task must be understandable by a beginner.
- The task must move the project forward.
- The task must produce a visible result, such as a checklist, tracker, schedule, message, prototype, budget, content batch, customer list, or completed practice set.
- If information is missing, make a safe assumption and include a short "Assumption:" line only inside the relevant task description.
- If the idea is about selling something, include tasks about offer, audience, pricing, cost, sales, and delivery.
- If the idea is about creating something, include tasks about requirements, materials/tools, first version, testing, feedback, and final delivery.
- If the idea is about learning, include tasks about topics, practice, review, exercises, and progress checks.
- If the idea is about an event, include tasks about goal, people, budget, location, schedule, materials, and follow-up.
- If the idea is about content, include tasks about audience, content pillars, first posts/videos, publishing schedule, and feedback.
- If the idea is "I want more customers" or similarly vague, generate a first achievable customer acquisition plan: define the ideal customer and offer, choose 3 channels, write outreach, contact a small measurable number of leads, track responses, and improve the offer from replies.

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

User idea and requirements:
{input_prompt.strip()}

Return JSON in exactly this shape:
{{
  "domain": "short natural label inferred from the user idea",
  "summary": "short summary of the generated plan",
  "tasks": [
    {{
      "suggested_order": 1,
      "title": "specific action-based task title",
      "description": "Goal: One sentence explaining why this exact task matters.\\n\\nSteps:\\n1. First practical action.\\n2. Second practical action.\\n3. Third practical action.\\n\\nDeliverable: The exact output the user should have.\\n\\nDone when: A measurable completion condition.\\n\\nCustomer benefit: One short sentence explaining how this helps the original goal.",
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
        next_labels=("Done when:", "Customer benefit:"),
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
        "message",
        "plan",
        "post",
        "practice",
        "price",
        "prototype",
        "schedule",
        "screen",
        "table",
        "tracker",
        "video",
    )

    return any(term in normalized for term in visible_terms)


def _is_actionable_task_description(value: str) -> bool:
    lowered = value.lower()

    has_all_sections = all(section in lowered for section in SMART_DESCRIPTION_SECTIONS)
    numbered_steps = len(re.findall(r"(?:^|\n)\s*\d+\.", value))

    return (
        has_all_sections
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
            r"^(idea|project idea|project idea and goal|requirements|requirements and constraints|requirements, features, constraints, and notes)\s*:\s*",
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
        "improve business",
        "work on app",
        "create content",
        "start marketing",
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


def _is_disallowed_generic_task_title(title: str, domain: str) -> bool:
    normalized = _normalize_comparison_text(title)

    if domain == "software":
        allowed_software_fragments = (
            "define product scope",
            "analyze user requirements",
            "design the app architecture",
            "design app architecture",
        )

        if any(fragment in normalized for fragment in allowed_software_fragments):
            return False

    return _matches_any_pattern(normalized, GENERIC_TASK_TITLE_PATTERNS)


def _has_similar_seen_title(title: str, seen_titles: set[str]) -> bool:
    return any(_task_titles_are_similar(title, seen_title) for seen_title in seen_titles)


def _fallback_task_title_for_index(
    domain: str,
    project_context: str,
    index: int,
) -> str:
    templates = _select_task_title_templates(
        domain=domain,
        project_context=project_context,
    )

    return templates[index % len(templates)]


def _format_actionable_description(
    title: str,
    base_description: str,
    project_context: str,
    domain: str = "general",
    assumption: str | None = None,
) -> str:
    clean_title = title.strip() or "Complete this task"
    clean_base = _sentence(
        base_description
        or f"Complete '{clean_title}' with one clear practical result"
    )
    steps = _build_task_steps(
        domain=domain,
        title=clean_title,
        project_context=project_context,
    )[:5]
    assumption_text = f"\n\nAssumption: {assumption}" if assumption else ""
    numbered_steps = "\n".join(
        f"{index}. {_sentence(step)}"
        for index, step in enumerate(steps, start=1)
    )

    return (
        f"Goal: {clean_base}"
        f"{assumption_text}\n\n"
        "Steps:\n"
        f"{numbered_steps}\n\n"
        f"Deliverable: {_build_task_deliverable(clean_title, domain)}\n\n"
        f"Done when: {_build_task_done_when(clean_title)}\n\n"
        f"Customer benefit: {_build_task_customer_benefit(domain, clean_title)}"
    )


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


def _build_task_description_repair_prompt(
    project: Project,
    input_prompt: str,
    tasks: list[dict[str, Any]],
) -> str:
    project_context = _extract_user_project_context(
        project=project,
        input_prompt=input_prompt,
    )
    task_payload = [
        {
            "suggested_order": task.get("suggested_order"),
            "title": task.get("title"),
            "current_description": task.get("description"),
        }
        for task in tasks
    ]

    return f"""
You are Planora AI.

The previous task descriptions were too generic.
Rewrite only the task descriptions so every task is specific to the user's exact project idea.

Project idea and requirements:
{project_context}

Tasks to repair:
{json.dumps(task_payload, ensure_ascii=False, indent=2)}

Rules:
- Keep the same suggested_order values.
- Keep the same titles.
- Rewrite every description to be project-specific.
- Do not repeat the same steps for every task.
- Do not copy the project idea as the description.
- Use simple beginner-friendly language.
- Each task must produce something visible, written, built, tested, chosen, shared, sold, or ready to use.
- Make the steps concrete for this exact idea. For example, if the idea is a homework app, mention homework fields, subjects, due dates, reminders, dashboard, filters, or completed status where relevant.

Every description must use this exact structure:

Goal: One simple sentence explaining why this exact task matters.

Steps:
1. First practical project-specific action.
2. Second practical project-specific action.
3. Third practical project-specific action.
4. Optional fourth project-specific action when useful.

Deliverable: The exact output the user should have after finishing this task.

Done when: A clear condition that proves this task is complete.

Customer benefit: One short sentence explaining how this task helps the original goal.

Return valid JSON only in this exact shape:
{{
  "tasks": [
    {{
      "suggested_order": 1,
      "title": "same title",
      "description": "Goal: ...\n\nSteps:\n1. ...\n2. ...\n3. ...\n\nDeliverable: ...\n\nDone when: ...\n\nCustomer benefit: ..."
    }}
  ]
}}
""".strip()


def _generated_plan_has_generic_descriptions(generated_plan: dict[str, Any]) -> bool:
    tasks = generated_plan.get("tasks")

    if not isinstance(tasks, list):
        return False

    return any(
        isinstance(task, dict)
        and (
            _description_is_too_generic(str(task.get("description") or ""))
            or not _is_actionable_task_description(str(task.get("description") or ""))
        )
        for task in tasks
    )


def _repair_generic_task_descriptions(
    generated_plan: dict[str, Any],
    project: Project,
    input_prompt: str,
) -> dict[str, Any]:
    if not _generated_plan_has_generic_descriptions(generated_plan):
        return generated_plan

    tasks = generated_plan.get("tasks")

    if not isinstance(tasks, list) or not tasks:
        return generated_plan

    prompt = _build_task_description_repair_prompt(
        project=project,
        input_prompt=input_prompt,
        tasks=tasks,
    )
    provider_reply = generate_ai_reply_from_provider(prompt)

    if provider_reply is None:
        return generated_plan

    parsed = _parse_json_object(provider_reply)

    if parsed is None or not isinstance(parsed.get("tasks"), list):
        return generated_plan

    project_context = _extract_user_project_context(
        project=project,
        input_prompt=input_prompt,
    )
    repaired_by_order: dict[int, str] = {}

    for raw_task in parsed["tasks"]:
        if not isinstance(raw_task, dict):
            continue

        suggested_order_value = raw_task.get("suggested_order")

        if suggested_order_value is None:
            continue

        try:
            suggested_order = int(str(suggested_order_value))
        except (TypeError, ValueError):
            continue

        description = _clean_ai_text_field(
            raw_task.get("description"),
            fallback="",
            max_length=2200,
            preserve_newlines=True,
        )

        if not description:
            continue

        if not _is_actionable_task_description(description):
            continue

        if _description_repeats_project_idea(description, project_context):
            continue

        if _description_is_too_generic(description):
            continue

        repaired_by_order[suggested_order] = description

    if not repaired_by_order:
        return generated_plan

    repaired_tasks: list[dict[str, Any]] = []

    for task in tasks:
        if not isinstance(task, dict):
            repaired_tasks.append(task)
            continue

        suggested_order_value = task.get("suggested_order")
        fallback_order = len(repaired_tasks) + 1

        try:
            suggested_order = (
                int(str(suggested_order_value))
                if suggested_order_value is not None
                else fallback_order
            )
        except (TypeError, ValueError):
            suggested_order = fallback_order

        repaired_description = repaired_by_order.get(suggested_order)

        if repaired_description is None:
            repaired_tasks.append(task)
            continue

        repaired_tasks.append(
            {
                **task,
                "description": repaired_description,
            }
        )

    source = str(generated_plan.get("source", "gemini_structured_v2"))

    return {
        **generated_plan,
        "source": f"{source}_description_repaired",
        "tasks": repaired_tasks,
        "description_repair_applied": True,
    }


def _normalize_ai_plan_response(
    ai_data: dict[str, Any],
    project: Project,
    input_prompt: str,
    task_count: int,
    include_milestones: bool,
) -> dict[str, Any] | None:
    raw_tasks = ai_data.get("tasks")

    if not isinstance(raw_tasks, list):
        return None

    if len(raw_tasks) != task_count:
        return None

    due_dates = _build_ai_due_dates(project=project, task_count=task_count)
    tasks: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    seen_descriptions: set[str] = set()
    rejected_generic_count = 0
    project_context = _extract_user_project_context(
        project=project,
        input_prompt=input_prompt,
    )
    detected_domain = _detect_project_domain(project_context)

    for index, raw_task in enumerate(raw_tasks):
        if not isinstance(raw_task, dict):
            return None

        title = _clean_ai_text_field(
            raw_task.get("title"),
            fallback=f"Complete project step {index + 1}",
            max_length=120,
        )
        description = _clean_ai_text_field(
            raw_task.get("description"),
            fallback=(
                "Goal: Complete this step with a clear practical result.\n\n"
                "Steps:\n"
                "1. Understand what this task requires.\n"
                "2. Complete the smallest useful version.\n"
                "3. Review the result before moving forward.\n\n"
                "Deliverable: A finished result for this task.\n\n"
                "Done when: The result is clear, saved, and useful for the next task."
            ),
            max_length=2200,
            preserve_newlines=True,
        )

        if _is_bad_ai_task_text(title) or _is_bad_ai_task_text(description):
            return None

        if _is_disallowed_generic_task_title(title, detected_domain):
            return None

        if _is_low_quality_task_title(title):
            title = _fallback_task_title_for_index(
                domain=detected_domain,
                project_context=project_context,
                index=index,
            )
            rejected_generic_count += 1

        description_key = _description_key(description)
        needs_description_rewrite = (
            not _is_actionable_task_description(description)
            or _description_repeats_project_idea(
                description=description,
                project_context=project_context,
            )
            or _description_is_too_generic(description)
            or description_key in seen_descriptions
        )

        if needs_description_rewrite:
            fallback_domain = _detect_project_domain(project_context)
            description = _format_actionable_description(
                title=title,
                base_description=_build_task_description_for_domain(
                    domain=fallback_domain,
                    title=title,
                    project_context=project_context,
                ),
                project_context=project_context,
                domain=fallback_domain,
                assumption=_build_contextual_assumption(
                    project_context=project_context,
                    domain=fallback_domain,
                )
                if index == 0
                else None,
            )
            description_key = _description_key(description)
            rejected_generic_count += 1

        if description_key in seen_descriptions:
            return None

        normalized_title_key = title.lower()

        if (
            normalized_title_key in seen_titles
            or _has_similar_seen_title(title, seen_titles)
        ):
            return None

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
                "due_date": due_dates[index],
                "assigned_to": raw_task.get("assigned_to"),
            }
        )

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

    if not recommendations:
        recommendations = [
            "Review the generated tasks before accepting the plan.",
            "Regenerate if the tasks do not match your idea.",
            "Edit unclear tasks before saving the project.",
        ]

    if not risks:
        risks = [
            {
                "risk": "Unclear scope",
                "recommendation": "Review the generated tasks and edit anything that does not match your idea.",
            }
        ]

    return {
        "source": "gemini_structured_v3",
        "domain": domain,
        "summary": summary,
        "rejected_generic_count": rejected_generic_count,
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
) -> dict[str, Any] | None:
    prompt = _build_structured_ai_plan_prompt(
        project=project,
        input_prompt=input_prompt,
        task_count=task_count,
        include_milestones=include_milestones,
        existing_tasks=existing_tasks,
        overwrite_existing_tasks=overwrite_existing_tasks,
    )

    provider_reply = generate_ai_reply_from_provider(prompt)

    if provider_reply is None:
        return None

    parsed = _parse_json_object(provider_reply)

    if parsed is None:
        return None

    normalized_plan = _normalize_ai_plan_response(
        ai_data=parsed,
        project=project,
        input_prompt=input_prompt,
        task_count=task_count,
        include_milestones=include_milestones,
    )

    if normalized_plan is None:
        return None

    return _repair_generic_task_descriptions(
        generated_plan=normalized_plan,
        project=project,
        input_prompt=input_prompt,
    )


def _build_local_generated_plan(
    project: Project,
    input_prompt: str,
    task_count: int,
    include_milestones: bool = True,
    project_members: list[ProjectMember] | None = None,
) -> dict[str, Any]:
    due_dates = _build_due_dates(
        project=project,
        task_count=task_count,
    )

    project_context = (
        input_prompt.strip()
        or project.description
        or f"Create a structured project plan for {project.title}."
    )
    user_project_context = _extract_user_project_context(
        project=project,
        input_prompt=project_context,
    )
    domain = _detect_project_domain(user_project_context)
    task_title_templates = _select_task_title_templates(
        domain=domain,
        project_context=user_project_context,
    )

    tasks: list[dict[str, Any]] = []
    assignable_member_ids = [
        member.user_id
        for member in (project_members or [])
        if member.user_id is not None
    ]

    for index in range(task_count):
        title_template = task_title_templates[index % len(task_title_templates)]
        suffix = f" {index + 1}" if index >= len(task_title_templates) else ""
        assigned_to = (
            assignable_member_ids[index % len(assignable_member_ids)]
            if project.project_type == "team" and assignable_member_ids
            else None
        )

        tasks.append(
            {
                "suggested_order": index + 1,
                "title": f"{title_template}{suffix}",
                "description": _format_actionable_description(
                    title=title_template,
                    base_description=_build_task_description_for_domain(
                        domain=domain,
                        title=title_template,
                        project_context=user_project_context,
                    ),
                    project_context=user_project_context,
                    domain=domain,
                    assumption=_build_contextual_assumption(
                        project_context=user_project_context,
                        domain=domain,
                    )
                    if index == 0
                    else None,
                ),
                "priority": _priority_for_index(
                    index=index,
                    task_count=task_count,
                ),
                "estimated_hours": _estimated_hours_for_index(index),
                "due_date": due_dates[index].isoformat(),
                "assigned_to": assigned_to,
            }
        )

    return {
        "source": "local_dynamic_fallback_v5",
        "domain": domain,
        "summary": (
            f"Generated a structured fallback plan for '{project.title}' with "
            f"{task_count} tasks before the project deadline."
        ),
        "rejected_generic_count": 0,
        "project": {
            "project_id": project.project_id,
            "title": project.title,
            "project_type": project.project_type,
            "deadline": _to_utc(project.deadline).isoformat(),
        },
        "tasks": tasks,
        "milestones": _build_milestones(
            domain=domain,
            include_milestones=include_milestones,
        ),
        "risks": _build_risks(domain),
        "recommendations": _build_recommendations(domain),
    }


def build_generated_plan(
    project: Project,
    input_prompt: str,
    task_count: int,
    include_milestones: bool = True,
    project_members: list[ProjectMember] | None = None,
    existing_tasks: list[Task] | None = None,
    overwrite_existing_tasks: bool = False,
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
    )

    if ai_generated_plan is not None:
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

    fallback_plan = _build_local_generated_plan(
        project=project,
        input_prompt=input_prompt,
        task_count=task_count,
        include_milestones=include_milestones,
        project_members=project_members,
    )

    fallback_summary = str(fallback_plan.get("summary", "")).strip()

    return {
    **fallback_plan,
    "source": "local_dynamic_fallback_v5",
    "summary": (
        f"{fallback_summary} AI provider was unavailable or returned invalid JSON, "
        "so Planora used a safe fallback."
    ).strip(),
}


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
        summary=str(ai_plan.generated_plan.get("summary", "")),
        tasks_created=len(created_tasks),
        tasks_skipped_as_duplicates=skipped_duplicate_count,
        improvement_summary=str(ai_plan.generated_plan.get("improvement_summary", "")),
        rejected_generic_count=int(
            ai_plan.generated_plan.get("rejected_generic_count") or 0
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
        pieces.append(f"Requirements and constraints: {requirements}")

    return "\n".join(pieces)


def _build_preview_prompt(
    preview_data: AIPlanPreviewRequest,
) -> str:
    pieces = [
        f"Project idea and goal:\n{preview_data.project_idea.strip()}",
    ]

    requirements = (preview_data.requirements or "").strip()

    if requirements:
        pieces.append(f"Requirements, features, constraints, and notes:\n{requirements}")

    return "\n\n".join(pieces)


def _preview_task_response_from_plan_task(
    task_data: dict[str, Any],
) -> AIPlanPreviewTaskResponse:
    return AIPlanPreviewTaskResponse(
        suggested_order=int(str(task_data.get("suggested_order") or 1)),        title=str(task_data["title"]),
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
    )

    return AIPlanPreviewResponse(
        source=str(generated_plan["source"]),
        domain=str(generated_plan["domain"]),
        project_title=project.title,
        description=project.description,
        project_type=preview_data.project_type,
        team_id=preview_data.team_id,
        deadline=preview_data.deadline,
        summary=str(generated_plan["summary"]),
        tasks=[
            _preview_task_response_from_plan_task(task)
            for task in generated_plan["tasks"]
        ],
        milestones=list(generated_plan["milestones"]),
        risks=list(generated_plan["risks"]),
        recommendations=list(generated_plan["recommendations"]),
        project_idea=preview_data.project_idea,
        requirements=preview_data.requirements,
        available_hours_per_week=preview_data.available_hours_per_week,
        preferred_task_count=preview_data.preferred_task_count,
    )


def _generated_plan_from_preview(
    project: Project,
    preview: AIPlanPreviewResponse,
) -> dict[str, Any]:
    return {
        "source": preview.source,
        "domain": preview.domain,
        "summary": preview.summary,
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
        summary=str(ai_plan.generated_plan.get("summary", "")),
        tasks_created=len(created_tasks),
        tasks_skipped_as_duplicates=skipped_duplicate_count,
        improvement_summary=str(ai_plan.generated_plan.get("improvement_summary", "")),
        rejected_generic_count=int(
            ai_plan.generated_plan.get("rejected_generic_count") or 0
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
