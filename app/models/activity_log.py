from __future__ import annotations

from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.task import Task
    from app.models.user import User


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    __table_args__ = (
        CheckConstraint(
            """
            event_type IN (
                'project_created',
                'project_updated',
                'task_created',
                'task_updated',
                'task_completed',
                'task_deleted',
                'comment_created',
                'comment_updated',
                'comment_deleted',
                'attachment_uploaded',
                'attachment_deleted',
                'deadline_reminder_generated'
            )
            """,
            name="chk_activity_logs_event_type",
        ),
    )

    activity_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    task_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("tasks.task_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    actor_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    actor_username_snapshot: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    actor_full_name_snapshot: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    task_title_snapshot: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    project: Mapped["Project"] = relationship(
        back_populates="activity_logs",
    )

    task: Mapped["Task | None"] = relationship(
        back_populates="activity_logs",
    )

    actor: Mapped["User | None"] = relationship(
        back_populates="activity_logs",
    )