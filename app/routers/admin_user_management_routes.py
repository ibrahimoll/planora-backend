from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_admin_user
from app.models.user import User
from app.schemas.admin_dashboard_schema import AdminActivityLogResponse
from app.schemas.admin_user_management_schema import (
    AdminUserActionResponse,
    AdminUserDetailResponse,
    AdminUserRoleUpdateRequest,
)
from app.services.admin_user_management_service import (
    activate_user_by_admin,
    change_user_role_by_admin,
    deactivate_user_by_admin,
    get_admin_user_activity,
    get_admin_user_detail,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentAdmin = Annotated[User, Depends(get_current_admin_user)]

router = APIRouter(
    prefix="/admin/users",
    tags=["Admin User Management"],
)


@router.get("/{user_id}", response_model=AdminUserDetailResponse)
def read_admin_user_detail(
    user_id: int,
    db: DBSession,
    current_admin: CurrentAdmin,
):
    return get_admin_user_detail(db=db, user_id=user_id)


@router.get("/{user_id}/activity", response_model=list[AdminActivityLogResponse])
def read_admin_user_activity(
    user_id: int,
    db: DBSession,
    current_admin: CurrentAdmin,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return get_admin_user_activity(db=db, user_id=user_id, limit=limit, offset=offset)


@router.patch("/{user_id}/deactivate", response_model=AdminUserActionResponse)
def deactivate_admin_user(
    user_id: int,
    db: DBSession,
    current_admin: CurrentAdmin,
):
    return deactivate_user_by_admin(db=db, admin=current_admin, user_id=user_id)


@router.patch("/{user_id}/activate", response_model=AdminUserActionResponse)
def activate_admin_user(
    user_id: int,
    db: DBSession,
    current_admin: CurrentAdmin,
):
    return activate_user_by_admin(db=db, admin=current_admin, user_id=user_id)


@router.patch("/{user_id}/role", response_model=AdminUserActionResponse)
def change_admin_user_role(
    user_id: int,
    payload: AdminUserRoleUpdateRequest,
    db: DBSession,
    current_admin: CurrentAdmin,
):
    return change_user_role_by_admin(
        db=db,
        admin=current_admin,
        user_id=user_id,
        new_role=payload.role,
    )
