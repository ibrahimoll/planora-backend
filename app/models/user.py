from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import(
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.email_verification_code import EmailVerificationCode
    from app.models.password_reset_code import PasswordResetCode
    from app.models.oauth_account import OAuthAccount
    from app.models.project import Project
    from app.models.task import Task
    from app.models.team import Team
    from app.models.team_member import TeamMember
    from app.models.project_member import ProjectMember
    from app.models.comment import Comment
    from app.models.attachment import Attachment

CASCADE_ALL_DELETE_ORPHAN = "all, delete-orphan"

class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint(
            "role IN('user', 'admin')",
            name = "chk_users_role",
        ),
    )

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)

    role: Mapped[str] = mapped_column(
        String(20),
        nullable= False,
        server_default= text("'user'"),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable= False,
        server_default= text("true"),
    )

    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    profile_pic: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    verification_codes: Mapped[list["EmailVerificationCode"]] = relationship(
        back_populates="user",
        cascade= CASCADE_ALL_DELETE_ORPHAN,
    )

    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        back_populates= "user",
        cascade= CASCADE_ALL_DELETE_ORPHAN,
    )

    created_projects: Mapped[list["Project"]] = relationship(
        back_populates="creator",
    )
    
    password_reset_codes: Mapped[list["PasswordResetCode"]] = relationship(
    back_populates="user",
    cascade=CASCADE_ALL_DELETE_ORPHAN,
    )

    assigned_tasks: Mapped[list["Task"]] = relationship(
        foreign_keys="Task.assigned_to",
        back_populates="assignee",
    )
    
    created_tasks: Mapped[list["Task"]] = relationship(
        foreign_keys="Task.created_by",
        back_populates="creator",
    )

    created_teams: Mapped[list["Team"]] = relationship(
        back_populates="creator",
    )

    team_memberships: Mapped[list["TeamMember"]] = relationship(
        back_populates="user",
        cascade=CASCADE_ALL_DELETE_ORPHAN,
    )

    project_memberships: Mapped[list["ProjectMember"]] = relationship(
        back_populates="user",
        cascade=CASCADE_ALL_DELETE_ORPHAN,
    )

    comments: Mapped[list["Comment"]] = relationship(
        back_populates="user",
        cascade=CASCADE_ALL_DELETE_ORPHAN, 
    )

    uploaded_attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="uploader",
    )