from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.project import Project
from app.models.user import User
from app.schemas.smart_schedule_schema import (
    SmartSchedulePreviewResponse,
    SmartScheduleRequest,
    SmartScheduleResponse,
)
from app.services.project_service import (
    can_manage_project,
    get_my_personal_project_by_id,
    get_project_membership,
    get_team_project_by_id,
)
from app.services.smart_schedule_service import (
    create_smart_schedule_for_project,
    get_smart_schedules_for_project,
    preview_smart_schedule_for_project,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

PROJECT_NOT_FOUND = "Project not found"
NOT_ALLOWED = "You are not allowed to perform this action"

router = APIRouter(
    tags=["Smart Schedules"],
)


def _get_personal_project_or_404(
    db: Session,
    project_id: int,
    current_user: User,
) -> Project:
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


def _get_team_project_or_404(
    db: Session,
    team_id: int,
    project_id: int,
) -> Project:
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


def _require_team_project_member(
    db: Session,
    project_id: int,
    current_user: User,
) -> None:
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


def _require_team_project_manager(
    db: Session,
    project_id: int,
    current_user: User,
) -> None:
    membership = get_project_membership(
        db=db,
        project_id=project_id,
        user_id=current_user.user_id,
    )

    if membership is None or not can_manage_project(membership):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )


@router.post(
    "/projects/{project_id}/smart-schedules/preview",
    response_model=SmartSchedulePreviewResponse,
)
def preview_personal_project_smart_schedule(
    project_id: int,
    schedule_request: SmartScheduleRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    project = _get_personal_project_or_404(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    return preview_smart_schedule_for_project(
        db=db,
        project=project,
        schedule_request=schedule_request,
    )


@router.post(
    "/projects/{project_id}/smart-schedules",
    response_model=SmartScheduleResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def generate_personal_project_smart_schedule(
    project_id: int,
    schedule_request: SmartScheduleRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    project = _get_personal_project_or_404(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    return create_smart_schedule_for_project(
        db=db,
        project=project,
        current_user=current_user,
        schedule_request=schedule_request,
    )


@router.get(
    "/projects/{project_id}/smart-schedules",
    response_model=list[SmartScheduleResponse],
)
def list_personal_project_smart_schedules(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = _get_personal_project_or_404(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    return get_smart_schedules_for_project(
        db=db,
        project=project,
    )


@router.post(
    "/teams/{team_id}/projects/{project_id}/smart-schedules/preview",
    response_model=SmartSchedulePreviewResponse,
)
def preview_team_project_smart_schedule(
    team_id: int,
    project_id: int,
    schedule_request: SmartScheduleRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    project = _get_team_project_or_404(
        db=db,
        team_id=team_id,
        project_id=project_id,
    )

    _require_team_project_member(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    return preview_smart_schedule_for_project(
        db=db,
        project=project,
        schedule_request=schedule_request,
    )


@router.post(
    "/teams/{team_id}/projects/{project_id}/smart-schedules",
    response_model=SmartScheduleResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def generate_team_project_smart_schedule(
    team_id: int,
    project_id: int,
    schedule_request: SmartScheduleRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    project = _get_team_project_or_404(
        db=db,
        team_id=team_id,
        project_id=project_id,
    )

    _require_team_project_manager(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    return create_smart_schedule_for_project(
        db=db,
        project=project,
        current_user=current_user,
        schedule_request=schedule_request,
    )


@router.get(
    "/teams/{team_id}/projects/{project_id}/smart-schedules",
    response_model=list[SmartScheduleResponse],
)
def list_team_project_smart_schedules(
    team_id: int,
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = _get_team_project_or_404(
        db=db,
        team_id=team_id,
        project_id=project_id,
    )

    _require_team_project_member(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    return get_smart_schedules_for_project(
        db=db,
        project=project,
    )