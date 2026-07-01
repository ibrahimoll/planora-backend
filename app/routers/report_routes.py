from __future__ import annotations

from datetime import datetime, timezone
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
    ReportRequestResponse,
)
from app.services.email_service import EmailDeliveryError, send_report_request_email
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


@router.post(
    "/projects/{project_id}/request",
    response_model=ReportRequestResponse,
    status_code=http_status.HTTP_202_ACCEPTED,
)
def request_project_report(
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

    admins = (
        db.query(User)
        .filter(
            User.role == "admin",
            User.is_active.is_(True),
            User.is_email_verified.is_(True),
        )
        .all()
    )

    if not admins:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No verified active admin is available to receive report requests.",
        )

    delivered_count = 0
    for admin in admins:
        try:
            send_report_request_email(
                recipient_email=admin.email,
                admin_name=admin.full_name,
                requester_name=current_user.full_name,
                requester_email=current_user.email,
                project_title=project.title,
                project_id=project.project_id,
                project_type=project.project_type,
            )
            delivered_count += 1
        except EmailDeliveryError:
            continue

    if delivered_count == 0:
        raise HTTPException(
            status_code=http_status.HTTP_502_BAD_GATEWAY,
            detail="Report request could not be emailed to admins.",
        )

    return ReportRequestResponse(
        message="Report request sent to admin.",
        project_id=project.project_id,
        project_title=project.title,
        requested_at=datetime.now(timezone.utc),
        notified_admin_count=delivered_count,
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
