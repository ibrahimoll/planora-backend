from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_admin_user
from app.models.user import User
from app.schemas.admin_risk_report_schema import (
    AdminHighRiskProjectResponse,
    AdminProjectSummaryReportResponse,
    AdminRiskCenterSummaryResponse,
    AdminSystemSummaryReportResponse,
    AdminUserSummaryReportResponse,
)
from app.services.admin_risk_report_service import (
    get_admin_high_risk_projects,
    get_admin_projects_summary_report,
    get_admin_risk_summary,
    get_admin_system_summary_report,
    get_admin_users_summary_report,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentAdmin = Annotated[User, Depends(get_current_admin_user)]

router = APIRouter(
    prefix="/admin",
    tags=["Admin Risk and Reports"],
)


@router.get("/risk/summary", response_model=AdminRiskCenterSummaryResponse)
def read_admin_risk_summary(
    db: DBSession,
    current_admin: CurrentAdmin,
):
    return get_admin_risk_summary(db=db)


@router.get("/risk/high-risk-projects", response_model=list[AdminHighRiskProjectResponse])
def read_admin_high_risk_projects(
    db: DBSession,
    current_admin: CurrentAdmin,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return get_admin_high_risk_projects(db=db, limit=limit, offset=offset)


@router.get("/reports/system-summary", response_model=AdminSystemSummaryReportResponse)
def read_admin_system_summary_report(
    db: DBSession,
    current_admin: CurrentAdmin,
):
    return get_admin_system_summary_report(db=db)


@router.get("/reports/projects-summary", response_model=AdminProjectSummaryReportResponse)
def read_admin_projects_summary_report(
    db: DBSession,
    current_admin: CurrentAdmin,
):
    return get_admin_projects_summary_report(db=db)


@router.get("/reports/users-summary", response_model=AdminUserSummaryReportResponse)
def read_admin_users_summary_report(
    db: DBSession,
    current_admin: CurrentAdmin,
):
    return get_admin_users_summary_report(db=db)
