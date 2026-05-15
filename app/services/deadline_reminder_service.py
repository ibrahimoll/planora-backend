from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.deadline_reminder import DeadlineReminder
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.deadline_reminder_schema import DeadlineReminderType
from app.schemas.notification_schema import NotificationType
from app.services.notification_service import create_notification


def reminder_already_exists(
    db: Session,
    task_id: int,
    user_id: int,
    reminder_type: DeadlineReminderType,
    due_date_snapshot: datetime,
) -> bool:
    stmt = select(DeadlineReminder).where(
        DeadlineReminder.task_id == task_id,
        DeadlineReminder.user_id == user_id,
        DeadlineReminder.reminder_type == reminder_type.value,
        DeadlineReminder.due_date_snapshot == due_date_snapshot,
    )

    return db.execute(stmt).scalars().first() is not None


def create_deadline_reminder_if_needed(
    db: Session,
    task: Task,
    project: Project,
    reminder_type: DeadlineReminderType,
) -> bool:
    if task.assigned_to is None:
        return False

    if task.due_date is None:
        return False

    if reminder_already_exists(
        db=db,
        task_id=task.task_id,
        user_id=task.assigned_to,
        reminder_type=reminder_type,
        due_date_snapshot=task.due_date,
    ):
        return False

    reminder = DeadlineReminder(
        task_id=task.task_id,
        project_id=task.project_id,
        user_id=task.assigned_to,
        reminder_type=reminder_type.value,
        due_date_snapshot=task.due_date,
    )

    db.add(reminder)

    if reminder_type == DeadlineReminderType.DUE_SOON:
        title = "Task deadline reminder"
        message = (
            f'Task "{task.title}" in project "{project.title}" '
            f"is due soon: {task.due_date.isoformat()}."
        )
    else:
        title = "Task overdue"
        message = (
            f'Task "{task.title}" in project "{project.title}" '
            f"is overdue. Deadline was: {task.due_date.isoformat()}."
        )

    create_notification(
        db=db,
        user_id=task.assigned_to,
        title=title,
        message=message,
        notification_type=NotificationType.DEADLINE,
        commit=False,
    )

    return True


def run_deadline_reminder_scan(
    db: Session,
    hours_ahead: int = 24,
    include_overdue: bool = True,
) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(hours=hours_ahead)

    due_soon_created = 0
    overdue_created = 0

    due_soon_stmt = (
        select(Task, Project)
        .join(Project, Task.project_id == Project.project_id)
        .where(
            Task.due_date.is_not(None),
            Task.assigned_to.is_not(None),
            Task.status != "completed",
            Task.due_date >= now,
            Task.due_date <= window_end,
        )
    )

    due_soon_rows = db.execute(due_soon_stmt).all()

    for task, project in due_soon_rows:
        created = create_deadline_reminder_if_needed(
            db=db,
            task=task,
            project=project,
            reminder_type=DeadlineReminderType.DUE_SOON,
        )

        if created:
            due_soon_created += 1

    if include_overdue:
        overdue_stmt = (
            select(Task, Project)
            .join(Project, Task.project_id == Project.project_id)
            .where(
                Task.due_date.is_not(None),
                Task.assigned_to.is_not(None),
                Task.status != "completed",
                Task.due_date < now,
            )
        )

        overdue_rows = db.execute(overdue_stmt).all()

        for task, project in overdue_rows:
            created = create_deadline_reminder_if_needed(
                db=db,
                task=task,
                project=project,
                reminder_type=DeadlineReminderType.OVERDUE,
            )

            if created:
                overdue_created += 1

    db.commit()

    return {
        "due_soon_created": due_soon_created,
        "overdue_created": overdue_created,
        "total_created": due_soon_created + overdue_created,
    }


def get_my_deadline_reminders(
    db: Session,
    current_user: User,
    limit: int = 50,
) -> list[DeadlineReminder]:
    stmt = (
        select(DeadlineReminder)
        .where(DeadlineReminder.user_id == current_user.user_id)
        .order_by(DeadlineReminder.generated_at.desc())
        .limit(limit)
    )

    return list(db.execute(stmt).scalars().all())