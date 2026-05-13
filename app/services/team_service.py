from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.user import User
from app.schemas.team_schema import TeamCreate, TeamRole, TeamUpdate


def create_team(
    db: Session,
    team_data: TeamCreate,
    current_user: User,
) -> Team:
    team = Team(
        name=team_data.name,
        created_by=current_user.user_id,
    )

    db.add(team)
    db.flush()

    owner_member = TeamMember(
        team_id=team.team_id,
        user_id=current_user.user_id,
        role=TeamRole.owner.value,
    )

    db.add(owner_member)
    db.commit()
    db.refresh(team)

    return team


def get_my_teams(
    db: Session,
    current_user: User,
) -> list[Team]:
    stmt = (
        select(Team)
        .join(TeamMember, TeamMember.team_id == Team.team_id)
        .where(TeamMember.user_id == current_user.user_id)
        .order_by(Team.created_at.desc())
    )

    return list(db.execute(stmt).scalars().all())


def get_team_by_id(
    db: Session,
    team_id: int,
) -> Team | None:
    stmt = select(Team).where(Team.team_id == team_id)

    return db.execute(stmt).scalars().first()


def get_team_membership(
    db: Session,
    team_id: int,
    user_id: int,
) -> TeamMember | None:
    stmt = select(TeamMember).where(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id,
    )

    return db.execute(stmt).scalars().first()


def is_team_member(
    db: Session,
    team_id: int,
    user_id: int,
) -> bool:
    return get_team_membership(
        db=db,
        team_id=team_id,
        user_id=user_id,
    ) is not None


def can_manage_team(
    membership: TeamMember,
) -> bool:
    return membership.role in {
        TeamRole.owner.value,
        TeamRole.admin.value,
    }


def is_team_owner(
    membership: TeamMember,
) -> bool:
    return membership.role == TeamRole.owner.value


def update_team(
    db: Session,
    team: Team,
    team_data: TeamUpdate,
) -> Team:
    update_data = team_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(team, field, value)

    db.commit()
    db.refresh(team)

    return team


def delete_team(
    db: Session,
    team: Team,
) -> None:
    db.delete(team)
    db.commit()


def get_team_members(
    db: Session,
    team_id: int,
) -> list[TeamMember]:
    stmt = (
        select(TeamMember)
        .where(TeamMember.team_id == team_id)
        .order_by(TeamMember.joined_at.asc())
    )

    return list(db.execute(stmt).scalars().all())


def get_user_by_email(
    db: Session,
    email: str,
) -> User | None:
    stmt = select(User).where(User.email == email)

    return db.execute(stmt).scalars().first()


def add_team_member(
    db: Session,
    team: Team,
    user: User,
    role: TeamRole,
) -> TeamMember:
    member = TeamMember(
        team_id=team.team_id,
        user_id=user.user_id,
        role=role.value,
    )

    db.add(member)
    db.commit()
    db.refresh(member)

    return member


def update_team_member_role(
    db: Session,
    member: TeamMember,
    role: TeamRole,
) -> TeamMember:
    member.role = role.value

    db.commit()
    db.refresh(member)

    return member


def remove_team_member(
    db: Session,
    member: TeamMember,
) -> None:
    team_project_ids = select(Project.project_id).where(
        Project.team_id == member.team_id,
        Project.project_type == "team",
    )

    db.execute(
        delete(ProjectMember).where(
            ProjectMember.user_id == member.user_id,
            ProjectMember.project_id.in_(team_project_ids),
        )
    )
    db.delete(member)
    db.commit()
