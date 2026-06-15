from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.ai_plan_schema import (
    AIPlanPreviewRequest,
    AIPlanPreviewResponse,
    AIPlanPreviewTaskResponse,
)
from app.schemas.task_schema import TaskStatus
from app.services.team_service import get_team_by_id, get_team_membership

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

NOT_ALLOWED = "You are not allowed to perform this action"
TEAM_NOT_FOUND = "Team not found"

router = APIRouter(tags=["AI Plans"])

STOPWORDS = {
    "about",
    "after",
    "and",
    "app",
    "build",
    "create",
    "for",
    "from",
    "have",
    "idea",
    "make",
    "plan",
    "project",
    "that",
    "the",
    "this",
    "want",
    "with",
}

FITNESS_KEYWORDS = {
    "calories",
    "cardio",
    "exercise",
    "fitness",
    "gym",
    "lose weight",
    "muscle",
    "push-up",
    "pushup",
    "run",
    "running",
    "strength",
    "workout",
}
STUDY_KEYWORDS = {"course", "exam", "homework", "learn", "lesson", "study"}
SOFTWARE_KEYWORDS = {"api", "app", "backend", "frontend", "mobile", "software", "website"}
BUSINESS_KEYWORDS = {"business", "campaign", "customer", "marketing", "sales", "shop"}
HABIT_KEYWORDS = {"daily", "habit", "journal", "routine", "sleep", "wake"}


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _contains_any(value: str, keywords: set[str]) -> bool:
    lowered = value.lower()
    return any(keyword in lowered for keyword in keywords)


def _classify_idea(project_idea: str, requirements: str | None) -> str:
    source = f"{project_idea} {requirements or ''}"

    if _contains_any(source, FITNESS_KEYWORDS):
        return "fitness_health"

    if _contains_any(source, STUDY_KEYWORDS):
        return "study_learning"

    if _contains_any(source, SOFTWARE_KEYWORDS):
        return "software_app"

    if _contains_any(source, BUSINESS_KEYWORDS):
        return "business_marketing"

    if _contains_any(source, HABIT_KEYWORDS):
        return "personal_habit"

    return "generic_project"


def _derive_project_title(project_idea: str) -> str:
    title = re.split(r"[\n.!?]", project_idea.strip(), maxsplit=1)[0].strip()
    title = re.sub(r"^\s*i\s+(want|need)\s+to\s+", "", title, flags=re.IGNORECASE)
    title = re.sub(
        r"^\s*(build|create|start|launch|make)\s+",
        "",
        title,
        flags=re.IGNORECASE,
    ).strip()

    if not title:
        return "AI Generated Plan"

    if len(title) > 86:
        title = f"{title[:83].rstrip()}..."

    return title[0].upper() + title[1:]


def _topic_from_idea(project_idea: str, requirements: str | None) -> str:
    source = f"{project_idea} {requirements or ''}"
    words: list[str] = []

    for token in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9'-]{2,}", source.lower()):
        normalized = token.strip("'-_")

        if normalized in STOPWORDS or normalized in words:
            continue

        words.append(normalized)

        if len(words) >= 4:
            break

    return " ".join(words) if words else "the goal"


def _fitness_focus(project_idea: str) -> str:
    lowered = project_idea.lower()

    if "push-up" in lowered or "pushup" in lowered:
        return "pushups"

    if "run" in lowered or "running" in lowered:
        return "running"

    if "lose weight" in lowered:
        return "weight loss"

    if "muscle" in lowered:
        return "muscle building"

    return "fitness"


def _build_due_dates(deadline: datetime, task_count: int) -> list[datetime]:
    now = datetime.now(timezone.utc)
    deadline_utc = _to_utc(deadline)

    if task_count <= 0:
        return []

    if deadline_utc <= now:
        return [deadline_utc for _ in range(task_count)]

    step_seconds = (deadline_utc - now).total_seconds() / (task_count + 1)

    return [now + timedelta(seconds=step_seconds * (index + 1)) for index in range(task_count)]


