from __future__ import annotations

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
    AIPlanGenerateRequest,
    AIPlanGenerateResponse,
    AIPlanGeneratedTaskResponse,
)
from app.schemas.task_schema import TaskStatus
from app.services.activity_log_service import create_activity_log


TASK_TITLE_TEMPLATES = [
    "Define scope and success criteria",
    "Analyze requirements and constraints",
    "Design the project structure",
    "Prepare the implementation plan",
    "Complete the core project work",
    "Review and test the work",
    "Fix issues and improve quality",
    "Prepare final delivery and documentation",
    "Evaluate risks and backup plan",
    "Finalize presentation material",
    "Collect feedback and adjust",
    "Submit final version",
]

BUSINESS_TASK_TITLE_TEMPLATES = [
    "Research target niche and customer demand",
    "Define startup budget and pricing model",
    "Compare suppliers and sample options",
    "Choose brand name and positioning",
    "Plan the first product collection",
    "Set up sales channel and social presence",
    "Map launch timeline and promotions",
    "Confirm delivery and fulfillment process",
    "Check legal, tax, and operations requirements",
    "Prepare inventory and order tracking",
    "Create customer service and returns process",
    "Review launch readiness and backup plan",
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

BUSINESS_KEYWORDS = (
    "business",
    "clothing",
    "fashion",
    "brand",
    "boutique",
    "shop",
    "store",
    "supplier",
    "suppliers",
    "inventory",
    "delivery",
    "ecommerce",
    "e-commerce",
    "product collection",
    "startup",
    "launch",
    "legal",
)

SOFTWARE_KEYWORDS = (
    "software",
    "app",
    "mobile app",
    "website",
    "platform",
    "flutter",
    "backend",
    "frontend",
    "code",
    "coding",
    "api",
)


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _build_due_dates(project: Project, task_count: int) -> list[datetime]:
    now = datetime.now(timezone.utc)
    deadline = _to_utc(project.deadline)

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


def _contains_any(value: str, keywords: tuple[str, ...]) -> bool:
    normalized = value.lower()

    return any(keyword in normalized for keyword in keywords)


def _select_task_title_templates(project_context: str) -> list[str]:
    is_business = _contains_any(project_context, BUSINESS_KEYWORDS)
    is_software = _contains_any(project_context, SOFTWARE_KEYWORDS)

    if is_business and not is_software:
        return BUSINESS_TASK_TITLE_TEMPLATES

    if is_software:
        return SOFTWARE_TASK_TITLE_TEMPLATES

    return TASK_TITLE_TEMPLATES


def _build_milestones(
    project_context: str,
    include_milestones: bool,
) -> list[dict[str, Any]]:
    if not include_milestones:
        return []

    if _contains_any(project_context, BUSINESS_KEYWORDS) and not _contains_any(
        project_context,
        SOFTWARE_KEYWORDS,
    ):
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


def _build_risks(project_context: str) -> list[dict[str, str]]:
    if _contains_any(project_context, BUSINESS_KEYWORDS) and not _contains_any(
        project_context,
        SOFTWARE_KEYWORDS,
    ):
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


def build_generated_plan(
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
    combined_context = f"{project.title}\n{project_context}"
    task_title_templates = _select_task_title_templates(combined_context)

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
                "description": (
                    f"For project '{project.title}', complete this step based on: "
                    f"{project_context[:400]}"
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
        "source": "local_rule_based_v1",
        "summary": (
            f"Generated a structured plan for '{project.title}' with "
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
            project_context=combined_context,
            include_milestones=include_milestones,
        ),
        "risks": _build_risks(combined_context),
        "recommendations": [
            "Review the generated tasks before starting.",
            "Adjust due dates if the project deadline is very close.",
            "Assign team tasks manually after generation.",
        ],
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
            description=str(task_data["description"]),
            priority=str(task_data["priority"]),
            estimated_hours=float(task_data["estimated_hours"]),
            actual_hours=None,
            status=TaskStatus.todo.value,
            due_date=_parse_due_date(str(task_data["due_date"])),
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
            "source": "local_rule_based_v1",
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
