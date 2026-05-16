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
    from app.models.team import Team
    from app.models.project_member import ProjectMember
    from app.models.attachment import Attachment
    from app.models.invitation import Invitation
    from app.models.deadline_reminder import DeadlineReminder
    from app.models.activity_log import ActivityLog
    from app.models.user_progress import UserProgress
    from app.models.ai_plan import AIPlan
    from app.models.risk_analysis import RiskAnalysis

CASCADE_ALL_DELETE_ORPHAN = "all, delete-orphan"

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
        ForeignKey("teams.team_id", ondelete="RESTRICT"),
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
        cascade=CASCADE_ALL_DELETE_ORPHAN,
    )

    team: Mapped["Team | None"] = relationship(
        back_populates="projects",
    )

    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project",
        cascade=CASCADE_ALL_DELETE_ORPHAN,
    )

    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="project",
        cascade=CASCADE_ALL_DELETE_ORPHAN,
    )
    
    creator: Mapped["User"] = relationship(
        back_populates="created_projects",
    )

    invitations: Mapped[list["Invitation"]] = relationship(
        back_populates="project",
        cascade=CASCADE_ALL_DELETE_ORPHAN,
    )

    deadline_reminders: Mapped[list["DeadlineReminder"]] = relationship(
        back_populates="project",
        cascade=CASCADE_ALL_DELETE_ORPHAN,
    )

    activity_logs: Mapped[list["ActivityLog"]] = relationship(
        back_populates="project",
        cascade=CASCADE_ALL_DELETE_ORPHAN,
    )

    user_progress_records: Mapped[list["UserProgress"]] = relationship(
        back_populates="project",
        cascade=CASCADE_ALL_DELETE_ORPHAN,
    )

    ai_plans: Mapped[list["AIPlan"]] = relationship(
        back_populates="project",
        cascade=CASCADE_ALL_DELETE_ORPHAN,
    )

    risk_analyses: Mapped[list["RiskAnalysis"]] = relationship(
        back_populates="project",
        cascade=CASCADE_ALL_DELETE_ORPHAN,
    )