from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.ai_plan_schema import (
    AIPlanAcceptPreviewRequest,
    AIPlanAcceptPreviewResponse,
    AIPlanGenerateRequest,
    AIPlanGenerateResponse,
    AIPlanPreviewRequest,
    AIPlanPreviewResponse,
    AIPlanResponse,
)
from app.schemas.project_schema import ProjectCreate, TeamProjectCreate
from app.services.ai_plan_service import (
    create_ai_plan_from_accepted_preview,
    create_ai_plan_generation_response,
    create_ai_plan_for_project,
    create_ai_plan_preview,
    get_ai_plans_for_project,
)
from app.services.project_service import (
    can_manage_project,
    create_personal_project,
    create_team_project,
    get_my_personal_project_by_id,
    get_project_membership,
    get_team_project_by_id,
)
from app.services.team_service import can_manage_team, get_team_by_id, get_team_membership

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

PROJECT_NOT_FOUND = "Project not found"
NOT_ALLOWED = "You are not allowed to perform this action"
TEAM_NOT_FOUND = "Team not found"
logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["AI Plans"],
)


def _truncate_description(value: str | None) -> str | None:
    if value is None or len(value) <= 5000:
        return value

    return f"{value[:4997].rstrip()}..."


@router.post(
    "/ai-plans/preview-from-idea",
    response_model=AIPlanPreviewResponse,
)
def preview_ai_plan_from_idea(
    preview_data: AIPlanPreviewRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    logger.info(
        "AI Planner preview route entered. user_id=%s project_type=%s team_id_present=%s preferred_task_count=%s",
        current_user.user_id,
        preview_data.project_type.value,
        preview_data.team_id is not None,
        preview_data.preferred_task_count,
    )

    if preview_data.project_type.value == "team":
        if preview_data.team_id is None:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Team id is required for team project previews",
            )

        team = get_team_by_id(
            db=db,
            team_id=preview_data.team_id,
        )

        if team is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=TEAM_NOT_FOUND,
            )

        membership = get_team_membership(
            db=db,
            team_id=preview_data.team_id,
            user_id=current_user.user_id,
        )

        if membership is None:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail=NOT_ALLOWED,
            )

    preview = create_ai_plan_preview(
        preview_data=preview_data,
        current_user=current_user,
    )
    logger.info(
        "AI Planner preview route returned. user_id=%s ai_generation_status=%s task_count=%s",
        current_user.user_id,
        preview.ai_generation_status,
        len(preview.tasks),
    )
    return preview


@router.post(
    "/ai-plans/accept-preview",
    response_model=AIPlanAcceptPreviewResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def accept_ai_plan_preview(
    accept_data: AIPlanAcceptPreviewRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    preview = accept_data.preview

    if preview.project_type.value == "team":
        if preview.team_id is None:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Team id is required for team project previews",
            )

        team = get_team_by_id(
            db=db,
            team_id=preview.team_id,
        )

        if team is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=TEAM_NOT_FOUND,
            )

        membership = get_team_membership(
            db=db,
            team_id=preview.team_id,
            user_id=current_user.user_id,
        )

        if membership is None or not can_manage_team(membership):
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail=NOT_ALLOWED,
            )

        project = create_team_project(
            db=db,
            team=team,
            project_data=TeamProjectCreate(
                title=preview.project_title,
                description=_truncate_description(preview.description),
                deadline=preview.deadline,
            ),
            current_user=current_user,
        )
    else:
        project = create_personal_project(
            db=db,
            project_data=ProjectCreate(
                title=preview.project_title,
                description=_truncate_description(preview.description),
                deadline=preview.deadline,
            ),
            current_user=current_user,
        )

    return create_ai_plan_from_accepted_preview(
        db=db,
        project=project,
        current_user=current_user,
        accept_data=accept_data,
    )


@router.post(
    "/projects/{project_id}/ai-plan/generate",
    response_model=AIPlanGenerateResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def generate_personal_project_ai_plan_and_tasks(
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

    return create_ai_plan_generation_response(
        db=db,
        project=project,
        current_user=current_user,
        plan_data=plan_data,
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
    "/teams/{team_id}/projects/{project_id}/ai-plan/generate",
    response_model=AIPlanGenerateResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def generate_team_project_ai_plan_and_tasks(
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

    if membership is None:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    return create_ai_plan_generation_response(
        db=db,
        project=project,
        current_user=current_user,
        plan_data=plan_data,
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
