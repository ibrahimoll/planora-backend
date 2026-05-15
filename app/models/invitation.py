from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
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
    from app.models.project import Project
    from app.models.team import Team
    from app.models.user import User


class Invitation(Base):
    __tablename__ = "invitations"

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'expired')",
            name="chk_invitations_status",
        ),
        CheckConstraint(
            "role IN ('admin', 'manager', 'member')",
            name="chk_invitations_role",
        ),
        CheckConstraint(
            "invited_user_id IS NOT NULL OR email IS NOT NULL",
            name="chk_invitations_target",
        ),
        CheckConstraint(
            "project_id IS NULL OR team_id IS NOT NULL",
            name="chk_invitations_project_requires_team",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="chk_invitations_expiry",
        ),
    )

    invitation_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    invited_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    invited_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    team_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("teams.team_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    project_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'pending'"),
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    inviter: Mapped["User"] = relationship(
        foreign_keys=[invited_by],
        back_populates="sent_invitations",
    )

    invited_user: Mapped["User | None"] = relationship(
        foreign_keys=[invited_user_id],
        back_populates="received_invitations",
    )

    team: Mapped["Team"] = relationship(
        back_populates="invitations",
    )

    project: Mapped["Project | None"] = relationship(
        back_populates="invitations",
    )