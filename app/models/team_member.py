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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.team import Team
    from app.models.user import User


class TeamMember(Base):
    __tablename__ = "team_members"

    __table_args__ = (
        CheckConstraint(
            "role IN ('owner', 'admin', 'member')",
            name="chk_team_members_role",
        ),
        UniqueConstraint(
            "team_id",
            "user_id",
            name="uq_team_members_team_user",
        ),
    )

    team_member_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    team_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("teams.team_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'member'"),
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    team: Mapped["Team"] = relationship(
        back_populates="members",
    )

    user: Mapped["User"] = relationship(
        back_populates="team_memberships",
    )