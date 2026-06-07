from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.user import User
    from app.models.comment_mention import CommentMention


class Comment(Base):
    __tablename__ = "comments"

    comment_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    task_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tasks.task_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    comment_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    task: Mapped["Task"] = relationship(
        back_populates="comments",
    )

    user: Mapped["User"] = relationship(
        back_populates="comments",
    )

    @property
    def user_username(self) -> str | None:
        return self.user.username if self.user is not None else None

    @property
    def user_full_name(self) -> str | None:
        return self.user.full_name if self.user is not None else None

    @property
    def user_profile_pic(self) -> str | None:
        return self.user.profile_pic if self.user is not None else None

    mentions: Mapped[list["CommentMention"]] = relationship(
        back_populates="comment",
        cascade="all, delete-orphan",
    )
