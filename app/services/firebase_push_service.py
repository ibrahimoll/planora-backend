from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.device_token import DeviceToken
from app.models.notification_preference import NotificationPreference


INVALID_FIREBASE_TOKEN_ERROR_NAMES = {
    "UnregisteredError",
    "InvalidArgumentError",
    "SenderIdMismatchError",
}


@dataclass(slots=True)
class PushSendResult:
    status: str
    detail: str
    sent_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    deactivated_tokens: int = 0


def _notification_preference_field(notification_type: str) -> str | None:
    return {
        "task": "task_notifications",
        "project": "project_notifications",
        "team": "team_notifications",
        "comment": "comment_notifications",
        "mention": "mention_notifications",
        "invite": "invite_notifications",
        "deadline": "deadline_notifications",
        "ai": "ai_notifications",
        "risk": "risk_notifications",
        "system": "system_notifications",
    }.get(notification_type)


def _is_invalid_token_error(exc: Exception) -> bool:
    return exc.__class__.__name__ in INVALID_FIREBASE_TOKEN_ERROR_NAMES


def initialize_firebase_app() -> bool:
    if not settings.firebase_enabled:
        return False

    if firebase_admin._apps:
        return True

    if settings.firebase_credentials_json:
        credential_data = json.loads(settings.firebase_credentials_json)
        credential = credentials.Certificate(credential_data)
        firebase_admin.initialize_app(credential)
        return True

    if settings.firebase_credentials_path:
        credential = credentials.Certificate(settings.firebase_credentials_path)
        firebase_admin.initialize_app(credential)
        return True

    return False


def _get_active_device_tokens(
    db: Session,
    user_id: int,
) -> list[DeviceToken]:
    stmt = select(DeviceToken).where(
        DeviceToken.user_id == user_id,
        DeviceToken.is_active.is_(True),
    )

    return list(db.execute(stmt).scalars().all())


def _get_notification_preferences(
    db: Session,
    user_id: int,
) -> NotificationPreference | None:
    stmt = select(NotificationPreference).where(
        NotificationPreference.user_id == user_id,
    )

    return db.execute(stmt).scalars().first()


def _user_allows_push(
    preferences: NotificationPreference | None,
    notification_type: str,
) -> bool:
    if preferences is None:
        return True

    if not preferences.push_enabled:
        return False

    preference_field = _notification_preference_field(notification_type)

    if preference_field is None:
        return True

    return bool(getattr(preferences, preference_field))


def send_push_to_user(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notification_type: str,
    data: dict[str, Any] | None = None,
) -> PushSendResult:
    active_tokens = _get_active_device_tokens(
        db=db,
        user_id=user_id,
    )

    if not active_tokens:
        return PushSendResult(
            status="skipped",
            detail="No active device tokens found for this user.",
        )

    preferences = _get_notification_preferences(
        db=db,
        user_id=user_id,
    )

    if not _user_allows_push(
        preferences=preferences,
        notification_type=notification_type,
    ):
        return PushSendResult(
            status="skipped",
            detail="User notification preferences disabled this push notification.",
            skipped_count=len(active_tokens),
        )

    try:
        firebase_ready = initialize_firebase_app()
    except Exception:
        return PushSendResult(
            status="skipped",
            detail="Firebase initialization failed. Push notification was skipped.",
            skipped_count=len(active_tokens),
        )

    if not firebase_ready:
        return PushSendResult(
            status="skipped",
            detail="Firebase push sending is disabled or not configured.",
            skipped_count=len(active_tokens),
        )

    push_data = {
        "type": str(notification_type),
        **{
            str(key): str(value)
            for key, value in (data or {}).items()
            if value is not None
        },
    }

    sent_count = 0
    failed_count = 0
    deactivated_tokens = 0

    for device_token in active_tokens:
        firebase_message = messaging.Message(
            data={
                **push_data,
                "title": title,
                "message": message,
            },
            token=device_token.token,
        )

        try:
            messaging.send(firebase_message)
            sent_count += 1
        except Exception as exc:
            failed_count += 1

            if _is_invalid_token_error(exc):
                device_token.is_active = False
                deactivated_tokens += 1

    if deactivated_tokens:
        db.commit()

    if sent_count and failed_count:
        status = "partial"
        detail = "Push notification was sent to some devices, but failed for others."
    elif sent_count:
        status = "sent"
        detail = "Push notification sent successfully."
    else:
        status = "failed"
        detail = "Push notification failed for all active devices."

    return PushSendResult(
        status=status,
        detail=detail,
        sent_count=sent_count,
        failed_count=failed_count,
        deactivated_tokens=deactivated_tokens,
    )