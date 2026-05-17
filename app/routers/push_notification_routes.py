from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.push_notification_schema import (
    DeviceTokenCreate,
    DeviceTokenResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    PushNotificationMessageResponse,
)
from app.services.push_notification_service import (
    deactivate_my_device_token,
    get_my_device_tokens,
    get_or_create_notification_preferences,
    register_device_token,
    update_notification_preferences,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

router = APIRouter(
    prefix="/push-notifications",
    tags=["Push Notifications"],
)


@router.post(
    "/device-tokens",
    response_model=DeviceTokenResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def create_or_update_device_token(
    token_data: DeviceTokenCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    return register_device_token(
        db=db,
        current_user=current_user,
        token_data=token_data,
    )


@router.get(
    "/device-tokens",
    response_model=list[DeviceTokenResponse],
)
def list_my_device_tokens(
    db: DBSession,
    current_user: CurrentUser,
):
    return get_my_device_tokens(
        db=db,
        current_user=current_user,
    )


@router.patch(
    "/device-tokens/{device_token_id}/deactivate",
    response_model=DeviceTokenResponse,
)
def deactivate_device_token(
    device_token_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    device_token = deactivate_my_device_token(
        db=db,
        current_user=current_user,
        device_token_id=device_token_id,
    )

    if device_token is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Device token not found.",
        )

    return device_token


@router.get(
    "/preferences",
    response_model=NotificationPreferenceResponse,
)
def get_my_push_preferences(
    db: DBSession,
    current_user: CurrentUser,
):
    return get_or_create_notification_preferences(
        db=db,
        current_user=current_user,
    )


@router.patch(
    "/preferences",
    response_model=NotificationPreferenceResponse,
)
def update_my_push_preferences(
    preference_data: NotificationPreferenceUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    return update_notification_preferences(
        db=db,
        current_user=current_user,
        preference_data=preference_data,
    )


@router.get(
    "/status",
    response_model=PushNotificationMessageResponse,
)
def push_notification_status():
    return PushNotificationMessageResponse(
        message="Push notification foundation is ready. Firebase sending is not enabled yet.",
    )