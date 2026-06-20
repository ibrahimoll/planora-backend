from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.activity_log_schema import ActivityLogEventType
from app.schemas.task_schema import (
    TaskCreate,
    TaskPriority,
    TaskStatus,
    TaskUpdate,
    TeamTaskCreate,
    TeamTaskUpdate,
)
from app.services.activity_log_service import create_activity_log
from app.services.project_service import can_manage_project, get_project_membership


def get_my_personal_project_for_tasks(
    db: Session,
    project_id: int,
    current_user: User,
) -> Project | None:
    member_exists = (
        select(ProjectMember.member_id)
        .where(
            ProjectMember.project_id == Project.project_id,
            ProjectMember.user_id == current_user.user_id,
        )
        .exists()
    )
    stmt = select(Project).where(
        Project.project_id == project_id,
        Project.project_type == "personal",
        (
            (Project.created_by == current_user.user_id)
            | member_exists
        ),
    )

    return db.execute(stmt).scalars().first()


def create_task_for_personal_project(
    db: Session,
    project: Project,
    task_data: TaskCreate,
    current_user: User,
    assigned_to: int | None = None,
) -> Task:
    task = Task(
        project_id=project.project_id,
        assigned_to=assigned_to or current_user.user_id,
        created_by=current_user.user_id,
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority.value,
        estimated_hours=task_data.estimated_hours,
        actual_hours=task_data.actual_hours,
        status=TaskStatus.todo.value,
        due_date=task_data.due_date,
        completed_at=None,
    )

    db.add(task)
    db.flush()

    create_activity_log(
        db=db,
        project=project,
        actor=current_user,
        task=task,
        event_type=ActivityLogEventType.TASK_CREATED,
        message=f"{current_user.full_name} created task '{task.title}'.",
        metadata={
            "priority": task.priority,
            "assigned_to": task.assigned_to,
        },
        commit=False,
    )

    db.commit()
    db.refresh(task)
    db.refresh(task, attribute_names=["assignee", "creator"])

    return task


def can_manage_personal_project_tasks(
    db: Session,
    project: Project,
    current_user: User,
) -> bool:
    if project.created_by == current_user.user_id:
        return True

    membership = get_project_membership(
        db=db,
        project_id=project.project_id,
        user_id=current_user.user_id,
    )

    return membership is not None and can_manage_project(membership)


def get_tasks_for_personal_project(
    db: Session,
    project: Project,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
) -> list[Task]:
    stmt = (
        select(Task)
        .options(
            selectinload(Task.assignee),
            selectinload(Task.creator),
            selectinload(Task.subtasks),
        )
        .where(
            Task.project_id == project.project_id,
        )
    )

    if status is not None:
        stmt = stmt.where(Task.status == status.value)

    if priority is not None:
        stmt = stmt.where(Task.priority == priority.value)

    stmt = stmt.order_by(Task.created_at.desc())

    return list(db.execute(stmt).scalars().all())


def get_task_for_personal_project_by_id(
    db: Session,
    project: Project,
    task_id: int,
) -> Task | None:
    stmt = (
        select(Task)
        .options(
            selectinload(Task.assignee),
            selectinload(Task.creator),
            selectinload(Task.subtasks),
        )
        .where(
            Task.task_id == task_id,
            Task.project_id == project.project_id,
        )
    )

    return db.execute(stmt).scalars().first()


def apply_task_field_update(
    task: Task,
    field: str,
    value: Any,
) -> bool:
    if value is None:
        return False

    old_value = getattr(task, field)

    if field == "status":
        new_status = value.value
        task.status = new_status
        task.completed_at = (
            datetime.now(timezone.utc)
            if new_status == TaskStatus.completed.value
            else None
        )
        return old_value != new_status

    if field == "priority":
        new_priority = value.value
        task.priority = new_priority
        return old_value != new_priority

    setattr(task, field, value)
    return old_value != value


def apply_task_updates(
    task: Task,
    update_data: dict[str, Any],
) -> list[str]:
    changed_fields: list[str] = []

    for field, value in update_data.items():
        if apply_task_field_update(
            task=task,
            field=field,
            value=value,
        ):
            changed_fields.append(field)

    return changed_fields


def get_task_update_activity_event_type(
    previous_status: str,
    new_status: str,
) -> ActivityLogEventType:
    if (
        previous_status != TaskStatus.completed.value
        and new_status == TaskStatus.completed.value
    ):
        return ActivityLogEventType.TASK_COMPLETED

    return ActivityLogEventType.TASK_UPDATED


def log_task_update_activity(
    db: Session,
    task: Task,
    current_user: User,
    previous_status: str,
    changed_fields: list[str],
) -> None:
    if not changed_fields:
        return

    create_activity_log(
        db=db,
        project=task.project,
        actor=current_user,
        task=task,
        event_type=get_task_update_activity_event_type(
            previous_status=previous_status,
            new_status=task.status,
        ),
        message=f"{current_user.full_name} updated task '{task.title}'.",
        metadata={
            "changed_fields": changed_fields,
            "previous_status": previous_status,
            "new_status": task.status,
        },
        commit=False,
    )


