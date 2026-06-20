from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.subtask import Subtask
from app.models.task import Task
from app.models.user import User
from app.schemas.task_schema import (
    SubtaskCompletionUpdate,
    SubtaskCreate,
    SubtaskUpdate,
)


def list_subtasks(db: Session, task: Task) -> list[Subtask]:
    stmt = (
        select(Subtask)
        .where(Subtask.task_id == task.task_id)
        .order_by(Subtask.created_at, Subtask.subtask_id)
    )
    return list(db.execute(stmt).scalars().all())


def get_subtask(db: Session, task: Task, subtask_id: int) -> Subtask | None:
    stmt = select(Subtask).where(
        Subtask.subtask_id == subtask_id,
        Subtask.task_id == task.task_id,
    )
    return db.execute(stmt).scalars().first()


def create_subtask(
    db: Session,
    task: Task,
    subtask_data: SubtaskCreate,
    current_user: User,
) -> Subtask:
    subtask = Subtask(
        task_id=task.task_id,
        created_by=current_user.user_id,
        title=subtask_data.title.strip(),
        is_completed=False,
    )
    db.add(subtask)
    db.commit()
    db.refresh(subtask)
    db.expire(task, ["subtasks"])
    return subtask


def update_subtask(
    db: Session,
    task: Task,
    subtask: Subtask,
    subtask_data: SubtaskUpdate,
) -> Subtask:
    subtask.title = subtask_data.title.strip()
    db.commit()
    db.refresh(subtask)
    db.expire(task, ["subtasks"])
    return subtask


def set_subtask_completion(
    db: Session,
    task: Task,
    subtask: Subtask,
    completion_data: SubtaskCompletionUpdate,
) -> Subtask:
    subtask.is_completed = completion_data.is_completed
    subtask.completed_at = (
        datetime.now(timezone.utc) if completion_data.is_completed else None
    )
    db.commit()
    db.refresh(subtask)
    db.expire(task, ["subtasks"])
    return subtask


def delete_subtask(db: Session, task: Task, subtask: Subtask) -> None:
    db.delete(subtask)
    db.commit()
    db.expire(task, ["subtasks"])
