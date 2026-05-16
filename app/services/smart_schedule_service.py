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


def _get_start_date(
    schedule_request: SmartScheduleRequest,
    now: datetime,
    warnings: list[str],
) -> datetime:
    start_date = (
        _to_utc(schedule_request.start_date)
        if schedule_request.start_date is not None
        else now
    )

    if start_date < now:
        warnings.append("Start date was in the past, so scheduling starts from now.")
        return now

    return start_date


def _get_completed_tasks(tasks: list[Task]) -> list[Task]:
    return [
        task
        for task in tasks
        if task.status == "completed"
    ]


def _get_schedulable_tasks(tasks: list[Task]) -> list[Task]:
    return sorted(
        [
            task
            for task in tasks
            if task.status != "completed"
        ],
        key=_task_sort_key,
    )


def _get_effective_estimated_hours(task: Task) -> float:
    estimated_hours = _number_to_float(task.estimated_hours)

    if estimated_hours <= 0:
        return 1.0

    return estimated_hours


def _should_move_to_next_day(
    estimated_hours: float,
    remaining_capacity: float,
    daily_capacity_hours: float,
) -> bool:
    return estimated_hours > remaining_capacity and remaining_capacity < daily_capacity_hours


def _calculate_suggested_due_date(
    current_date: datetime,
    estimated_hours: float,
    daily_capacity_hours: float,
) -> datetime:
    days_needed = max(
        1,
        ceil(estimated_hours / daily_capacity_hours),
    )

    return _end_of_day(
        current_date + timedelta(days=days_needed - 1)
    )


def _get_next_schedule_position(
    suggested_due_date: datetime,
    remaining_after_task: float,
    daily_capacity_hours: float,
) -> tuple[datetime, float]:
    if remaining_after_task <= 0:
        return (
            _end_of_day(suggested_due_date + timedelta(days=1)),
            daily_capacity_hours,
        )

    return suggested_due_date, remaining_after_task


def _build_scheduled_item(
    task: Task,
    estimated_hours: float,
    suggested_due_date: datetime,
    project_deadline: datetime,
) -> SmartScheduleTaskItem:
    return SmartScheduleTaskItem(
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


def _build_scheduled_items(
    schedulable_tasks: list[Task],
    start_date: datetime,
    daily_capacity_hours: float,
    project_deadline: datetime,
) -> tuple[list[SmartScheduleTaskItem], float]:
    current_date = _end_of_day(start_date)
    remaining_capacity = daily_capacity_hours
    estimated_total_hours = 0.0
    scheduled_items: list[SmartScheduleTaskItem] = []

    for task in schedulable_tasks:
        estimated_hours = _get_effective_estimated_hours(task)
        estimated_total_hours += estimated_hours

        if _should_move_to_next_day(
            estimated_hours=estimated_hours,
            remaining_capacity=remaining_capacity,
            daily_capacity_hours=daily_capacity_hours,
        ):
            current_date = _end_of_day(current_date + timedelta(days=1))
            remaining_capacity = daily_capacity_hours

        suggested_due_date = _calculate_suggested_due_date(
            current_date=current_date,
            estimated_hours=estimated_hours,
            daily_capacity_hours=daily_capacity_hours,
        )

        remaining_after_task = remaining_capacity - estimated_hours

        current_date, remaining_capacity = _get_next_schedule_position(
            suggested_due_date=suggested_due_date,
            remaining_after_task=remaining_after_task,
            daily_capacity_hours=daily_capacity_hours,
        )

        scheduled_items.append(
            _build_scheduled_item(
                task=task,
                estimated_hours=estimated_hours,
                suggested_due_date=suggested_due_date,
                project_deadline=project_deadline,
            )
        )

    return scheduled_items, estimated_total_hours


def _get_first_suggested_due_date(
    scheduled_items: list[SmartScheduleTaskItem],
) -> datetime | None:
    if not scheduled_items:
        return None

    return scheduled_items[0].suggested_due_date


def _get_last_suggested_due_date(
    scheduled_items: list[SmartScheduleTaskItem],
) -> datetime | None:
    if not scheduled_items:
        return None

    return scheduled_items[-1].suggested_due_date


def _add_schedule_warnings(
    warnings: list[str],
    project_deadline: datetime,
    start_date: datetime,
    schedulable_tasks: list[Task],
    last_suggested_due_date: datetime | None,
) -> None:
    if project_deadline <= start_date:
        warnings.append("Project deadline is already passed or too close for normal scheduling.")

    if not schedulable_tasks:
        warnings.append("There are no incomplete tasks to schedule.")

    if last_suggested_due_date is not None and last_suggested_due_date > project_deadline:
        warnings.append("The generated schedule goes beyond the project deadline.")


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
    warnings: list[str] = []

    start_date = _get_start_date(
        schedule_request=schedule_request,
        now=now,
        warnings=warnings,
    )

    completed_tasks = _get_completed_tasks(tasks)
    schedulable_tasks = _get_schedulable_tasks(tasks)

    scheduled_items, estimated_total_hours = _build_scheduled_items(
        schedulable_tasks=schedulable_tasks,
        start_date=start_date,
        daily_capacity_hours=schedule_request.daily_capacity_hours,
        project_deadline=project_deadline,
    )

    first_suggested_due_date = _get_first_suggested_due_date(scheduled_items)
    last_suggested_due_date = _get_last_suggested_due_date(scheduled_items)

    _add_schedule_warnings(
        warnings=warnings,
        project_deadline=project_deadline,
        start_date=start_date,
        schedulable_tasks=schedulable_tasks,
        last_suggested_due_date=last_suggested_due_date,
    )

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