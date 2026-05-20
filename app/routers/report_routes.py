from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.report_schema import (
    ProjectReportResponse,
    ReportExportHistoryListResponse,
)
from app.services.report_service import (
    create_report_export_history,
    generate_project_report,
    get_accessible_project_for_report,
    list_my_report_exports,
    list_project_report_exports,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

PROJECT_NOT_FOUND = "Project not found"

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)


@router.get(
    "/projects/{project_id}",
    response_model=ProjectReportResponse,
)
def export_project_report(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_accessible_project_for_report(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    report = generate_project_report(
        db=db,
        project=project,
    )

    export = create_report_export_history(
        db=db,
        project=project,
        current_user=current_user,
        report=report,
    )

    return report.model_copy(
        update={
            "export_id": export.report_export_id,
        }
    )


@router.get(
    "/exports",
    response_model=ReportExportHistoryListResponse,
)
def get_my_report_export_history(
    db: DBSession,
    current_user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return list_my_report_exports(
        db=db,
        current_user=current_user,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/projects/{project_id}/exports",
    response_model=ReportExportHistoryListResponse,
)
def get_project_report_export_history(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    project = get_accessible_project_for_report(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    return list_project_report_exports(
        db=db,
        project=project,
        limit=limit,
        offset=offset,
    )