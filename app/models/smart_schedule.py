from __future__ import annotations

from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class SmartSchedule(Base):
    __tablename__ = "smart_schedules"

    __table_args__ = (
        CheckConstraint(
            "strategy IN ('balanced')",
            name="chk_smart_schedules_strategy",
        ),
    )

    schedule_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    generated_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    strategy: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'balanced'"),
    )

    schedule_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    project: Mapped["Project"] = relationship(
        back_populates="smart_schedules",
    )

    generated_by_user: Mapped["User | None"] = relationship(
        back_populates="generated_smart_schedules",
    )