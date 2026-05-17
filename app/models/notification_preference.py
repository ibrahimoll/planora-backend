from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            name="uq_notification_preferences_user_id",
        ),
    )

    preference_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    task_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    project_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    team_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    comment_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    mention_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    invite_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    deadline_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    ai_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    risk_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    system_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    push_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="notification_preferences")