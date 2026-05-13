from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.team_member import TeamMember
    from app.models.user import User


class Team(Base):
    __tablename__ = "teams"

    team_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    creator: Mapped["User"] = relationship(
        back_populates="created_teams",
    )

    members: Mapped[list["TeamMember"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
    )

    projects: Mapped[list["Project"]] = relationship(
        back_populates="team",
    )