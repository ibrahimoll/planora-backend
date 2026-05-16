from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.admin_log import AdminLog
from app.models.notification import Notification
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.admin_user_management_schema import (
    AdminUserActionResponse,
    AdminUserCountsResponse,
    AdminUserDetailResponse,
)


def _count_query(db: Session, stmt) -> int:
    value = db.scalar(stmt)
    return int(value or 0)


def _count_where(db: Session, model: type, *conditions) -> int:
    stmt = select(func.count()).select_from(model)

    if conditions:
        stmt = stmt.where(*conditions)

    return _count_query(db, stmt)


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return user


def _active_verified_admin_count(db: Session) -> int:
    return _count_query(
        db,
        select(func.count())
        .select_from(User)
        .where(
            User.role == "admin",
            User.is_active.is_(True),
            User.is_email_verified.is_(True),
        ),
    )


def _create_admin_log(
    db: Session,
    admin_id: int,
    action: str,
    target_user_id: int | None,
) -> AdminLog:
    log = AdminLog(
        admin_id=admin_id,
        target_user_id=target_user_id,
        action=action,
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return log


def _build_user_detail(
    db: Session,
    user: User,
) -> AdminUserDetailResponse:
    counts = AdminUserCountsResponse(
        projects_created=_count_where(db, Project, Project.created_by == user.user_id),
        assigned_tasks=_count_where(db, Task, Task.assigned_to == user.user_id),
        created_tasks=_count_where(db, Task, Task.created_by == user.user_id),
        notifications=_count_where(db, Notification, Notification.user_id == user.user_id),
        admin_logs_as_target=_count_where(db, AdminLog, AdminLog.target_user_id == user.user_id),
    )

    return AdminUserDetailResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_email_verified=user.is_email_verified,
        profile_pic=user.profile_pic,
        created_at=user.created_at,
        counts=counts,
    )


def get_admin_user_detail(db: Session, user_id: int) -> AdminUserDetailResponse:
    user = _get_user_or_404(db=db, user_id=user_id)
    return _build_user_detail(db=db, user=user)


def get_admin_user_activity(db: Session, user_id: int, limit: int, offset: int) -> list[ActivityLog]:
    _get_user_or_404(db=db, user_id=user_id)

    stmt = (
        select(ActivityLog)
        .where(ActivityLog.actor_id == user_id)
        .order_by(ActivityLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    return list(db.execute(stmt).scalars().all())


def deactivate_user_by_admin(db: Session, admin: User, user_id: int) -> AdminUserActionResponse:
    user = _get_user_or_404(db=db, user_id=user_id)

    if user.user_id == admin.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own admin account.",
        )

    if (
        user.role == "admin"
        and user.is_active
        and user.is_email_verified
        and _active_verified_admin_count(db) <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate the last active verified admin.",
        )

    user.is_active = False

    log = _create_admin_log(
        db=db,
        admin_id=admin.user_id,
        target_user_id=user.user_id,
        action=f"deactivated_user:user_id={user.user_id}",
    )

    db.refresh(user)

    return AdminUserActionResponse(
        message="User deactivated successfully.",
        user=_build_user_detail(db=db, user=user),
        admin_log_id=log.log_id,
    )


def activate_user_by_admin(db: Session, admin: User, user_id: int) -> AdminUserActionResponse:
    user = _get_user_or_404(db=db, user_id=user_id)

    user.is_active = True

    log = _create_admin_log(
        db=db,
        admin_id=admin.user_id,
        target_user_id=user.user_id,
        action=f"activated_user:user_id={user.user_id}",
    )

    db.refresh(user)

    return AdminUserActionResponse(
        message="User activated successfully.",
        user=_build_user_detail(db=db, user=user),
        admin_log_id=log.log_id,
    )


def change_user_role_by_admin(db: Session, admin: User, user_id: int, new_role: str) -> AdminUserActionResponse:
    user = _get_user_or_404(db=db, user_id=user_id)
    old_role = user.role

    if user.user_id == admin.user_id and new_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove your own admin role.",
        )

    if (
        old_role == "admin"
        and new_role == "user"
        and user.is_active
        and user.is_email_verified
        and _active_verified_admin_count(db) <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove the last active verified admin.",
        )

    user.role = new_role

    log = _create_admin_log(
        db=db,
        admin_id=admin.user_id,
        target_user_id=user.user_id,
        action=(
            f"changed_user_role:user_id={user.user_id}:"
            f"old_role={old_role}:new_role={new_role}"
        ),
    )

    db.refresh(user)

    return AdminUserActionResponse(
        message="User role updated successfully.",
        user=_build_user_detail(db=db, user=user),
        admin_log_id=log.log_id,
    )
