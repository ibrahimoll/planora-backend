from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.subtask import Subtask
from app.models.task import Task
from app.models.user import User
from app.schemas.task_schema import (
    SubtaskCompletionUpdate,
    SubtaskCreate,
    SubtaskDeleteResponse,
    SubtaskResponse,
    SubtaskUpdate,
)
from app.services.project_service import can_manage_project, get_project_membership
from app.services.subtask_service import (
    create_subtask,
    delete_subtask,
    get_subtask,
    list_subtasks,
    set_subtask_completion,
    update_subtask,
)
from app.services.task_service import (
    can_manage_personal_project_tasks,
    get_my_personal_project_for_tasks,
    get_task_for_personal_project_by_id,
    get_task_for_team_project_by_id,
    get_team_project_for_tasks,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

PROJECT_NOT_FOUND = "Project not found"
TASK_NOT_FOUND = "Task not found"
SUBTASK_NOT_FOUND = "Subtask not found"
NOT_ALLOWED = "You are not allowed to perform this action"

personal_router = APIRouter(
    prefix="/projects/{project_id}/tasks/{task_id}/subtasks",
    tags=["Subtasks"],
)

team_router = APIRouter(
    prefix="/teams/{team_id}/projects/{project_id}/tasks/{task_id}/subtasks",
    tags=["Team Project Subtasks"],
)


def _get_personal_task(
    db: Session,
    project_id: int,
    task_id: int,
    current_user: User,
) -> tuple[Project, Task]:
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

    return project, task


def _get_team_task(
    db: Session,
    team_id: int,
    project_id: int,
    task_id: int,
    current_user: User,
) -> tuple[Project, ProjectMember, Task]:
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

    return project, membership, task


def _require_personal_mutation_access(
    db: Session,
    project: Project,
    task: Task,
    current_user: User,
) -> None:
    if can_manage_personal_project_tasks(db, project, current_user):
        return

    if task.assigned_to != current_user.user_id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )


def _require_team_mutation_access(
    membership: ProjectMember,
    task: Task,
    current_user: User,
) -> None:
    if can_manage_project(membership):
        return

    if task.assigned_to != current_user.user_id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )


def _get_subtask_or_404(
    db: Session,
    task: Task,
    subtask_id: int,
) -> Subtask:
    subtask = get_subtask(db=db, task=task, subtask_id=subtask_id)
    if subtask is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=SUBTASK_NOT_FOUND,
        )
    return subtask


@personal_router.get("", response_model=list[SubtaskResponse])
def list_personal_subtasks(
    project_id: int,
    task_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    _project, task = _get_personal_task(db, project_id, task_id, current_user)
    return list_subtasks(db=db, task=task)


@personal_router.post(
    "",
    response_model=SubtaskResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def create_personal_subtask(
    project_id: int,
    task_id: int,
    subtask_data: SubtaskCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    project, task = _get_personal_task(db, project_id, task_id, current_user)
    _require_personal_mutation_access(db, project, task, current_user)
    return create_subtask(db, task, subtask_data, current_user)


@personal_router.patch("/{subtask_id}", response_model=SubtaskResponse)
def update_personal_subtask(
    project_id: int,
    task_id: int,
    subtask_id: int,
    subtask_data: SubtaskUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    project, task = _get_personal_task(db, project_id, task_id, current_user)
    _require_personal_mutation_access(db, project, task, current_user)
    subtask = _get_subtask_or_404(db, task, subtask_id)
    return update_subtask(db, task, subtask, subtask_data)


@personal_router.patch("/{subtask_id}/complete", response_model=SubtaskResponse)
def complete_personal_subtask(
    project_id: int,
    task_id: int,
    subtask_id: int,
    completion_data: SubtaskCompletionUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    project, task = _get_personal_task(db, project_id, task_id, current_user)
    _require_personal_mutation_access(db, project, task, current_user)
    subtask = _get_subtask_or_404(db, task, subtask_id)
    return set_subtask_completion(db, task, subtask, completion_data)


@personal_router.delete("/{subtask_id}", response_model=SubtaskDeleteResponse)
def delete_personal_subtask(
    project_id: int,
    task_id: int,
    subtask_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project, task = _get_personal_task(db, project_id, task_id, current_user)
    _require_personal_mutation_access(db, project, task, current_user)
    subtask = _get_subtask_or_404(db, task, subtask_id)
    delete_subtask(db, task, subtask)
    return SubtaskDeleteResponse(message="Subtask deleted successfully.")


@team_router.get("", response_model=list[SubtaskResponse])
def list_team_subtasks(
    team_id: int,
    project_id: int,
    task_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    _project, _membership, task = _get_team_task(
        db, team_id, project_id, task_id, current_user
    )
    return list_subtasks(db=db, task=task)


@team_router.post(
    "",
    response_model=SubtaskResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def create_team_subtask(
    team_id: int,
    project_id: int,
    task_id: int,
    subtask_data: SubtaskCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    _project, membership, task = _get_team_task(
        db, team_id, project_id, task_id, current_user
    )
    _require_team_mutation_access(membership, task, current_user)
    return create_subtask(db, task, subtask_data, current_user)


@team_router.patch("/{subtask_id}", response_model=SubtaskResponse)
def update_team_subtask(
    team_id: int,
    project_id: int,
    task_id: int,
    subtask_id: int,
    subtask_data: SubtaskUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    _project, membership, task = _get_team_task(
        db, team_id, project_id, task_id, current_user
    )
    _require_team_mutation_access(membership, task, current_user)
    subtask = _get_subtask_or_404(db, task, subtask_id)
    return update_subtask(db, task, subtask, subtask_data)


@team_router.patch("/{subtask_id}/complete", response_model=SubtaskResponse)
def complete_team_subtask(
    team_id: int,
    project_id: int,
    task_id: int,
    subtask_id: int,
    completion_data: SubtaskCompletionUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    _project, membership, task = _get_team_task(
        db, team_id, project_id, task_id, current_user
    )
    _require_team_mutation_access(membership, task, current_user)
    subtask = _get_subtask_or_404(db, task, subtask_id)
    return set_subtask_completion(db, task, subtask, completion_data)


@team_router.delete("/{subtask_id}", response_model=SubtaskDeleteResponse)
def delete_team_subtask(
    team_id: int,
    project_id: int,
    task_id: int,
    subtask_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    _project, membership, task = _get_team_task(
        db, team_id, project_id, task_id, current_user
    )
    _require_team_mutation_access(membership, task, current_user)
    subtask = _get_subtask_or_404(db, task, subtask_id)
    delete_subtask(db, task, subtask)
    return SubtaskDeleteResponse(message="Subtask deleted successfully.")
