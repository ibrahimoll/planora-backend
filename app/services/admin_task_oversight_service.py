from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.admin_log import AdminLog
from app.models.attachment import Attachment
from app.models.comment import Comment
from app.models.project import Project
from app.models.task import Task
from app.models.team import Team
from app.models.user import User
from app.schemas.admin_task_oversight_schema import (
    AdminTaskActionResponse,
    AdminTaskDetailResponse,
    AdminTaskListResponse,
    AdminTaskProjectResponse,
    AdminTaskSummaryResponse,
    AdminTaskUserResponse,
)


def _count_query(db: Session, stmt: Select[tuple[int]]) -> int:
    value = db.scalar(stmt)
    return int(value or 0)


def _count_where(db: Session, model: type, *conditions: Any) -> int:
    stmt = select(func.count()).select_from(model)
    if conditions:
        stmt = stmt.where(*conditions)
    return _count_query(db, stmt)


def _count_select(db: Session, stmt: Select[Any]) -> int:
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    return _count_query(db, count_stmt)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _get_task_or_404(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return task


def _get_project_or_500(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Task parent project is missing.",
        )
    return project


def _get_user_response(db: Session, user_id: int | None) -> AdminTaskUserResponse | None:
    if user_id is None:
        return None
    user = db.get(User, user_id)
    if user is None:
        return None
    return AdminTaskUserResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
    )


def _get_project_response(db: Session, project: Project) -> AdminTaskProjectResponse:
    team_name: str | None = None
    if project.team_id is not None:
        team = db.get(Team, project.team_id)
        if team is not None:
            team_name = team.name

    return AdminTaskProjectResponse(
        project_id=project.project_id,
        title=project.title,
        status=project.status,
        project_type=project.project_type,
        team_id=project.team_id,
        team_name=team_name,
    )


def _is_task_overdue(task: Task) -> bool:
    if task.status == "completed" or task.due_date is None:
        return False
    return task.due_date < _now_utc()


def _build_task_summary(db: Session, task: Task) -> AdminTaskSummaryResponse:
    project = _get_project_or_500(db=db, project_id=task.project_id)
    creator = _get_user_response(db=db, user_id=task.created_by)
    if creator is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Task creator is missing.",
        )

    return AdminTaskSummaryResponse(
        task_id=task.task_id,
        title=task.title,
        priority=task.priority,
        status=task.status,
        due_date=task.due_date,
        completed_at=task.completed_at,
        created_at=task.created_at,
        estimated_hours=float(task.estimated_hours) if task.estimated_hours is not None else None,
        actual_hours=float(task.actual_hours) if task.actual_hours is not None else None,
        is_overdue=_is_task_overdue(task),
        project=_get_project_response(db=db, project=project),
        assignee=_get_user_response(db=db, user_id=task.assigned_to),
        creator=creator,
    )


def _build_task_detail(db: Session, task: Task) -> AdminTaskDetailResponse:
    summary = _build_task_summary(db=db, task=task)
    return AdminTaskDetailResponse(
        task_id=summary.task_id,
        title=summary.title,
        description=task.description,
        priority=summary.priority,
        status=summary.status,
        due_date=summary.due_date,
        completed_at=summary.completed_at,
        created_at=summary.created_at,
        estimated_hours=summary.estimated_hours,
        actual_hours=summary.actual_hours,
        is_overdue=summary.is_overdue,
        project=summary.project,
        assignee=summary.assignee,
        creator=summary.creator,
        comments_count=_count_where(db, Comment, Comment.task_id == task.task_id),
        attachments_count=_count_where(db, Attachment, Attachment.task_id == task.task_id),
    )


def get_admin_tasks(
    db: Session,
    limit: int,
    offset: int,
    status_filter: str | None = None,
    priority: str | None = None,
    project_id: int | None = None,
    assigned_to: int | None = None,
    created_by: int | None = None,
    overdue: bool | None = None,
    unassigned: bool | None = None,
    search: str | None = None,
) -> AdminTaskListResponse:
    now = _now_utc()
    stmt = select(Task)

    if status_filter is not None:
        stmt = stmt.where(Task.status == status_filter)
    if priority is not None:
        stmt = stmt.where(Task.priority == priority)
    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    if assigned_to is not None:
        stmt = stmt.where(Task.assigned_to == assigned_to)
    if created_by is not None:
        stmt = stmt.where(Task.created_by == created_by)
    if overdue is True:
        stmt = stmt.where(
            Task.status != "completed",
            Task.due_date.is_not(None),
            Task.due_date < now,
        )
    if overdue is False:
        stmt = stmt.where(
            or_(
                Task.status == "completed",
                Task.due_date.is_(None),
                Task.due_date >= now,
            )
        )
    if unassigned is True:
        stmt = stmt.where(Task.assigned_to.is_(None))
    if unassigned is False:
        stmt = stmt.where(Task.assigned_to.is_not(None))
    if search is not None and search.strip():
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Task.title.ilike(pattern),
                Task.description.ilike(pattern),
            )
        )

    total = _count_select(db, stmt)

    tasks = list(
        db.execute(
            stmt.order_by(Task.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        .scalars()
        .all()
    )

    return AdminTaskListResponse(
        items=[_build_task_summary(db=db, task=task) for task in tasks],
        total=total,
        limit=limit,
        offset=offset,
    )


def get_admin_task_detail(db: Session, task_id: int) -> AdminTaskDetailResponse:
    task = _get_task_or_404(db=db, task_id=task_id)
    return _build_task_detail(db=db, task=task)


def update_task_status_by_admin(db: Session, admin: User, task_id: int, new_status: str) -> AdminTaskActionResponse:
    task = _get_task_or_404(db=db, task_id=task_id)
    old_status = task.status
    task.status = new_status
    task.completed_at = _now_utc() if new_status == "completed" else None

    log = AdminLog(
        admin_id=admin.user_id,
        target_user_id=task.assigned_to,
        action=(
            f"changed_task_status:task_id={task.task_id}:"
            f"old_status={old_status}:new_status={new_status}"
        ),
    )
    db.add(log)
    db.commit()
    db.refresh(task)
    db.refresh(log)

    return AdminTaskActionResponse(
        message="Task status updated successfully.",
        task=_build_task_detail(db=db, task=task),
        admin_log_id=log.log_id,
    )


def update_task_assignment_by_admin(
    db: Session,
    admin: User,
    task_id: int,
    assigned_to: int | None,
) -> AdminTaskActionResponse:
    task = _get_task_or_404(db=db, task_id=task_id)
    old_assigned_to = task.assigned_to

    if assigned_to is not None:
        user = db.get(User, assigned_to)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned user not found.")
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign task to an inactive user.",
            )

    task.assigned_to = assigned_to
    log = AdminLog(
        admin_id=admin.user_id,
        target_user_id=assigned_to,
        action=(
            f"changed_task_assignment:task_id={task.task_id}:"
            f"old_assigned_to={old_assigned_to}:new_assigned_to={assigned_to}"
        ),
    )
    db.add(log)
    db.commit()
    db.refresh(task)
    db.refresh(log)

    return AdminTaskActionResponse(
        message="Task assignment updated successfully.",
        task=_build_task_detail(db=db, task=task),
        admin_log_id=log.log_id,
    )
