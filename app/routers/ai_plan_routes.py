from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.ai_plan_schema import AIPlanGenerateRequest, AIPlanResponse
from app.services.ai_plan_service import (
    create_ai_plan_for_project,
    get_ai_plans_for_project,
)
from app.services.project_service import (
    can_manage_project,
    get_my_personal_project_by_id,
    get_project_membership,
    get_team_project_by_id,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

PROJECT_NOT_FOUND = "Project not found"
NOT_ALLOWED = "You are not allowed to perform this action"

router = APIRouter(
    tags=["AI Plans"],
)


@router.post(
    "/projects/{project_id}/ai-plans",
    response_model=AIPlanResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def generate_personal_project_ai_plan(
    project_id: int,
    plan_data: AIPlanGenerateRequest,
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

    return create_ai_plan_for_project(
        db=db,
        project=project,
        current_user=current_user,
        plan_data=plan_data,
    )


@router.get(
    "/projects/{project_id}/ai-plans",
    response_model=list[AIPlanResponse],
)
def list_personal_project_ai_plans(
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

    return get_ai_plans_for_project(
        db=db,
        project=project,
    )


@router.post(
    "/teams/{team_id}/projects/{project_id}/ai-plans",
    response_model=AIPlanResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def generate_team_project_ai_plan(
    team_id: int,
    project_id: int,
    plan_data: AIPlanGenerateRequest,
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

    return create_ai_plan_for_project(
        db=db,
        project=project,
        current_user=current_user,
        plan_data=plan_data,
    )


@router.get(
    "/teams/{team_id}/projects/{project_id}/ai-plans",
    response_model=list[AIPlanResponse],
)
def list_team_project_ai_plans(
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

    return get_ai_plans_for_project(
        db=db,
        project=project,
    )