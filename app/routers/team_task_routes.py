from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.task_schema import (
    TaskDeleteResponse,
    TaskPriority,
    TaskResponse,
    TaskStatus,
    TeamTaskCreate,
    TeamTaskUpdate,
)
from app.services.project_service import (
    can_manage_project,
    get_project_membership,
)
from app.services.task_service import (
    create_task_for_team_project,
    delete_task_for_team_project,
    get_task_for_team_project_by_id,
    get_tasks_for_team_project,
    get_team_project_for_tasks,
    update_task_for_team_project,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

PROJECT_NOT_FOUND = "Project not found"
TASK_NOT_FOUND = "Task not found"
NOT_ALLOWED = "You are not allowed to perform this action"
ASSIGNEE_NOT_PROJECT_MEMBER = "Assigned user must be a member of this project"

router = APIRouter(
    prefix="/teams/{team_id}/projects/{project_id}/tasks",
    tags=["Team Project Tasks"],
)


def require_team_project_access(
    db: Session,
    team_id: int,
    project_id: int,
    current_user: User,
) -> tuple[Project, ProjectMember]:
    project = get_team_project_for_tasks(
        db=db,
        team_id=team_id,
        project_id=project_id,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    membership = get_project_membership(
        db=db,
        project_id=project_id,
        user_id=current_user.user_id,
    )

    if membership is None:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    return project, membership


@router.post(
    "",
    response_model=TaskResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def create_team_task(
    team_id: int,
    project_id: int,
    task_data: TeamTaskCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    project, membership = require_team_project_access(
        db=db,
        team_id=team_id,
        project_id=project_id,
        current_user=current_user,
    )

    if not can_manage_project(membership):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    assigned_to = task_data.assigned_to or current_user.user_id

    assignee_membership = get_project_membership(
        db=db,
        project_id=project_id,
        user_id=assigned_to,
    )

    if assignee_membership is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=ASSIGNEE_NOT_PROJECT_MEMBER,
        )

    return create_task_for_team_project(
        db=db,
        project=project,
        task_data=task_data,
        current_user=current_user,
        assigned_to=assigned_to,
    )


@router.get(
    "",
    response_model=list[TaskResponse],
)
def list_team_tasks(
    team_id: int,
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    assigned_to: int | None = None,
):
    project, _membership = require_team_project_access(
        db=db,
        team_id=team_id,
        project_id=project_id,
        current_user=current_user,
    )

    return get_tasks_for_team_project(
        db=db,
        project=project,
        status=status,
        priority=priority,
        assigned_to=assigned_to,
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
)
def get_team_task(
    team_id: int,
    project_id: int,
    task_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project, _membership = require_team_project_access(
        db=db,
        team_id=team_id,
        project_id=project_id,
        current_user=current_user,
    )

    task = get_task_for_team_project_by_id(
        db=db,
        project=project,
        task_id=task_id,
    )

    if task is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=TASK_NOT_FOUND,
        )

    return task


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
)
def update_team_task(
    team_id: int,
    project_id: int,
    task_id: int,
    task_data: TeamTaskUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    project, membership = require_team_project_access(
        db=db,
        team_id=team_id,
        project_id=project_id,
        current_user=current_user,
    )

    task = get_task_for_team_project_by_id(
        db=db,
        project=project,
        task_id=task_id,
    )

    if task is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=TASK_NOT_FOUND,
        )

    is_manager = can_manage_project(membership)

    if not is_manager:
        if task.assigned_to != current_user.user_id:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail=NOT_ALLOWED,
            )

        update_data = task_data.model_dump(exclude_unset=True)
        allowed_member_fields = {"status", "actual_hours"}
        forbidden_fields = set(update_data.keys()) - allowed_member_fields

        if forbidden_fields:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Project members can only update status and actual_hours for their own tasks",
            )

    if is_manager and task_data.assigned_to is not None:
        assignee_membership = get_project_membership(
            db=db,
            project_id=project_id,
            user_id=task_data.assigned_to,
        )

        if assignee_membership is None:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=ASSIGNEE_NOT_PROJECT_MEMBER,
            )

    return update_task_for_team_project(
        db=db,
        task=task,
        task_data=task_data,
    )


@router.delete(
    "/{task_id}",
    response_model=TaskDeleteResponse,
)
def delete_team_task(
    team_id: int,
    project_id: int,
    task_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project, membership = require_team_project_access(
        db=db,
        team_id=team_id,
        project_id=project_id,
        current_user=current_user,
    )

    if not can_manage_project(membership):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    task = get_task_for_team_project_by_id(
        db=db,
        project=project,
        task_id=task_id,
    )

    if task is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=TASK_NOT_FOUND,
        )

    delete_task_for_team_project(
        db=db,
        task=task,
    )

    return TaskDeleteResponse(
        message="Team project task deleted successfully.",
    )