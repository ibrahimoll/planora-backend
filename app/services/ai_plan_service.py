from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
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
    "Write the first clear version of the idea",
    "Choose the exact first outcome",
    "List the tools and resources needed",
    "Create the smallest useful first version",
    "Test the first result with one real example",
    "Fix the confusing or broken parts",
    "Prepare the version to share",
    "Share it with the first real audience",
    "Collect feedback and choose the next improvement",
    "Track what worked and plan the next step",
]

BUSINESS_TASK_TITLE_TEMPLATES = [
    "Choose the first offer to sell",
    "Define the first target customer",
    "Calculate the cost and selling price",
    "Create the basic brand and sales message",
    "Find the first supplier or production method",
    "Prepare the first small batch or service package",
    "Create the first sales channel",
    "Set up payment, delivery, and order tracking",
    "Make the first launch content",
    "Sell to the first real customers",
    "Collect feedback and improve the offer",
]

SOFTWARE_TASK_TITLE_TEMPLATES = [
    "Choose the first usable version to build",
    "List the main users and user actions",
    "Sketch the main screens and data needed",
    "Create the project setup and folder structure",
    "Build the first working flow",
    "Add the most important feature",
    "Test the main user flow",
    "Fix the first bugs and confusing parts",
    "Prepare the release build",
    "Show it to first users and collect feedback",
]

