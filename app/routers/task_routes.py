from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.task_schema import (
    TaskCreate,
    TaskDeleteResponse,
    TaskPriority,
    TaskResponse,
    TaskStatus,
    TaskUpdate,
)
from app.services.task_service import (
    create_task_for_personal_project,
    delete_task_for_personal_project,
    get_my_personal_project_for_tasks,
    get_task_for_personal_project_by_id,
    get_tasks_for_personal_project,
    update_task_for_personal_project,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

PROJECT_NOT_FOUND = "Project not found"
TASK_NOT_FOUND = "Task not found"

router = APIRouter(
    prefix="/projects/{project_id}/tasks",
    tags=["Tasks"],
)


@router.post(
    "",
    response_model=TaskResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def create_task(
    project_id: int,
    task_data: TaskCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_my_personal_project_for_tasks(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    return create_task_for_personal_project(
        db=db,
        project=project,
        task_data=task_data,
        current_user=current_user,
    )


@router.get(
    "",
    response_model=list[TaskResponse],
)
def get_tasks(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
):
    project = get_my_personal_project_for_tasks(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    return get_tasks_for_personal_project(
        db=db,
        project=project,
        status=status,
        priority=priority,
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
)
def get_task(
    project_id: int,
    task_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_my_personal_project_for_tasks(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    task = get_task_for_personal_project_by_id(
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
def update_task(
    project_id: int,
    task_id: int,
    task_data: TaskUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_my_personal_project_for_tasks(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    task = get_task_for_personal_project_by_id(
        db=db,
        project=project,
        task_id=task_id,
    )

    if task is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=TASK_NOT_FOUND,
        )

    return update_task_for_personal_project(
        db=db,
        task=task,
        task_data=task_data,
    )


@router.delete(
    "/{task_id}",
    response_model=TaskDeleteResponse,
)
def delete_task(
    project_id: int,
    task_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_my_personal_project_for_tasks(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    task = get_task_for_personal_project_by_id(
        db=db,
        project=project,
        task_id=task_id,
    )

    if task is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=TASK_NOT_FOUND,
        )

    delete_task_for_personal_project(
        db=db,
        task=task,
    )

    return TaskDeleteResponse(
        message="Task deleted successfully.",
    )