def _description(
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
    if focus != "pushups":
        focus = "training"

    return [
        {
            "title": "Test your current max pushups",
            "goal": "Find your safe starting point before increasing daily pushup volume.",
            "steps": (
                "Warm up your shoulders, wrists, and chest for 5 minutes.",
                "Do one controlled max-rep set with clean form and stop before form breaks.",
                "Record total reps, effort level, and any discomfort.",
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
                "Keep the first week below failure so soreness stays manageable.",
                "Write the exact daily target and when each set will happen.",
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
    ]


def _generic_blueprints(domain: str, topic: str) -> list[dict[str, Any]]:
    if domain == "software_app":
        return [
            {
                "title": f"Define {topic} core user flow",
                "goal": f"Clarify the main user path for {topic}.",
                "steps": (
                    "Write the primary user action from start to finish.",
                    "List the screens, data, and decisions needed for that path.",
                    "Remove anything that is not needed for the first release.",
                ),
                "deliverable": "A core flow outline.",
                "done_when": "The main user path can be explained in ordered steps.",
                "why_it_matters": "A clear flow prevents scattered development work.",
                "priority": "high",
                "estimated_hours": 2.0,
            },
            {
                "title": f"Prioritize {topic} first-release features",
                "goal": f"Choose the smallest feature set that makes {topic} usable.",
                "steps": (
                    "List must-have, should-have, and later features.",
                    "Mark dependencies between must-have features.",
                    "Pick the first release scope.",
                ),
                "deliverable": "A prioritized feature list.",
                "done_when": "Every first-release feature has a clear reason to exist.",
                "why_it_matters": "Feature priority keeps the software work focused.",
                "priority": "high",
                "estimated_hours": 2.0,
            },
        ]

    return [
        {
            "title": f"Clarify the next outcome for {topic}",
            "goal": f"Decide what concrete result should come next for {topic}.",
            "steps": (
                "Write the result you want in one sentence.",
                "List constraints, resources, and open questions.",
                "Choose the next action that creates visible progress.",
            ),
            "deliverable": "A clear next-outcome note.",
            "done_when": "The next result and first action are written down.",
            "why_it_matters": "Clear outcomes make the work easier to start.",
            "priority": "high",
            "estimated_hours": 1.0,
        },
        {
            "title": f"Break {topic} into action steps",
            "goal": f"Turn {topic} into ordered work you can complete.",
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


def _blueprints_for_domain(domain: str, project_idea: str, topic: str, task_count: int) -> list[dict[str, Any]]:
    blueprints = (
        _fitness_blueprints(_fitness_focus(project_idea))
        if domain == "fitness_health"
        else _generic_blueprints(domain, topic)
    )

    while len(blueprints) < task_count:
        index = len(blueprints) + 1
        blueprints.append(
            {
                "title": f"Review {topic} checkpoint {index}",
                "goal": f"Use recent progress to choose the next practical step for {topic}.",
                "steps": (
                    "Review what was completed since the last checkpoint.",
                    "Write what is blocked, unclear, or too difficult.",
                    "Choose one adjustment for the next work session.",
                ),
                "deliverable": f"A checkpoint note for {topic}.",
                "done_when": "The next adjustment is written and ready to follow.",
                "why_it_matters": "Regular checkpoints keep the plan realistic.",
                "priority": "medium",
                "estimated_hours": 0.75,
            }
        )

    return blueprints


def _build_project_description(preview_data: AIPlanPreviewRequest) -> str:
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


def _build_preview_tasks(
    preview_data: AIPlanPreviewRequest,
    domain: str,
    topic: str,
) -> list[AIPlanPreviewTaskResponse]:
    task_count = max(3, min(12, preview_data.preferred_task_count))
    due_dates = _build_due_dates(preview_data.deadline, task_count)
    blueprints = _blueprints_for_domain(domain, preview_data.project_idea, topic, task_count)
    tasks: list[AIPlanPreviewTaskResponse] = []

    for index, blueprint in enumerate(blueprints[:task_count]):
        tasks.append(
            AIPlanPreviewTaskResponse(
                suggested_order=index + 1,
                title=str(blueprint["title"]),
                description=_description(
                    goal=str(blueprint["goal"]),
                    steps=blueprint["steps"],
                    deliverable=str(blueprint["deliverable"]),
                    done_when=str(blueprint["done_when"]),
                    why_it_matters=str(blueprint["why_it_matters"]),
                ),
                priority=str(blueprint["priority"]),
                estimated_hours=float(blueprint["estimated_hours"]),
                status=TaskStatus.todo.value,
                due_date=due_dates[index] if index < len(due_dates) else None,
                assigned_to=None,
            )
        )

    return tasks


def _build_milestones(domain: str, topic: str, include_milestones: bool) -> list[dict[str, Any]]:
    if not include_milestones:
        return []

    if domain == "fitness_health":
        return [
            {
                "name": "Baseline recorded",
                "description": "The starting pushup level is measured safely.",
                "suggested_order": 1,
            },
            {
                "name": "Routine started",
                "description": "The first week of pushup training is scheduled and tracked.",
                "suggested_order": 2,
            },
            {
                "name": "Progress reviewed",
                "description": "Training volume, form, and recovery are reviewed after 14 days.",
                "suggested_order": 3,
            },
        ]

    return [
        {
            "name": "Direction confirmed",
            "description": f"The next outcome for {topic} is clear.",
            "suggested_order": 1,
        },
        {
            "name": "Execution underway",
            "description": f"The main actions for {topic} are started and tracked.",
            "suggested_order": 2,
        },
        {
            "name": "Progress reviewed",
            "description": f"The current result for {topic} is reviewed and adjusted.",
            "suggested_order": 3,
        },
    ]


def _build_risks(domain: str) -> list[dict[str, str]]:
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
            "risk": "Progress may stall without tracking.",
            "recommendation": "Record the result of each work session before moving on.",
        },
    ]


def _build_recommendations(domain: str) -> list[str]:
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


def _validate_team_preview_access(
    *,
    db: Session,
    preview_data: AIPlanPreviewRequest,
    current_user: User,
) -> None:
    if preview_data.project_type.value != "team":
        return

    if preview_data.team_id is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Team id is required for team project previews",
        )

    team = get_team_by_id(db=db, team_id=preview_data.team_id)

    if team is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=TEAM_NOT_FOUND,
        )

    membership = get_team_membership(
        db=db,
        team_id=preview_data.team_id,
        user_id=current_user.user_id,
    )

    if membership is None:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )


