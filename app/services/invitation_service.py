from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.invitation import Invitation
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.user import User
from app.schemas.invitation_schema import TeamInvitationCreate
from app.schemas.notification_schema import NotificationType
from app.services.notification_service import create_notification


def get_user_by_username(
    db: Session,
    username: str,
) -> User | None:
    stmt = select(User).where(User.username == username)

    return db.execute(stmt).scalars().first()


def get_pending_team_invitation(
    db: Session,
    team_id: int,
    invited_user_id: int,
) -> Invitation | None:
    stmt = select(Invitation).where(
        Invitation.team_id == team_id,
        Invitation.project_id.is_(None),
        Invitation.invited_user_id == invited_user_id,
        Invitation.status == "pending",
    )

    return db.execute(stmt).scalars().first()


def create_team_invitation(
    db: Session,
    team: Team,
    invited_user: User,
    inviter: User,
    invitation_data: TeamInvitationCreate,
) -> Invitation:
    invitation = Invitation(
        invited_by=inviter.user_id,
        invited_user_id=invited_user.user_id,
        email=None,
        team_id=team.team_id,
        project_id=None,
        role=invitation_data.role.value,
        status="pending",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )

    db.add(invitation)
    db.flush()

    create_notification(
        db=db,
        user_id=invited_user.user_id,
        title="New team invitation",
        message=f"{inviter.full_name} invited you to join {team.name}.",
        notification_type=NotificationType.INVITE,
        commit=False,
    )

    db.commit()
    db.refresh(invitation)

    return invitation


def get_my_pending_invitations(
    db: Session,
    current_user: User,
) -> list[Invitation]:
    stmt = (
        select(Invitation)
        .where(
            Invitation.invited_user_id == current_user.user_id,
            Invitation.status == "pending",
        )
        .order_by(Invitation.created_at.desc())
    )

    return list(db.execute(stmt).scalars().all())


def get_invitation_by_id(
    db: Session,
    invitation_id: int,
) -> Invitation | None:
    stmt = select(Invitation).where(
        Invitation.invitation_id == invitation_id,
    )

    return db.execute(stmt).scalars().first()


def is_invitation_expired(
    invitation: Invitation,
) -> bool:
    return invitation.expires_at <= datetime.now(UTC)


def mark_invitation_as_expired(
    db: Session,
    invitation: Invitation,
) -> Invitation:
    invitation.status = "expired"
    invitation.responded_at = datetime.now(UTC)

    db.commit()
    db.refresh(invitation)

    return invitation


def accept_team_invitation(
    db: Session,
    invitation: Invitation,
    current_user: User,
) -> Invitation:
    member = TeamMember(
        team_id=invitation.team_id,
        user_id=current_user.user_id,
        role=invitation.role,
    )

    db.add(member)

    team_project_stmt = select(Project).where(
        Project.team_id == invitation.team_id,
        Project.project_type == "team",
    )

    team_projects = list(db.execute(team_project_stmt).scalars().all())

    for project in team_projects:
        existing_project_member_stmt = select(ProjectMember).where(
            ProjectMember.project_id == project.project_id,
            ProjectMember.user_id == current_user.user_id,
        )

        existing_project_member = (
            db.execute(existing_project_member_stmt)
            .scalars()
            .first()
        )

        if existing_project_member is None:
            project_member = ProjectMember(
                project_id=project.project_id,
                user_id=current_user.user_id,
                role="member",
            )
            db.add(project_member)

    invitation.status = "accepted"
    invitation.responded_at = datetime.now(UTC)

    create_notification(
        db=db,
        user_id=invitation.invited_by,
        title="Team invitation accepted",
        message=f"{current_user.full_name} accepted your team invitation.",
        notification_type=NotificationType.INVITE,
        commit=False,
    )

    db.commit()
    db.refresh(invitation)

    return invitation


def reject_team_invitation(
    db: Session,
    invitation: Invitation,
    current_user: User,
) -> Invitation:
    invitation.status = "rejected"
    invitation.responded_at = datetime.now(UTC)

    create_notification(
        db=db,
        user_id=invitation.invited_by,
        title="Team invitation rejected",
        message=f"{current_user.full_name} rejected your team invitation.",
        notification_type=NotificationType.INVITE,
        commit=False,
    )

    db.commit()
    db.refresh(invitation)

    return invitation