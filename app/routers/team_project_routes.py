from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.project_schema import (
    ProjectDeleteResponse,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectStatus,
    ProjectUpdate,
    TeamProjectCreate,
)
from app.services.project_service import (
    can_manage_project,
    create_team_project,
    delete_team_project,
    get_project_members,
    get_project_membership,
    get_team_project_by_id,
    get_team_projects,
    is_project_owner,
    update_team_project,
)
from app.services.team_service import (
    can_manage_team,
    get_team_by_id,
    get_team_membership,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

TEAM_NOT_FOUND = "Team not found"
PROJECT_NOT_FOUND = "Project not found"
NOT_ALLOWED = "You are not allowed to perform this action"

router = APIRouter(
    prefix="/teams/{team_id}/projects",
    tags=["Team Projects"],
)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def create_project_for_team(
    team_id: int,
    project_data: TeamProjectCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    team = get_team_by_id(
        db=db,
        team_id=team_id,
    )

    if team is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=TEAM_NOT_FOUND,
        )

    membership = get_team_membership(
        db=db,
        team_id=team_id,
        user_id=current_user.user_id,
    )

    if membership is None or not can_manage_team(membership):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    return create_team_project(
        db=db,
        team=team,
        project_data=project_data,
        current_user=current_user,
    )


@router.get(
    "",
    response_model=list[ProjectResponse],
)
def list_team_projects(
    team_id: int,
    db: DBSession,
    current_user: CurrentUser,
    status: ProjectStatus | None = None,
):
    team = get_team_by_id(
        db=db,
        team_id=team_id,
    )

    if team is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=TEAM_NOT_FOUND,
        )

    membership = get_team_membership(
        db=db,
        team_id=team_id,
        user_id=current_user.user_id,
    )

    if membership is None:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    return get_team_projects(
        db=db,
        team_id=team_id,
        status=status,
    )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
)
def get_team_project(
    team_id: int,
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    membership = get_team_membership(
        db=db,
        team_id=team_id,
        user_id=current_user.user_id,
    )

    if membership is None:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    project = get_team_project_by_id(
        db=db,
        team_id=team_id,
        project_id=project_id,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    return project


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
)
def update_existing_team_project(
    team_id: int,
    project_id: int,
    project_data: ProjectUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_team_project_by_id(
        db=db,
        team_id=team_id,
        project_id=project_id,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    project_membership = get_project_membership(
        db=db,
        project_id=project_id,
        user_id=current_user.user_id,
    )

    if project_membership is None or not can_manage_project(project_membership):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    return update_team_project(
        db=db,
        project=project,
        project_data=project_data,
    )


@router.delete(
    "/{project_id}",
    response_model=ProjectDeleteResponse,
)
def delete_existing_team_project(
    team_id: int,
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_team_project_by_id(
        db=db,
        team_id=team_id,
        project_id=project_id,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    project_membership = get_project_membership(
        db=db,
        project_id=project_id,
        user_id=current_user.user_id,
    )

    if project_membership is None or not is_project_owner(project_membership):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    delete_team_project(
        db=db,
        project=project,
    )

    return ProjectDeleteResponse(
        message="Team project deleted successfully.",
    )


@router.get(
    "/{project_id}/members",
    response_model=list[ProjectMemberResponse],
)
def list_project_members(
    team_id: int,
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    team_membership = get_team_membership(
        db=db,
        team_id=team_id,
        user_id=current_user.user_id,
    )

    if team_membership is None:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    project = get_team_project_by_id(
        db=db,
        team_id=team_id,
        project_id=project_id,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    return get_project_members(
        db=db,
        project_id=project_id,
    )