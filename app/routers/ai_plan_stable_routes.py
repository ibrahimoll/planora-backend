from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Annotated

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

TASK_BLUEPRINTS = [
    {
        "title": "Define {topic} success criteria",
        "goal": "Set the exact first-version outcome for {topic} so the project has a clear finish line.",
        "steps": (
            "Write the main result the user should get from {topic}.",
            "List the must-have features or actions that prove the idea works.",
            "Choose 3 measurable checks that decide if the first version is successful.",
        ),
        "deliverable": "A success criteria document for {topic}.",
        "done_when": "The document has one goal, 3 success checks, and a clear first-version scope.",
        "benefit": "The user knows exactly what must be delivered first.",
        "priority": "high",
        "estimated_hours": 1.5,
    },
    {
        "title": "Map {topic} requirements",
        "goal": "Turn the idea into practical requirements before building or executing anything.",
        "steps": (
            "Separate must-have requirements, optional improvements, and constraints.",
            "Mark each requirement as simple, medium, or complex.",
            "Remove anything that does not support the first useful version.",
        ),
        "deliverable": "A prioritized requirements checklist for {topic}.",
        "done_when": "Every requirement has a priority and the first version has no unclear items.",
        "benefit": "The user can start with the highest-value work instead of guessing.",
        "priority": "high",
        "estimated_hours": 2.0,
    },
    {
        "title": "Create {topic} execution plan",
        "goal": "Break {topic} into ordered work that can be followed step by step.",
        "steps": (
            "Group the requirements into setup, build, test, and release work.",
            "Put the groups in dependency order so each step supports the next one.",
            "Estimate the time needed for each work group.",
        ),
        "deliverable": "A step-by-step execution plan for {topic}.",
        "done_when": "The plan shows what starts first, what depends on it, and what finishes the project.",
        "benefit": "The user can begin execution without confusion.",
        "priority": "medium",
        "estimated_hours": 2.5,
    },
    {
        "title": "Build {topic} first version",
        "goal": "Create a small usable version of {topic} that proves the core idea works.",
        "steps": (
            "Choose only the minimum features needed for a working first version.",
            "Build, draft, or prepare those features without adding polish yet.",
            "Write down anything blocked, missing, or unclear while building.",
        ),
        "deliverable": "A working first version or prototype plan for {topic}.",
        "done_when": "The core flow can be shown, tested, or explained from start to finish.",
        "benefit": "The user gets a real result instead of staying in planning mode.",
        "priority": "medium",
        "estimated_hours": 5.0,
    },
    {
        "title": "Test {topic} core flow",
        "goal": "Find problems in {topic} before relying on it or presenting it.",
        "steps": (
            "Run through the main flow from the first action to the final result.",
            "Write every bug, missing detail, confusing step, or weak point in a tracker.",
            "Choose the fixes that block the first useful version.",
        ),
        "deliverable": "A test results tracker for {topic}.",
        "done_when": "The tracker lists tested steps, found issues, and required fixes before release.",
        "benefit": "The user improves reliability before anyone depends on the result.",
        "priority": "medium",
        "estimated_hours": 3.0,
    },
    {
        "title": "Prepare {topic} release checklist",
        "goal": "Confirm that {topic} is ready to share, submit, launch, or continue safely.",
        "steps": (
            "List final checks for content, functionality, quality, and presentation.",
            "Confirm that all high-priority issues are finished or documented.",
            "Write the next action after release, such as feedback collection or improvement work.",
        ),
        "deliverable": "A final release checklist and next-step plan for {topic}.",
        "done_when": "The checklist is complete and there is a clear decision to release, submit, or improve.",
        "benefit": "The user finishes with fewer last-minute surprises.",
        "priority": "high",
        "estimated_hours": 2.0,
    },
    {
        "title": "Collect {topic} feedback",
        "goal": "Use real feedback to improve {topic} instead of guessing what matters.",
        "steps": (
            "Choose 2 or 3 people who match the expected user, customer, or reviewer.",
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
        "goal": "Fix the parts of {topic} that most affect usefulness, reliability, or quality.",
        "steps": (
            "Pick the highest-impact issues from testing and feedback.",
            "Fix one issue at a time and record what changed.",
            "Retest the changed parts to confirm each fix worked.",
        ),
        "deliverable": "An improvement log for {topic}.",
        "done_when": "The most important weak points are fixed and retested.",
        "benefit": "The user gets a cleaner and more dependable final result.",
        "priority": "medium",
        "estimated_hours": 4.0,
    },
    {
        "title": "Write {topic} documentation",
        "goal": "Make {topic} easier to understand, maintain, present, or hand off.",
        "steps": (
            "Write what the project does and who it helps.",
            "Document the main setup, usage, or handoff steps.",
            "Add known limitations and future improvements.",
        ),
        "deliverable": "A clear documentation page for {topic}.",
        "done_when": "Someone else can understand the purpose and basic usage from the document.",
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
            "Write the remaining improvements for the next version.",
        ),
        "deliverable": "A final quality review checklist for {topic}.",
        "done_when": "All success criteria are marked passed, failed, or moved to a future version.",
        "benefit": "The user finishes with a clear view of quality and next steps.",
        "priority": "high",
        "estimated_hours": 1.5,
    },
    {
        "title": "Schedule {topic} work sessions",
        "goal": "Protect focused time so {topic} keeps moving forward before the deadline.",
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
            "Create a tracker with task, status, blocker, and next action columns.",
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


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _derive_project_title(project_idea: str) -> str:
    title = re.split(r"[\n.!?]", project_idea.strip(), maxsplit=1)[0].strip()
    title = re.sub(r"^\s*i\s+(want|need)\s+to\s+", "", title, flags=re.IGNORECASE)
    title = re.sub(r"^\s*(build|create|start|launch|make)\s+", "", title, flags=re.IGNORECASE).strip()

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

    return " ".join(words) if words else "project"


def _build_description(blueprint: dict[str, object], topic: str) -> str:
    steps = blueprint["steps"]
    assert isinstance(steps, tuple)

    return (
        f"Goal: {blueprint['goal']}\n\n"
        "Steps:\n"
        f"1. {steps[0]}\n"
        f"2. {steps[1]}\n"
        f"3. {steps[2]}\n\n"
        f"Deliverable: {blueprint['deliverable']}\n\n"
        f"Done when: {blueprint['done_when']}\n\n"
        f"Customer benefit: {blueprint['benefit']}"
    ).replace("{topic}", topic)


def _build_due_dates(deadline: datetime, task_count: int) -> list[datetime]:
    now = datetime.now(timezone.utc)
    deadline_utc = _to_utc(deadline)

    if task_count <= 0:
        return []

    if deadline_utc <= now:
        return [deadline_utc for _ in range(task_count)]

    step_seconds = (deadline_utc - now).total_seconds() / (task_count + 1)

    return [now + timedelta(seconds=step_seconds * (index + 1)) for index in range(task_count)]


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
        pieces.append(f"Requirements and constraints: {requirements}")

    return "\n".join(pieces)


def _build_preview_tasks(preview_data: AIPlanPreviewRequest, topic: str) -> list[AIPlanPreviewTaskResponse]:
    task_count = max(3, min(12, preview_data.preferred_task_count))
    due_dates = _build_due_dates(preview_data.deadline, task_count)
    tasks: list[AIPlanPreviewTaskResponse] = []

    for index, blueprint in enumerate(TASK_BLUEPRINTS[:task_count]):
        title = str(blueprint["title"]).replace("{topic}", topic)
        tasks.append(
            AIPlanPreviewTaskResponse(
                suggested_order=index + 1,
                title=title,
                description=_build_description(blueprint, topic),
                priority=str(blueprint["priority"]),
                estimated_hours=float(blueprint["estimated_hours"]),
                status=TaskStatus.todo.value,
                due_date=due_dates[index] if index < len(due_dates) else None,
                assigned_to=None,
            )
        )

    return tasks


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

    topic = _topic_from_idea(preview_data.project_idea, preview_data.requirements)
    project_title = _derive_project_title(preview_data.project_idea)
    tasks = _build_preview_tasks(preview_data, topic)

    milestones = []
    if preview_data.include_milestones:
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

    return AIPlanPreviewResponse(
        success=True,
        message="Generated a structured project plan.",
        ai_generation_status="generated",
        source="stable_ai_planner_v1",
        domain=topic,
        project_title=project_title,
        description=_build_project_description(preview_data),
        project_type=preview_data.project_type,
        team_id=preview_data.team_id,
        deadline=preview_data.deadline,
        summary=f"Generated a practical plan for {project_title} with {len(tasks)} focused tasks.",
        tasks=tasks,
        milestones=milestones,
        risks=[
            {
                "risk": "The idea may still be too broad for the first version.",
                "recommendation": "Keep only the requirements that directly support the first usable result.",
            },
            {
                "risk": "Testing may reveal missing details late in the process.",
                "recommendation": "Test the core flow before adding polish or optional work.",
            },
        ],
        recommendations=[
            "Start with the success criteria task before building anything large.",
            "Keep every task tied to a visible deliverable.",
            "Review the generated plan and adjust wording before accepting it.",
        ],
        project_idea=preview_data.project_idea,
        requirements=preview_data.requirements,
        available_hours_per_week=preview_data.available_hours_per_week,
        preferred_task_count=preview_data.preferred_task_count,
        rejected_generic_count=0,
        rejected_unrelated_count=0,
    )
