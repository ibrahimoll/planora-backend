from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_admin_user
from app.models.user import User
from app.schemas.admin_dashboard_schema import (
    AdminActivityLogResponse,
    AdminDashboardOverviewResponse,
    AdminLogResponse,
    AdminUserSummaryResponse,
)
from app.services.admin_dashboard_service import (
    get_admin_dashboard_overview,
    get_admin_logs,
    get_admin_users,
    get_recent_activity_logs,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentAdmin = Annotated[User, Depends(get_current_admin_user)]
UserRoleFilter = Literal["user", "admin"]

router = APIRouter(
    prefix="/admin",
    tags=["Admin Dashboard"],
)


@router.get("/dashboard/overview", response_model=AdminDashboardOverviewResponse)
def read_admin_dashboard_overview(
    db: DBSession,
    current_admin: CurrentAdmin,
):
    return get_admin_dashboard_overview(db=db)


@router.get("/users", response_model=list[AdminUserSummaryResponse])
def read_admin_users(
    db: DBSession,
    current_admin: CurrentAdmin,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    role: UserRoleFilter | None = None,
    is_active: bool | None = None,
    is_email_verified: bool | None = None,
    search: str | None = None,
):
    return get_admin_users(
        db=db,
        limit=limit,
        offset=offset,
        role=role,
        is_active=is_active,
        is_email_verified=is_email_verified,
        search=search,
    )


@router.get("/dashboard/recent-activity", response_model=list[AdminActivityLogResponse])
def read_recent_activity_logs(
    db: DBSession,
    current_admin: CurrentAdmin,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return get_recent_activity_logs(db=db, limit=limit)


@router.get("/logs", response_model=list[AdminLogResponse])
def read_admin_logs(
    db: DBSession,
    current_admin: CurrentAdmin,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    admin_id: int | None = None,
    target_user_id: int | None = None,
    action: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
):
    return get_admin_logs(
        db=db,
        limit=limit,
        offset=offset,
        admin_id=admin_id,
        target_user_id=target_user_id,
        action=action,
        created_from=created_from,
        created_to=created_to,
    )
