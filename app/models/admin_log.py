from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class AdminLog(Base):
    __tablename__ = "admin_logs"

    log_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    admin_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    target_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    admin: Mapped["User"] = relationship(
        foreign_keys=[admin_id],
        back_populates="admin_logs",
    )

    target_user: Mapped["User | None"] = relationship(
        foreign_keys=[target_user_id],
        back_populates="target_admin_logs",
    )