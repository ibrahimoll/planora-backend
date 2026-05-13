from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.task import Task


class Project(Base):
    __tablename__ = "projects"

    __table_args__ = (
        CheckConstraint(
            "status IN ('not_started', 'in_progress', 'completed', 'on_hold', 'cancelled')",
            name="chk_project_status",
        ),
        CheckConstraint(
            "project_type IN ('personal', 'team')",
            name="chk_project_type",
        ),
        CheckConstraint(
            """
            (
                project_type = 'personal'
                AND team_id IS NULL
            )
            OR
            (
                project_type = 'team'
                AND team_id IS NOT NULL
            )
            """,
            name="chk_project_type_team_relation",
        ),
    )

    project_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    team_id: Mapped[int | None] = mapped_column(
        BigInteger,
        # ForeignKey("teams.team_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'not_started'"),
    )

    project_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
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
    )

    tasks: Mapped[list["Task"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )

    creator: Mapped["User"] = relationship(
        back_populates="created_projects",
    )