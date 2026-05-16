from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.risk_analysis_schema import (
    RiskAnalysisPreviewResponse,
    RiskAnalysisResponse,
)
from app.services.risk_analysis_service import (
    create_risk_analysis_for_project,
    get_accessible_project_for_risk_analysis,
    get_risk_analyses_for_project,
    preview_risk_analysis_for_project,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

PROJECT_NOT_FOUND = "Project not found"

router = APIRouter(
    prefix="/projects",
    tags=["Risk Analysis"],
)


@router.get(
    "/{project_id}/risk-analysis/preview",
    response_model=RiskAnalysisPreviewResponse,
)
def preview_project_risk_analysis(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_accessible_project_for_risk_analysis(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    return preview_risk_analysis_for_project(
        db=db,
        project=project,
    )


@router.post(
    "/{project_id}/risk-analysis",
    response_model=RiskAnalysisResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def generate_project_risk_analysis(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_accessible_project_for_risk_analysis(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    return create_risk_analysis_for_project(
        db=db,
        project=project,
    )


@router.get(
    "/{project_id}/risk-analysis",
    response_model=list[RiskAnalysisResponse],
)
def list_project_risk_analyses(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_accessible_project_for_risk_analysis(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    return get_risk_analyses_for_project(
        db=db,
        project=project,
    )