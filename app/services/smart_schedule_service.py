from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from math import ceil

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.smart_schedule import SmartSchedule
from app.models.task import Task
from app.models.user import User
from app.schemas.smart_schedule_schema import (
    SmartSchedulePreviewResponse,
    SmartScheduleRequest,
    SmartScheduleTaskItem,
)


PRIORITY_ORDER = {
    "high": 0,
    "medium": 1,
    "low": 2,
}


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _number_to_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0

    return float(value)


def _end_of_day(value: datetime) -> datetime:
    return value.replace(hour=23, minute=59, second=0, microsecond=0)


def _task_sort_key(task: Task) -> tuple[int, datetime, int]:
    created_at = _to_utc(task.created_at)

    return (
        PRIORITY_ORDER.get(task.priority, 99),
        created_at,
        task.task_id,
    )


def get_project_tasks_for_smart_schedule(
    db: Session,
    project_id: int,
) -> list[Task]:
    stmt = select(Task).where(Task.project_id == project_id)
    return list(db.execute(stmt).scalars().all())


def build_smart_schedule_preview(
    project: Project,
    tasks: list[Task],
    schedule_request: SmartScheduleRequest,
) -> SmartSchedulePreviewResponse:
    now = datetime.now(timezone.utc)
    project_deadline = _to_utc(project.deadline)

    start_date = (
        _to_utc(schedule_request.start_date)
        if schedule_request.start_date is not None
        else now
    )

    warnings: list[str] = []

    if start_date < now:
        start_date = now
        warnings.append("Start date was in the past, so scheduling starts from now.")

    if project_deadline <= start_date:
        warnings.append("Project deadline is already passed or too close for normal scheduling.")

    completed_tasks = [
        task
        for task in tasks
        if task.status == "completed"
    ]

    schedulable_tasks = sorted(
        [
            task
            for task in tasks
            if task.status != "completed"
        ],
        key=_task_sort_key,
    )

    if not schedulable_tasks:
        warnings.append("There are no incomplete tasks to schedule.")

    current_date = _end_of_day(start_date)
    remaining_capacity = schedule_request.daily_capacity_hours

    scheduled_items: list[SmartScheduleTaskItem] = []
    estimated_total_hours = 0.0

    for task in schedulable_tasks:
        estimated_hours = _number_to_float(task.estimated_hours)

        if estimated_hours <= 0:
            estimated_hours = 1.0

        estimated_total_hours += estimated_hours

        if estimated_hours > remaining_capacity and remaining_capacity < schedule_request.daily_capacity_hours:
            current_date = _end_of_day(current_date + timedelta(days=1))
            remaining_capacity = schedule_request.daily_capacity_hours

        days_needed = max(
            1,
            ceil(estimated_hours / schedule_request.daily_capacity_hours),
        )

        suggested_due_date = _end_of_day(
            current_date + timedelta(days=days_needed - 1)
        )

        remaining_after_task = remaining_capacity - estimated_hours

        if remaining_after_task <= 0:
            current_date = _end_of_day(suggested_due_date + timedelta(days=1))
            remaining_capacity = schedule_request.daily_capacity_hours
        else:
            current_date = suggested_due_date
            remaining_capacity = remaining_after_task

        scheduled_items.append(
            SmartScheduleTaskItem(
                task_id=task.task_id,
                title=task.title,
                priority=task.priority,
                status=task.status,
                assigned_to=task.assigned_to,
                estimated_hours=round(estimated_hours, 2),
                old_due_date=task.due_date,
                suggested_due_date=suggested_due_date,
                is_after_project_deadline=suggested_due_date > project_deadline,
            )
        )

    first_suggested_due_date = (
        scheduled_items[0].suggested_due_date
        if scheduled_items
        else None
    )

    last_suggested_due_date = (
        scheduled_items[-1].suggested_due_date
        if scheduled_items
        else None
    )

    if last_suggested_due_date is not None and last_suggested_due_date > project_deadline:
        warnings.append("The generated schedule goes beyond the project deadline.")

    return SmartSchedulePreviewResponse(
        project_id=project.project_id,
        strategy=schedule_request.strategy,
        daily_capacity_hours=schedule_request.daily_capacity_hours,
        total_tasks=len(tasks),
        schedulable_task_count=len(schedulable_tasks),
        completed_task_count=len(completed_tasks),
        estimated_total_hours=round(estimated_total_hours, 2),
        project_deadline=project_deadline,
        first_suggested_due_date=first_suggested_due_date,
        last_suggested_due_date=last_suggested_due_date,
        tasks=scheduled_items,
        warnings=warnings,
    )


def preview_smart_schedule_for_project(
    db: Session,
    project: Project,
    schedule_request: SmartScheduleRequest,
) -> SmartSchedulePreviewResponse:
    tasks = get_project_tasks_for_smart_schedule(
        db=db,
        project_id=project.project_id,
    )

    return build_smart_schedule_preview(
        project=project,
        tasks=tasks,
        schedule_request=schedule_request,
    )


def apply_smart_schedule_to_tasks(
    db: Session,
    preview: SmartSchedulePreviewResponse,
) -> list[int]:
    task_ids = [
        item.task_id
        for item in preview.tasks
    ]

    if not task_ids:
        return []

    stmt = select(Task).where(Task.task_id.in_(task_ids))
    tasks_by_id = {
        task.task_id: task
        for task in db.execute(stmt).scalars().all()
    }

    applied_task_ids: list[int] = []

    for item in preview.tasks:
        task = tasks_by_id.get(item.task_id)

        if task is None or task.status == "completed":
            continue

        task.due_date = item.suggested_due_date
        applied_task_ids.append(task.task_id)

    return applied_task_ids


def create_smart_schedule_for_project(
    db: Session,
    project: Project,
    current_user: User,
    schedule_request: SmartScheduleRequest,
) -> SmartSchedule:
    preview = preview_smart_schedule_for_project(
        db=db,
        project=project,
        schedule_request=schedule_request,
    )

    schedule_payload = preview.model_dump(mode="json")

    smart_schedule = SmartSchedule(
        project_id=project.project_id,
        generated_by=current_user.user_id,
        strategy=schedule_request.strategy.value,
        schedule_data=schedule_payload,
        applied_at=None,
    )

    db.add(smart_schedule)
    db.flush()

    applied_task_ids: list[int] = []

    if schedule_request.apply_schedule:
        applied_task_ids = apply_smart_schedule_to_tasks(
            db=db,
            preview=preview,
        )
        smart_schedule.applied_at = datetime.now(timezone.utc)
        smart_schedule.schedule_data = {
            **schedule_payload,
            "applied_task_ids": applied_task_ids,
        }

    db.commit()
    db.refresh(smart_schedule)

    return smart_schedule


def get_smart_schedules_for_project(
    db: Session,
    project: Project,
) -> list[SmartSchedule]:
    stmt = (
        select(SmartSchedule)
        .where(SmartSchedule.project_id == project.project_id)
        .order_by(SmartSchedule.created_at.desc(), SmartSchedule.schedule_id.desc())
    )

    return list(db.execute(stmt).scalars().all())