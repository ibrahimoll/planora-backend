from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.activity_log_schema import (
    ActivityLogEventType,
    ActivityLogResponse,
)


def normalize_event_type(event_type: ActivityLogEventType | str) -> str:
    if isinstance(event_type, ActivityLogEventType):
        return event_type.value

    return event_type


def create_activity_log(
    db: Session,
    project: Project,
    actor: User | None,
    event_type: ActivityLogEventType | str,
    message: str,
    task: Task | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> ActivityLog:
    activity_log = ActivityLog(
        project_id=project.project_id,
        task_id=task.task_id if task is not None else None,
        actor_id=actor.user_id if actor is not None else None,
        event_type=normalize_event_type(event_type),
        actor_username_snapshot=actor.username if actor is not None else None,
        actor_full_name_snapshot=actor.full_name if actor is not None else None,
        task_title_snapshot=task.title if task is not None else None,
        message=message,
        metadata_json=metadata,
    )

    db.add(activity_log)

    if commit:
        db.commit()
        db.refresh(activity_log)

    return activity_log


def get_accessible_project_for_activity(
    db: Session,
    project_id: int,
    current_user: User,
) -> Project | None:
    project = db.get(Project, project_id)

    if project is None:
        return None

    if project.project_type == "personal":
        if project.created_by != current_user.user_id:
            return None

        return project

    membership_stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == current_user.user_id,
    )

    membership = db.execute(membership_stmt).scalars().first()

    if membership is None:
        return None

    return project


def get_project_activity_logs(
    db: Session,
    project: Project,
    event_type: ActivityLogEventType | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ActivityLog]:
    stmt = select(ActivityLog).where(
        ActivityLog.project_id == project.project_id,
    )

    if event_type is not None:
        stmt = stmt.where(ActivityLog.event_type == event_type.value)

    stmt = (
        stmt.order_by(ActivityLog.created_at.desc(), ActivityLog.activity_id.desc())
        .limit(limit)
        .offset(offset)
    )

    return list(db.execute(stmt).scalars().all())


def build_activity_log_response(activity_log: ActivityLog) -> ActivityLogResponse:
    return ActivityLogResponse(
        activity_id=activity_log.activity_id,
        project_id=activity_log.project_id,
        task_id=activity_log.task_id,
        actor_id=activity_log.actor_id,
        event_type=ActivityLogEventType(activity_log.event_type),
        actor_username_snapshot=activity_log.actor_username_snapshot,
        actor_full_name_snapshot=activity_log.actor_full_name_snapshot,
        task_title_snapshot=activity_log.task_title_snapshot,
        message=activity_log.message,
        metadata=activity_log.metadata_json,
        created_at=activity_log.created_at,
    )