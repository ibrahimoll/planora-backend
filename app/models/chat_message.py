from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    __table_args__ = (
        CheckConstraint(
            "sender_type IN ('user', 'ai')",
            name="chk_chat_messages_sender_type",
        ),
        CheckConstraint(
            """
            (
                sender_type = 'user'
                AND sender_id IS NOT NULL
            )
            OR
            (
                sender_type = 'ai'
                AND sender_id IS NULL
            )
            """,
            name="chk_chat_messages_sender_logic",
        ),
    )

    message_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    sender_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    message: Mapped[str] = mapped_column(Text, nullable=False)

    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    project: Mapped["Project"] = relationship(
        back_populates="chat_messages",
    )

    sender: Mapped["User | None"] = relationship(
        back_populates="chat_messages",
    )