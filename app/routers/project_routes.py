from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.project_schema import (
    ProjectCreate,
    ProjectDeleteResponse,
    ProjectResponse,
    ProjectStatus,
    ProjectUpdate,
)
from app.services.project_service import (
    create_personal_project,
    delete_my_personal_project,
    get_my_personal_project_by_id,
    get_my_personal_projects,
    update_my_personal_project,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

PROJECT_NOT_FOUND = "Project not found"

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def create_project(
    project_data: ProjectCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    return create_personal_project(
        db=db,
        project_data=project_data,
        current_user=current_user,
    )


@router.get(
    "",
    response_model=list[ProjectResponse],
)
def get_projects(
    db: DBSession,
    current_user: CurrentUser,
    status: ProjectStatus | None = None,
):
    return get_my_personal_projects(
        db=db,
        current_user=current_user,
        status=status,
    )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
)
def get_project(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_my_personal_project_by_id(
        db=db,
        project_id=project_id,
        current_user=current_user,
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
def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_my_personal_project_by_id(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    return update_my_personal_project(
        db=db,
        project=project,
        project_data=project_data,
        current_user=current_user,
    )


@router.delete(
    "/{project_id}",
    response_model=ProjectDeleteResponse,
)
def delete_project(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_my_personal_project_by_id(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    delete_my_personal_project(
        db=db,
        project=project,
    )

    return ProjectDeleteResponse(
        message="Project deleted successfully.",
    )