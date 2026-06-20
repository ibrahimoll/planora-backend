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
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.user import User


class Subtask(Base):
    __tablename__ = "subtasks"
    __table_args__ = (
        CheckConstraint(
            "((is_completed AND completed_at IS NOT NULL) OR "
            "(NOT is_completed AND completed_at IS NULL))",
            name="chk_subtasks_completed_at_logic",
        ),
    )

    subtask_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    task_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tasks.task_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    is_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    task: Mapped["Task"] = relationship(back_populates="subtasks")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])

    @property
    def status(self) -> str:
        return "completed" if self.is_completed else "todo"
