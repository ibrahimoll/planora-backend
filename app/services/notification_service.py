from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification_schema import NotificationCreate, NotificationType
from app.services.firebase_push_service import send_push_to_user

def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notification_type: NotificationType | str,
    commit: bool = True,
    send_push: bool = True,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=str(notification_type),
    )

    db.add(notification)

    if commit:
        db.commit()
        db.refresh(notification)

        if send_push:
            send_push_to_user(
                db=db,
                user_id=user_id,
                title=title,
                message=message,
                notification_type=str(notification_type),
                data={
                    "notification_id": notification.notification_id,
                },
            )

    return notification


def create_notification_from_schema(
    db: Session,
    notification_data: NotificationCreate,
) -> Notification:
    return create_notification(
        db=db,
        user_id=notification_data.user_id,
        title=notification_data.title,
        message=notification_data.message,
        notification_type=notification_data.type,
    )


def get_my_notifications(
    db: Session,
    current_user: User,
    unread_only: bool = False,
) -> list[Notification]:
    stmt = select(Notification).where(
        Notification.user_id == current_user.user_id,
    )

    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))

    stmt = stmt.order_by(Notification.created_at.desc())

    return list(db.execute(stmt).scalars().all())


def get_my_notification_by_id(
    db: Session,
    current_user: User,
    notification_id: int,
) -> Notification | None:
    stmt = select(Notification).where(
        Notification.notification_id == notification_id,
        Notification.user_id == current_user.user_id,
    )

    return db.execute(stmt).scalars().first()


def get_my_unread_notification_count(
    db: Session,
    current_user: User,
) -> int:
    stmt = select(func.count()).select_from(Notification).where(
        Notification.user_id == current_user.user_id,
        Notification.is_read.is_(False),
    )

    return int(db.execute(stmt).scalar_one())


def mark_notification_as_read(
    db: Session,
    notification: Notification,
) -> Notification:
    notification.is_read = True

    db.commit()
    db.refresh(notification)

    return notification


def mark_all_my_notifications_as_read(
    db: Session,
    current_user: User,
) -> int:
    stmt = select(Notification).where(
        Notification.user_id == current_user.user_id,
        Notification.is_read.is_(False),
    )

    notifications = list(db.execute(stmt).scalars().all())

    for notification in notifications:
        notification.is_read = True

    db.commit()

    return len(notifications)


def delete_notification(
    db: Session,
    notification: Notification,
) -> None:
    db.delete(notification)
    db.commit()