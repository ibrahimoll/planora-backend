from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_admin_user
from app.models.user import User
from app.schemas.admin_task_oversight_schema import (
    AdminTaskActionResponse,
    AdminTaskAssignmentUpdateRequest,
    AdminTaskDetailResponse,
    AdminTaskStatusUpdateRequest,
    AdminTaskSummaryResponse,
)
from app.services.admin_task_oversight_service import (
    get_admin_task_detail,
    get_admin_tasks,
    update_task_assignment_by_admin,
    update_task_status_by_admin,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentAdmin = Annotated[User, Depends(get_current_admin_user)]

TaskStatusFilter = Literal["todo", "in_progress", "completed", "blocked"]
TaskPriorityFilter = Literal["low", "medium", "high"]

router = APIRouter(
    prefix="/admin/tasks",
    tags=["Admin Task Oversight"],
)


@router.get("", response_model=list[AdminTaskSummaryResponse])
def read_admin_tasks(
    db: DBSession,
    current_admin: CurrentAdmin,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    status_filter: Annotated[TaskStatusFilter | None, Query(alias="status")] = None,
    priority: TaskPriorityFilter | None = None,
    project_id: int | None = None,
    assigned_to: int | None = None,
    created_by: int | None = None,
    overdue: bool | None = None,
    unassigned: bool | None = None,
    search: str | None = None,
):
    return get_admin_tasks(
        db=db,
        limit=limit,
        offset=offset,
        status_filter=status_filter,
        priority=priority,
        project_id=project_id,
        assigned_to=assigned_to,
        created_by=created_by,
        overdue=overdue,
        unassigned=unassigned,
        search=search,
    )


@router.get("/{task_id}", response_model=AdminTaskDetailResponse)
def read_admin_task_detail(
    task_id: int,
    db: DBSession,
    current_admin: CurrentAdmin,
):
    return get_admin_task_detail(db=db, task_id=task_id)


@router.patch("/{task_id}/status", response_model=AdminTaskActionResponse)
def update_admin_task_status(
    task_id: int,
    payload: AdminTaskStatusUpdateRequest,
    db: DBSession,
    current_admin: CurrentAdmin,
):
    return update_task_status_by_admin(
        db=db,
        admin=current_admin,
        task_id=task_id,
        new_status=payload.status,
    )


@router.patch("/{task_id}/assignment", response_model=AdminTaskActionResponse)
def update_admin_task_assignment(
    task_id: int,
    payload: AdminTaskAssignmentUpdateRequest,
    db: DBSession,
    current_admin: CurrentAdmin,
):
    return update_task_assignment_by_admin(
        db=db,
        admin=current_admin,
        task_id=task_id,
        assigned_to=payload.assigned_to,
    )
