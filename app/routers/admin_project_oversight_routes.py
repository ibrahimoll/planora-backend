from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_admin_user
from app.models.user import User
from app.schemas.admin_project_oversight_schema import (
    AdminProjectDetailResponse,
    AdminProjectListResponse,
    AdminProjectStatusUpdateRequest,
    AdminProjectStatusUpdateResponse,
)
from app.services.admin_project_oversight_service import (
    get_admin_project_detail,
    get_admin_projects,
    update_project_status_by_admin,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentAdmin = Annotated[User, Depends(get_current_admin_user)]

ProjectTypeFilter = Literal["personal", "team"]
ProjectStatusFilter = Literal[
    "not_started",
    "in_progress",
    "completed",
    "on_hold",
    "cancelled",
]

router = APIRouter(
    prefix="/admin/projects",
    tags=["Admin Project Oversight"],
)


@router.get(
    "",
    response_model=AdminProjectListResponse,
)
def read_admin_projects(
    db: DBSession,
    current_admin: CurrentAdmin,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    project_type: ProjectTypeFilter | None = None,
    status_filter: Annotated[
        ProjectStatusFilter | None,
        Query(alias="status"),
    ] = None,
    owner_id: int | None = None,
    team_id: int | None = None,
    search: str | None = None,
):
    return get_admin_projects(
        db=db,
        limit=limit,
        offset=offset,
        project_type=project_type,
        status_filter=status_filter,
        owner_id=owner_id,
        team_id=team_id,
        search=search,
    )


@router.get(
    "/{project_id}",
    response_model=AdminProjectDetailResponse,
)
def read_admin_project_detail(
    project_id: int,
    db: DBSession,
    current_admin: CurrentAdmin,
):
    return get_admin_project_detail(
        db=db,
        project_id=project_id,
    )


@router.patch(
    "/{project_id}/status",
    response_model=AdminProjectStatusUpdateResponse,
)
def update_admin_project_status(
    project_id: int,
    payload: AdminProjectStatusUpdateRequest,
    db: DBSession,
    current_admin: CurrentAdmin,
):
    return update_project_status_by_admin(
        db=db,
        admin=current_admin,
        project_id=project_id,
        new_status=payload.status,
    )