UNIVERSAL_TASK_PHASES = [
    "Write the first clear version of the idea",
    "Choose the exact first outcome",
    "List the tools and resources needed",
    "Create the smallest useful first version",
    "Test the first result with one real example",
    "Fix the confusing or broken parts",
    "Prepare the version to share",
    "Share it with the first real audience",
    "Collect feedback and choose the next improvement",
    "Track what worked and plan the next step",
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

    explicit_software_build = re.search(
        r"\b(?:build|create|develop|design|make|launch)\s+"
        r"(?:an?\s+)?(?:flutter\s+)?(?:mobile\s+)?"
        r"(?:app|application|game|clicking\s+game|clicker|web\s+app|website|platform|software|backend|frontend|api)\b",
        project_context,
        flags=re.IGNORECASE,
    )

    if explicit_software_build or is_explicit_software:
        return "software"

    if is_business:
        return "business"

    return "general"


def _select_task_title_templates(domain: str) -> list[str]:
    if domain == "business":
        return BUSINESS_TASK_TITLE_TEMPLATES

    if domain == "software":
        return SOFTWARE_TASK_TITLE_TEMPLATES

    return TASK_TITLE_TEMPLATES


def _business_task_description(
    title: str,
) -> str:
    normalized = title.lower()

    if "offer" in normalized or "sell" in normalized:
        return (
            "Choose one simple product or service to sell first so the launch is focused and easy to test."
        )

    if "target customer" in normalized or "audience" in normalized:
        return (
            "Define the exact type of customer you want first, what they need, and why they would choose your offer."
        )

    if "cost" in normalized or "price" in normalized or "pricing" in normalized:
        return (
            "Calculate the cost of one sale and choose a price that covers cost, delivery, and profit."
        )

    if "brand" in normalized or "message" in normalized:
        return (
            "Create a simple name, visual direction, and sales message that explains the offer clearly."
        )

    if "supplier" in normalized or "production" in normalized or "method" in normalized:
        return (
            "Find how you will make or source the offer and compare cost, quality, and delivery time."
        )

    if "batch" in normalized or "package" in normalized or "collection" in normalized:
        return (
            "Prepare a small first version of the product or service so you can test demand before scaling."
        )

    if "sales channel" in normalized or "online" in normalized or "channel" in normalized:
        return (
            "Choose the simplest place customers can see the offer and contact you to order."
        )

    if "delivery" in normalized or "payment" in normalized or "tracking" in normalized:
        return (
            "Set up the basic order process, including payment method, delivery option, and order tracking."
        )

    if "launch content" in normalized or "content" in normalized:
        return (
            "Create the first photos, captions, or messages needed to show the offer and invite people to buy."
        )

    if "first real customers" in normalized or "customers" in normalized:
        return (
            "Reach out to a small group of real people and try to get the first orders or commitments."
        )

    if "feedback" in normalized:
        return (
            "Ask early customers what was clear, what was confusing, and what should be improved first."
        )

    return (
        "Complete this business step by producing one clear output that helps you sell, test, or improve the offer."
    )

def _software_task_description(
    title: str,
) -> str:
    normalized = title.lower()

    if "first usable version" in normalized or "scope" in normalized:
        return (
            "Choose the smallest useful version to build first and remove features that can wait."
        )

    if "users" in normalized or "user actions" in normalized or "requirements" in normalized:
        return (
            "List who will use it and the exact actions they must be able to complete in the first version."
        )

    if "screens" in normalized or "data" in normalized or "architecture" in normalized:
        return (
            "Sketch the main screens, data fields, and flow before writing the full implementation."
        )

    if "setup" in normalized or "folder" in normalized or "roadmap" in normalized:
        return (
            "Create the project setup, organize the files, and prepare the tools needed to start building."
        )

    if "working flow" in normalized or "features" in normalized:
        return (
            "Build the first complete flow that proves the product can work from start to finish."
        )

    if "important feature" in normalized:
        return (
            "Build the one feature that matters most for the first usable version."
        )

    if "test" in normalized or "user flow" in normalized:
        return (
            "Test the main flow like a real user and write down anything broken or confusing."
        )

    if "bugs" in normalized or "confusing" in normalized or "quality" in normalized:
        return (
            "Fix the most obvious bugs and confusing parts before adding more features."
        )

    if "release" in normalized or "documentation" in normalized:
        return (
            "Prepare the build, notes, screenshots, or instructions needed to share the first version."
        )

    if "feedback" in normalized or "first users" in normalized:
        return (
            "Show the first version to real users and collect specific feedback for the next improvement."
        )

    return (
        "Complete this software step with one clear output that can be built, tested, or shown."
    )

def _general_task_description(
    title: str,
) -> str:
    normalized = title.lower()

    if "first clear version" in normalized or "idea" in normalized:
        return (
            "Write the idea in a simple way so you know exactly what you are trying to make or achieve."
        )

    if "first outcome" in normalized or "outcome" in normalized:
        return (
            "Choose the first result you want to finish instead of trying to complete everything at once."
        )

    if "tools" in normalized or "resources" in normalized:
        return (
            "List the tools, materials, information, people, or accounts needed to complete the first version."
        )

    if "smallest useful" in normalized or "first version" in normalized:
        return (
            "Create the smallest version that proves the idea can work."
        )

    if "test" in normalized or "example" in normalized:
        return (
            "Try the first result with one real example and check what works or fails."
        )

    if "fix" in normalized or "broken" in normalized or "confusing" in normalized:
        return (
            "Fix the parts that make the result unclear, incomplete, or hard to use."
        )

    if "share" in normalized or "audience" in normalized:
        return (
            "Prepare and share the result with the first person or group who can react to it."
        )

    if "feedback" in normalized or "improvement" in normalized:
        return (
            "Collect simple feedback and choose the next useful improvement."
        )

    if "track" in normalized or "next step" in normalized:
        return (
            "Write what worked, what did not work, and what you will do next."
        )

    return (
        "Complete this step with one clear output that proves progress."
    )

def _build_task_description_for_domain(
    domain: str,
    title: str,
) -> str:
    if domain == "business":
        return _business_task_description(title)

    if domain == "software":
        return _software_task_description(title)

    return _general_task_description(title)


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

    return [
        {
            "name": "Planning completed",
            "description": "Scope, requirements, and structure are clear.",
            "suggested_order": 1,
        },
        {
            "name": "Core work completed",
            "description": "Main project work is finished.",
            "suggested_order": 2,
        },
        {
            "name": "Final review completed",
            "description": "Testing, cleanup, and final delivery are done.",
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

    return [
        {
            "risk": "Deadline pressure",
            "recommendation": "Start high-priority tasks early and review progress daily.",
        },
        {
            "risk": "Unclear requirements",
            "recommendation": "Confirm project scope before implementation begins.",
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

    return [
        "Review the generated tasks before starting.",
        "Adjust due dates if the project deadline is very close.",
        "Assign team tasks manually after generation.",
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
) -> str:
    deadline_text = _to_utc(project.deadline).date().isoformat()
    description = project.description or "No description provided."

    return f"""
You are Planora AI, an expert project planner.

Your job:
Read the user's project idea carefully and turn it into practical beginner-friendly tasks.
The user may enter any kind of idea: business, app, game, content, learning goal, event, service, product, school project, personal project, or something else.
You must create the right tasks for the exact idea instead of using generic project-management phases.

Main behavior:
- Understand what the user is trying to create, sell, learn, organize, publish, build, or improve.
- Generate tasks that make the user know what to do next.
- The first task must be easy enough to start in 10 minutes.
- Every task must produce something visible, written, chosen, built, tested, shared, sold, or ready to use.
- Do not rely on fixed categories.
- Do not assume the project is software unless the user clearly asks for software, app, website, code, game, backend, frontend, API, or platform.
- Do not assume the project is a business unless the user clearly wants to sell, launch, earn money, attract customers, or operate a service.

Critical output rules:
- Return valid JSON only.
- No Markdown.
- No code fences.
- No text outside JSON.
- Generate exactly {task_count} tasks.
- Task titles must start with an action verb.
- Task titles must be specific to the user's idea.
- Priority must be one of: low, medium, high.
- estimated_hours must be a number between 0.5 and 40.
- suggested_order must start at 1 and increase by 1.

Forbidden task behavior:
- Do not copy the project idea into task descriptions.
- Do not use the same description for multiple tasks.
- Do not write descriptions that only explain the project idea.
- Do not create vague tasks like "Research", "Planning", "Analysis", "Preparation", "Strategy", "Review", or "Improve" unless the title and description say exactly what the user must do.
- Do not use professional project-management language when a beginner would not understand it.
- Do not make tasks that require big money, a full team, legal setup, or advanced tools unless the user asked for that.
- Do not tell the user to do everything at once.

Good title examples:
- Choose the first food item to sell
- Calculate the cost of one order
- Create the first playable scene
- Add basic player movement
- Write the first video script
- Set up the first customer order form
- Build the login screen
- Test the first version with 3 people

Bad title examples:
- Research
- Planning
- Analyze requirements
- Define scope
- Prepare strategy
- Improve quality
- Review project

Every task description must use these exact sections:

Goal:
One simple sentence explaining why this task matters.

Steps:
1. First practical action the user can do immediately.
2. Second practical action.
3. Third practical action.
Add step 4 or 5 only if useful.

Deliverable:
The exact thing the user should have after finishing the task.

Done when:
A clear condition that proves this task is complete.

Idea-specific guidance:
- If the idea is about selling something, include tasks about first offer, audience, price, cost, sales channel, payment, delivery, first customers, and feedback.
- If the idea is about creating a game, include tasks about first simple game idea, engine/tool, playable scene, player action, core mechanic, level/round, win/lose condition, and testing.
- If the idea is about creating an app or website, include tasks about first version, users, screens, data, setup, main flow, testing, and release.
- If the idea is about content, include tasks about audience, topic pillars, first script/post, publishing schedule, feedback, and improvement.
- If the idea is about learning, include tasks about topics, practice exercises, small projects, review, and progress checks.
- If the idea is about an event, include tasks about goal, guests, budget, location, schedule, materials, invitations, and follow-up.
- If the idea does not fit a category, still create practical tasks that help the user start and finish the first useful version.

Project context:
- title: {project.title}
- description: {description}
- project_type: {project.project_type}
- deadline: {deadline_text}

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
      "description": "Goal: Explain why this exact task matters.\\n\\nSteps:\\n1. First practical action.\\n2. Second practical action.\\n3. Third practical action.\\n\\nDeliverable: The exact output the user should have.\\n\\nDone when: How the user knows this task is finished.",
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
        "do not add",
        "$1",
    ]

    return any(fragment in lowered for fragment in bad_fragments)


def _is_actionable_task_description(value: str) -> bool:
    lowered = value.lower()

    required_sections = [
        "goal:",
        "steps:",
        "deliverable:",
        "done when:",
    ]

    has_all_sections = all(section in lowered for section in required_sections)
    numbered_steps = len(re.findall(r"(?:^|\n)\s*\d+\.", value))

    return has_all_sections and numbered_steps >= 3


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

    return cleaned[:500]


def _is_low_quality_task_title(title: str) -> bool:
    normalized = _normalize_comparison_text(title)
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
    }

    return normalized in generic_titles or len(normalized) < 4


def _format_actionable_description(
    title: str,
    base_description: str,
    project_context: str,
) -> str:
    clean_title = title.strip() or "Complete this task"
    clean_base = base_description.strip()

    if (
        not clean_base
        or _is_bad_ai_task_text(clean_base)
        or _description_repeats_project_idea(
            description=clean_base,
            project_context=project_context,
        )
    ):
        clean_base = f"Complete '{clean_title}' with a clear practical result."

    return (
        f"Goal: {clean_base}\n\n"
        "Steps:\n"
        f"1. Focus only on this task: {clean_title}.\n"
        "2. Decide the smallest useful result this task should produce.\n"
        "3. Complete that result without adding extra features or extra work.\n"
        "4. Check that the result is clear, saved, and ready for the next task.\n\n"
        f"Deliverable: A clear finished output for '{clean_title}'.\n\n"
        "Done when: You have something visible, written, chosen, built, tested, or ready to use."
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

    if hours < 0.5:
        return 0.5

    if hours > 40:
        return 40.0

    return round(hours, 2)


def _build_ai_due_dates(project: Project, task_count: int) -> list[str]:
    return [
        due_date.isoformat()
        for due_date in _build_due_dates(project=project, task_count=task_count)
    ]


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

    raw_tasks = raw_tasks[:task_count]

    if len(raw_tasks) < max(3, min(task_count, 3)):
        return None

    due_dates = _build_ai_due_dates(project=project, task_count=len(raw_tasks))
    tasks: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    seen_descriptions: set[str] = set()
    project_context = _extract_user_project_context(
        project=project,
        input_prompt=input_prompt,
    )

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

        if _is_low_quality_task_title(title):
            title = f"Complete project step {index + 1}"

        description_key = _description_key(description)
        needs_description_rewrite = (
            not _is_actionable_task_description(description)
            or _description_repeats_project_idea(
                description=description,
                project_context=project_context,
            )
            or description_key in seen_descriptions
        )

        if needs_description_rewrite:
            description = _format_actionable_description(
                title=title,
                base_description="Complete this task with a clear practical result.",
                project_context=project_context,
            )
            description_key = _description_key(description)

        normalized_title_key = title.lower()

        if normalized_title_key in seen_titles:
            title = f"{title} {index + 1}"
            normalized_title_key = title.lower()

            if needs_description_rewrite:
                description = _format_actionable_description(
                    title=title,
                    base_description="Complete this task with a clear practical result.",
                    project_context=project_context,
                )
                description_key = _description_key(description)

        seen_titles.add(normalized_title_key)
        seen_descriptions.add(description_key)

        tasks.append(
            {
                "suggested_order": index + 1,
                "title": title,
                "description": description,
                "priority": _coerce_ai_priority(
                    raw_task.get("priority"),
                    fallback=_priority_for_index(index=index, task_count=len(raw_tasks)),
                ),
                "estimated_hours": _coerce_ai_estimated_hours(
                    raw_task.get("estimated_hours"),
                    fallback=_estimated_hours_for_index(index),
                ),
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
        "source": "gemini_structured_v2",      
        "domain": domain,
        "summary": summary,
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
) -> dict[str, Any] | None:
    prompt = _build_structured_ai_plan_prompt(
        project=project,
        input_prompt=input_prompt,
        task_count=task_count,
        include_milestones=include_milestones,
    )

    provider_reply = generate_ai_reply_from_provider(prompt)

    if provider_reply is None:
        return None

    parsed = _parse_json_object(provider_reply)

    if parsed is None:
        return None

    return _normalize_ai_plan_response(
        ai_data=parsed,
        project=project,
        input_prompt=input_prompt,
        task_count=task_count,
        include_milestones=include_milestones,
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
    task_title_templates = _select_task_title_templates(domain)

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
                    ),
                    project_context=user_project_context,
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
        "source": "local_dynamic_fallback_v3",
        "domain": domain,
        "summary": (
            f"Generated a structured fallback plan for '{project.title}' with "
            f"{task_count} tasks before the project deadline."
        ),
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
    "source": "local_dynamic_fallback_v3",
    "summary": (
        f"{fallback_summary} AI provider was unavailable or returned invalid JSON, "
        "so Planora used a safe fallback."
    ).strip(),
}


def _parse_due_date(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _create_tasks_from_plan(
    db: Session,
    project: Project,
    current_user: User,
    generated_plan: dict[str, Any],
) -> list[Task]:
    created_tasks: list[Task] = []

    assigned_to = (
        current_user.user_id
        if project.project_type == "personal"
        else None
    )

    for task_data in generated_plan["tasks"]:
        task = Task(
            project_id=project.project_id,
            assigned_to=assigned_to,
            created_by=current_user.user_id,
            title=str(task_data["title"]),
            description=(
                str(task_data["description"])
                if task_data.get("description") is not None
                else None
            ),
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

    return created_tasks


def _delete_existing_project_tasks(
    db: Session,
    project: Project,
) -> int:
    existing_tasks = list(
        db.execute(
            select(Task).where(Task.project_id == project.project_id)
        )
        .scalars()
        .all()
    )

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
    ai_plan, _created_tasks = create_ai_plan_and_tasks_for_project(
        db=db,
        project=project,
        current_user=current_user,
        plan_data=plan_data,
    )

    return ai_plan


def create_ai_plan_and_tasks_for_project(
    db: Session,
    project: Project,
    current_user: User,
    plan_data: AIPlanGenerateRequest,
) -> tuple[AIPlan, list[Task]]:
    input_prompt = (
        plan_data.input_prompt.strip()
        if plan_data.input_prompt
        else f"Generate a project plan for {project.title}."
    )
    project_members = _get_project_members_for_assignment(
        db=db,
        project=project,
    )

    generated_plan = build_generated_plan(
        project=project,
        input_prompt=input_prompt,
        task_count=plan_data.task_count,
        include_milestones=plan_data.include_milestones,
        project_members=project_members,
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

    if plan_data.create_tasks:
        if plan_data.overwrite_existing_tasks:
            overwritten_task_count = _delete_existing_project_tasks(
                db=db,
                project=project,
            )

        created_tasks = _create_tasks_from_plan(
            db=db,
            project=project,
            current_user=current_user,
            generated_plan=generated_plan,
        )

    created_task_ids = [task.task_id for task in created_tasks]

    ai_plan.generated_plan = {
        **generated_plan,
        "created_task_ids": created_task_ids,
        "tasks_created": len(created_task_ids),
        "overwrite_existing_tasks": plan_data.overwrite_existing_tasks,
        "overwritten_task_count": overwritten_task_count,
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
            "created_task_ids": created_task_ids,
            "overwrite_existing_tasks": plan_data.overwrite_existing_tasks,
            "overwritten_task_count": overwritten_task_count,
            "source": str(generated_plan.get("source", "unknown")),
        },
        commit=False,
    )

    db.commit()
    db.refresh(ai_plan)

    for task in created_tasks:
        db.refresh(task)

    return ai_plan, created_tasks


def create_ai_plan_generation_response(
    db: Session,
    project: Project,
    current_user: User,
    plan_data: AIPlanGenerateRequest,
) -> AIPlanGenerateResponse:
    ai_plan, created_tasks = create_ai_plan_and_tasks_for_project(
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
        suggested_order=int(task_data["suggested_order"]),
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

    created_tasks = _create_tasks_from_plan(
        db=db,
        project=project,
        current_user=current_user,
        generated_plan=generated_plan,
    )
    created_task_ids = [task.task_id for task in created_tasks]
    ai_plan.generated_plan = {
        **generated_plan,
        "created_task_ids": created_task_ids,
        "tasks_created": len(created_task_ids),
        "overwrite_existing_tasks": False,
        "overwritten_task_count": 0,
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