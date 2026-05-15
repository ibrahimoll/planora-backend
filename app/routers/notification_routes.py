from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.notification_schema import (
    NotificationMessageResponse,
    NotificationResponse,
    NotificationUnreadCountResponse,
)
from app.services.notification_service import (
    delete_notification,
    get_my_notification_by_id,
    get_my_notifications,
    get_my_unread_notification_count,
    mark_all_my_notifications_as_read,
    mark_notification_as_read,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]
UnreadOnlyQuery = Annotated[bool, Query()]

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)

NOTIFICATION_NOT_FOUND = "Notification not found"


@router.get(
    "",
    response_model=list[NotificationResponse],
)
def list_my_notifications(
    db: DBSession,
    current_user: CurrentUser,
    unread_only: UnreadOnlyQuery = False,
):
    return get_my_notifications(
        db=db,
        current_user=current_user,
        unread_only=unread_only,
    )


@router.get(
    "/unread-count",
    response_model=NotificationUnreadCountResponse,
)
def get_unread_notifications_count(
    db: DBSession,
    current_user: CurrentUser,
):
    unread_count = get_my_unread_notification_count(
        db=db,
        current_user=current_user,
    )

    return NotificationUnreadCountResponse(
        unread_count=unread_count,
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
)
def read_notification(
    notification_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    notification = get_my_notification_by_id(
        db=db,
        current_user=current_user,
        notification_id=notification_id,
    )

    if notification is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=NOTIFICATION_NOT_FOUND,
        )

    return mark_notification_as_read(
        db=db,
        notification=notification,
    )


@router.patch(
    "/read-all",
    response_model=NotificationMessageResponse,
)
def read_all_notifications(
    db: DBSession,
    current_user: CurrentUser,
):
    updated_count = mark_all_my_notifications_as_read(
        db=db,
        current_user=current_user,
    )

    return NotificationMessageResponse(
        message=f"{updated_count} notifications marked as read.",
    )


@router.delete(
    "/{notification_id}",
    response_model=NotificationMessageResponse,
)
def remove_notification(
    notification_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    notification = get_my_notification_by_id(
        db=db,
        current_user=current_user,
        notification_id=notification_id,
    )

    if notification is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=NOTIFICATION_NOT_FOUND,
        )

    delete_notification(
        db=db,
        notification=notification,
    )

    return NotificationMessageResponse(
        message="Notification deleted successfully.",
    )