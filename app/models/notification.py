from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User

class Notification(Base):
    __tablename__ = "notifications"

    __table_args__ = (
        CheckConstraint(
            """
            type IN (
                'task',
                'project',
                'team',
                'comment',
                'mention',
                'invite',
                'deadline',
                'ai',
                'risk',
                'system'
            )
            """,
            name="chk_notifications_type",
        ),
    )

    notification_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(
        back_populates="notifications",
    )