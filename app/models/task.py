from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User
    from app.models.comment import Comment
    from app.models.attachment import Attachment
    from app.models.deadline_reminder import DeadlineReminder
    from app.models.activity_log import ActivityLog
    from app.models.subtask import Subtask


class Task(Base):
    __tablename__ = "tasks"

    __table_args__ = (
        CheckConstraint("priority IN ('low', 'medium', 'high')", name="chk_tasks_priority"),
        CheckConstraint("status IN ('todo', 'in_progress', 'completed', 'blocked')", name="chk_tasks_status"),
        CheckConstraint(
            "(estimated_hours IS NULL OR estimated_hours >= 0) AND (actual_hours IS NULL OR actual_hours >= 0)",
            name="chk_tasks_hours_non_negative",
        ),
        CheckConstraint(
            "((status = 'completed' AND completed_at IS NOT NULL) OR (status <> 'completed' AND completed_at IS NULL))",
            name="chk_tasks_completed_at_logic",
        ),
    )

    task_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_to: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'medium'"),
    )
    estimated_hours: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    actual_hours: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'todo'"),
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    project: Mapped["Project"] = relationship(back_populates="tasks")

    assignee: Mapped["User | None"] = relationship(
        foreign_keys=[assigned_to],
        back_populates="assigned_tasks",
    )

    comments: Mapped[list["Comment"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )

    creator: Mapped["User"] = relationship(
        foreign_keys=[created_by],
        back_populates="created_tasks",
    )

    @property
    def assigned_user(self) -> "User | None":
        return self.assignee

    @property
    def created_by_user(self) -> "User":
        return self.creator

    attachments: Mapped[list["Attachment"]] = relationship(back_populates="task")

    deadline_reminders: Mapped[list["DeadlineReminder"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )

    activity_logs: Mapped[list["ActivityLog"]] = relationship(
        back_populates="task",
    )

    subtasks: Mapped[list["Subtask"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="Subtask.created_at, Subtask.subtask_id",
    )

    @property
    def subtask_count(self) -> int:
        return len(self.subtasks)

    @property
    def completed_subtask_count(self) -> int:
        return sum(1 for subtask in self.subtasks if subtask.is_completed)

    @property
    def progress_percentage(self) -> float:
        if not self.subtasks:
            return 0.0

        return round((self.completed_subtask_count / self.subtask_count) * 100, 2)
