from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.user import User
from app.schemas.project_schema import(
    ProjectCreate,
    ProjectMemberRole,
    ProjectStatus,
    ProjectUpdate,
    TeamProjectCreate,
)


def create_personal_project(
    db: Session,
    project_data: ProjectCreate,
    current_user: User,
) -> Project:
    project = Project(
        created_by=current_user.user_id,
        team_id=None,
        title=project_data.title,
        description=project_data.description,
        deadline=project_data.deadline,
        status=ProjectStatus.not_started.value,
        project_type="personal",
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return project


def get_my_personal_projects(
    db: Session,
    current_user: User,
    status: ProjectStatus | None = None,
) -> list[Project]:
    stmt = select(Project).where(
        Project.created_by == current_user.user_id,
        Project.project_type == "personal",
    )

    if status is not None:
        stmt = stmt.where(Project.status == status.value)

    stmt = stmt.order_by(Project.created_at.desc())

    return list(db.execute(stmt).scalars().all())


def get_my_personal_project_by_id(
    db: Session,
    project_id: int,
    current_user: User,
) -> Project | None:
    stmt = select(Project).where(
        Project.project_id == project_id,
        Project.created_by == current_user.user_id,
        Project.project_type == "personal",
    )

    return db.execute(stmt).scalars().first()


def update_my_personal_project(
    db: Session,
    project: Project,
    project_data: ProjectUpdate,
) -> Project:
    update_data = project_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "status" and value is not None:
            setattr(project, field, value.value)
        else:
            setattr(project, field, value)

    db.commit()
    db.refresh(project)

    return project


def delete_my_personal_project(
    db: Session,
    project: Project,
) -> None:
    db.delete(project)
    db.commit()

def create_team_project(
        db: Session,
        team: Team,
        project_data: TeamProjectCreate,
        current_user: User,
) -> Project:
    project = Project(
        created_by = current_user.user_id,
        team_id = team.team_id,
        title = project_data.title,
        description = project_data.description,
        deadline = project_data.deadline,
        status=ProjectStatus.not_started.value,
        project_type = "team",
    )

    db.add(project)
    db.flush()

    stmt = (
        select(TeamMember)
        .where(TeamMember.team_id == team.team_id)
        .order_by(TeamMember.joined_at.asc())
    )

    team_members = list(db.execute(stmt).scalars().all())

    for team_members in team_members:
        if team_members.user_id == current_user.user_id:
            project_role = ProjectMemberRole.owner.value
        elif team_members.role in {"owner", "admin"}:
            project_role = ProjectMemberRole.manager.value
        else:
            project_role = ProjectMemberRole.member.value

        project_member = ProjectMember(
            project_id=project.project_id,
            user_id=team_members.user_id,
            role=project_role,
        )

        db.add(project_member)
    db.commit()
    db.refresh(project)

    return project

def get_team_projects(
        db: Session,
        team_id: int,
        status: ProjectStatus | None = None,
) -> list[Project]:
    stmt = select(Project).where(
        Project.team_id == team_id,
        Project.project_type == " team",
    )

    if status is not None:
        stmt = stmt.where(Project.status == status.value)

    stmt = stmt.order_by(Project.created_at.desc())

    return list(db.execute(stmt).scalars().all())

def get_team_project_by_id(
    db: Session,
    team_id: int,
    project_id: int,
) -> Project | None:
    stmt = select(Project).where(
        Project.project_id == project_id,
        Project.team_id == team_id,
        Project.project_type == "team",
    )

    return db.execute(stmt).scalars().first()

def update_team_project(
        db: Session,
        project: Project,
        project_data: ProjectUpdate,
) -> Project:
    update_data = project_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "status" and value is not None:
            setattr(project, field, value.value)
        else:
            setattr(project, field, value)

    db.commit()
    db.refresh(project)

def delete_team_project(
        db: Session,
        project: Project,
) -> None:
    db.delete(project)
    db.commit()

def get_project_members(
        db: Session,
        project_id: int,
) -> list[ProjectMember]:
    stmt = (
        select(ProjectMember)
        .where(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.joined_at.asc())
    )
    return list(db.execute(stmt).scalars().all())

def get_project_membership(
        db: Session,
        project_id: int,
        user_id: int,
) -> ProjectMember | None:
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    )

    return db.execute(stmt).scalars().first()

def can_manage_project(
        membership: ProjectMember,
) -> bool:
    return membership.role in{
        ProjectMemberRole.owner.value,
        ProjectMemberRole.manager.value,
    }

def is_project_owner(
        membership: ProjectMember,
) -> bool:
    return membership.role == ProjectMemberRole.owner.value