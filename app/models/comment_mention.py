from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.comment import Comment
    from app.models.user import User


class CommentMention(Base):
    __tablename__ = "comment_mentions"

    __table_args__ = (
        UniqueConstraint(
            "comment_id",
            "mentioned_user_id",
            name="uq_comment_mentions_comment_user",
        ),
    )

    mention_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    comment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("comments.comment_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    task_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tasks.task_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    mentioned_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    mentioned_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    comment: Mapped["Comment"] = relationship(
        back_populates="mentions",
    )

    mentioned_user: Mapped["User"] = relationship(
        foreign_keys=[mentioned_user_id],
        back_populates="received_comment_mentions",
    )

    mentioner: Mapped["User"] = relationship(
        foreign_keys=[mentioned_by],
        back_populates="created_comment_mentions",
    )