def update_task(
    db: Session,
    task: Task,
    update_data: dict[str, Any],
    current_user: User,
) -> Task:
    previous_status = task.status
    changed_fields = apply_task_updates(
        task=task,
        update_data=update_data,
    )

    log_task_update_activity(
        db=db,
        task=task,
        current_user=current_user,
        previous_status=previous_status,
        changed_fields=changed_fields,
    )

    db.commit()
    db.refresh(task)
    db.refresh(task, attribute_names=["assignee", "creator"])

    return task


def update_task_for_personal_project(
    db: Session,
    task: Task,
    task_data: TaskUpdate,
    current_user: User,
) -> Task:
    return update_task(
        db=db,
        task=task,
        update_data=task_data.model_dump(exclude_unset=True),
        current_user=current_user,
    )


def delete_task_for_personal_project(
    db: Session,
    task: Task,
    current_user: User,
) -> None:
    create_activity_log(
        db=db,
        project=task.project,
        actor=current_user,
        task=task,
        event_type=ActivityLogEventType.TASK_DELETED,
        message=f"{current_user.full_name} deleted task '{task.title}'.",
        metadata={
            "task_id": task.task_id,
            "task_title": task.title,
        },
        commit=False,
    )

    db.delete(task)
    db.commit()


def get_team_project_for_tasks(
    db: Session,
    team_id: int,
    project_id: int,
) -> Project | None:
    stmt = select(Project).where(
        Project.project_id == project_id,
        Project.team_id == team_id,
        Project.project_type == "team",
    )

    return db.execute(stmt).scalars().first()


def get_project_membership_for_tasks(
    db: Session,
    project_id: int,
    user_id: int,
) -> ProjectMember | None:
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    )

    return db.execute(stmt).scalars().first()


def create_task_for_team_project(
    db: Session,
    project: Project,
    task_data: TeamTaskCreate,
    current_user: User,
    assigned_to: int | None,
) -> Task:
    task = Task(
        project_id=project.project_id,
        assigned_to=assigned_to,
        created_by=current_user.user_id,
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority.value,
        estimated_hours=task_data.estimated_hours,
        actual_hours=task_data.actual_hours,
        status=TaskStatus.todo.value,
        due_date=task_data.due_date,
        completed_at=None,
    )

    db.add(task)
    db.flush()

    create_activity_log(
        db=db,
        project=project,
        actor=current_user,
        task=task,
        event_type=ActivityLogEventType.TASK_CREATED,
        message=f"{current_user.full_name} created task '{task.title}'.",
        metadata={
            "priority": task.priority,
            "assigned_to": task.assigned_to,
        },
        commit=False,
    )

    db.commit()
    db.refresh(task)
    db.refresh(task, attribute_names=["assignee", "creator"])

    return task


def get_tasks_for_team_project(
    db: Session,
    project: Project,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    assigned_to: int | None = None,
) -> list[Task]:
    stmt = (
        select(Task)
        .options(
            selectinload(Task.assignee),
            selectinload(Task.creator),
            selectinload(Task.subtasks),
        )
        .where(
            Task.project_id == project.project_id,
        )
    )

    if status is not None:
        stmt = stmt.where(Task.status == status.value)

    if priority is not None:
        stmt = stmt.where(Task.priority == priority.value)

    if assigned_to is not None:
        stmt = stmt.where(Task.assigned_to == assigned_to)

    stmt = stmt.order_by(Task.created_at.desc())

    return list(db.execute(stmt).scalars().all())


def get_task_for_team_project_by_id(
    db: Session,
    project: Project,
    task_id: int,
) -> Task | None:
    stmt = (
        select(Task)
        .options(
            selectinload(Task.assignee),
            selectinload(Task.creator),
            selectinload(Task.subtasks),
        )
        .where(
            Task.task_id == task_id,
            Task.project_id == project.project_id,
        )
    )

    return db.execute(stmt).scalars().first()


def update_task_for_team_project(
    db: Session,
    task: Task,
    task_data: TeamTaskUpdate,
    current_user: User,
) -> Task:
    return update_task(
        db=db,
        task=task,
        update_data=task_data.model_dump(exclude_unset=True),
        current_user=current_user,
    )


def delete_task_for_team_project(
    db: Session,
    task: Task,
    current_user: User,
) -> None:
    create_activity_log(
        db=db,
        project=task.project,
        actor=current_user,
        task=task,
        event_type=ActivityLogEventType.TASK_DELETED,
        message=f"{current_user.full_name} deleted task '{task.title}'.",
        metadata={
            "task_id": task.task_id,
            "task_title": task.title,
        },
        commit=False,
    )

    db.delete(task)
    db.commit()