@router.post(
    "/ai-plans/preview-from-idea",
    response_model=AIPlanPreviewResponse,
)
def stable_preview_ai_plan_from_idea(
    preview_data: AIPlanPreviewRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> AIPlanPreviewResponse:
    _validate_team_preview_access(
        db=db,
        preview_data=preview_data,
        current_user=current_user,
    )

    domain = _classify_idea(preview_data.project_idea, preview_data.requirements)
    topic = (
        _fitness_focus(preview_data.project_idea)
        if domain == "fitness_health"
        else _topic_from_idea(preview_data.project_idea, preview_data.requirements)
    )
    project_title = _derive_project_title(preview_data.project_idea)
    tasks = _build_preview_tasks(
        preview_data=preview_data,
        domain=domain,
        topic=topic,
    )

    return AIPlanPreviewResponse(
        success=True,
        message="Generated a structured plan.",
        ai_generation_status="generated",
        source="stable_ai_planner_v2",
        domain=domain,
        project_title=project_title,
        description=_build_project_description(preview_data),
        project_type=preview_data.project_type,
        team_id=preview_data.team_id,
        deadline=preview_data.deadline,
        summary=f"Generated a practical {domain.replace('_', ' ')} plan for {project_title} with {len(tasks)} tasks.",
        tasks=tasks,
        milestones=_build_milestones(domain, topic, preview_data.include_milestones),
        risks=_build_risks(domain),
        recommendations=_build_recommendations(domain),
        project_idea=preview_data.project_idea,
        requirements=preview_data.requirements,
        available_hours_per_week=preview_data.available_hours_per_week,
        preferred_task_count=len(tasks),
        rejected_generic_count=0,
        rejected_unrelated_count=0,
    )
