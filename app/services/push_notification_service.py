from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.device_token import DeviceToken
from app.models.notification_preference import NotificationPreference
from app.models.user import User
from app.schemas.push_notification_schema import (
    DeviceTokenCreate,
    NotificationPreferenceUpdate,
)


def register_device_token(
    db: Session,
    current_user: User,
    token_data: DeviceTokenCreate,
) -> DeviceToken:
    if token_data.device_key:
        stmt = select(DeviceToken).where(
            DeviceToken.user_id == current_user.user_id,
            DeviceToken.device_key == token_data.device_key,
        )
        existing_device = db.execute(stmt).scalars().first()

        if existing_device is not None:
            existing_device.token = token_data.token
            existing_device.platform = str(token_data.platform)
            existing_device.is_active = True

            db.commit()
            db.refresh(existing_device)
            return existing_device

    stmt = select(DeviceToken).where(DeviceToken.token == token_data.token)
    existing_token = db.execute(stmt).scalars().first()

    if existing_token is not None:
        existing_token.user_id = current_user.user_id
        existing_token.platform = str(token_data.platform)
        existing_token.device_key = token_data.device_key
        existing_token.is_active = True

        db.commit()
        db.refresh(existing_token)
        return existing_token

    device_token = DeviceToken(
        user_id=current_user.user_id,
        token=token_data.token,
        platform=str(token_data.platform),
        device_key=token_data.device_key,
        is_active=True,
    )

    db.add(device_token)
    db.commit()
    db.refresh(device_token)

    return device_token

def get_my_device_tokens(
    db: Session,
    current_user: User,
) -> list[DeviceToken]:
    stmt = (
        select(DeviceToken)
        .where(DeviceToken.user_id == current_user.user_id)
        .order_by(DeviceToken.created_at.desc())
    )

    return list(db.execute(stmt).scalars().all())


def deactivate_my_device_token(
    db: Session,
    current_user: User,
    device_token_id: int,
) -> DeviceToken | None:
    stmt = select(DeviceToken).where(
        DeviceToken.device_token_id == device_token_id,
        DeviceToken.user_id == current_user.user_id,
    )

    device_token = db.execute(stmt).scalars().first()

    if device_token is None:
        return None

    device_token.is_active = False

    db.commit()
    db.refresh(device_token)

    return device_token


def get_or_create_notification_preferences(
    db: Session,
    current_user: User,
) -> NotificationPreference:
    stmt = select(NotificationPreference).where(
        NotificationPreference.user_id == current_user.user_id,
    )

    preferences = db.execute(stmt).scalars().first()

    if preferences is not None:
        return preferences

    preferences = NotificationPreference(user_id=current_user.user_id)

    db.add(preferences)
    db.commit()
    db.refresh(preferences)

    return preferences


def update_notification_preferences(
    db: Session,
    current_user: User,
    preference_data: NotificationPreferenceUpdate,
) -> NotificationPreference:
    preferences = get_or_create_notification_preferences(
        db=db,
        current_user=current_user,
    )

    update_data = preference_data.model_dump(exclude_unset=True)

    for field_name, value in update_data.items():
        setattr(preferences, field_name, value)

    db.commit()
    db.refresh(preferences)

    return preferences