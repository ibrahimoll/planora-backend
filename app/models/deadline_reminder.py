from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.task import Task
    from app.models.user import User


class DeadlineReminder(Base):
    __tablename__ = "deadline_reminders"

    __table_args__ = (
        CheckConstraint(
            "reminder_type IN ('due_soon', 'overdue')",
            name="chk_deadline_reminders_type",
        ),
        UniqueConstraint(
            "task_id",
            "user_id",
            "reminder_type",
            "due_date_snapshot",
            name="uq_deadline_reminders_task_user_type_due_date",
        ),
    )

    reminder_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    task_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tasks.task_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reminder_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    due_date_snapshot: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    task: Mapped["Task"] = relationship(
        back_populates="deadline_reminders",
    )

    project: Mapped["Project"] = relationship(
        back_populates="deadline_reminders",
    )

    user: Mapped["User"] = relationship(
        back_populates="deadline_reminders",
    )