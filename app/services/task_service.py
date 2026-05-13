from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.task_schema import (
    TaskCreate,
    TaskPriority,
    TaskStatus,
    TaskUpdate,
    TeamTaskCreate,
    TeamTaskUpdate,
)


def get_my_personal_project_for_tasks(
    db: Session,
    project_id: int,
    current_user: User,
) -> Project | None:
    stmt = select(Project).where(
        Project.project_id == project_id,
        Project.created_by == current_user.user_id,
        Project.project_type == "personal",
    )

    return db.execute(stmt).scalars().first()


def create_task_for_personal_project(
    db: Session,
    project: Project,
    task_data: TaskCreate,
    current_user: User,
) -> Task:
    task = Task(
        project_id=project.project_id,
        assigned_to=current_user.user_id,
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
    db.commit()
    db.refresh(task)

    return task


def get_tasks_for_personal_project(
    db: Session,
    project: Project,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
) -> list[Task]:
    stmt = select(Task).where(
        Task.project_id == project.project_id,
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
    stmt = select(Task).where(
        Task.task_id == task_id,
        Task.project_id == project.project_id,
    )

    return db.execute(stmt).scalars().first()


def update_task_for_personal_project(
    db: Session,
    task: Task,
    task_data: TaskUpdate,
) -> Task:
    update_data = task_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "status":
            if value is None:
                continue

            new_status = value.value
            task.status = new_status

            if new_status == TaskStatus.completed.value:
                task.completed_at = datetime.now(timezone.utc)
            else:
                task.completed_at = None

        elif field == "priority":
            if value is None:
                continue

            task.priority = value.value

        else:
            setattr(task, field, value)

    db.commit()
    db.refresh(task)

    return task


def delete_task_for_personal_project(
    db: Session,
    task: Task,
) -> None:
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
    db.commit()
    db.refresh(task)

    return task


def get_tasks_for_team_project(
    db: Session,
    project: Project,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    assigned_to: int | None = None,
) -> list[Task]:
    stmt = select(Task).where(
        Task.project_id == project.project_id,
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
    stmt = select(Task).where(
        Task.task_id == task_id,
        Task.project_id == project.project_id,
    )

    return db.execute(stmt).scalars().first()


def update_task_for_team_project(
    db: Session,
    task: Task,
    task_data: TeamTaskUpdate,
) -> Task:
    update_data = task_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "status":
            if value is None:
                continue

            new_status = value.value
            task.status = new_status

            if new_status == TaskStatus.completed.value:
                task.completed_at = datetime.now(timezone.utc)
            else:
                task.completed_at = None

        elif field == "priority":
            if value is None:
                continue

            task.priority = value.value

        else:
            setattr(task, field, value)

    db.commit()
    db.refresh(task)

    return task


def delete_task_for_team_project(
    db: Session,
    task: Task,
) -> None:
    db.delete(task)
    db.commit()