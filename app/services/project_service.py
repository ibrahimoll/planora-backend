from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.user import User
from app.schemas.activity_log_schema import ActivityLogEventType
from app.schemas.project_schema import (
    ProjectCreate,
    ProjectMemberRole,
    ProjectStatus,
    ProjectUpdate,
    TeamProjectCreate,
)
from app.schemas.project_schema import (
    ProjectAssignableRole,
    ProjectCreate,
    ProjectMemberRole,
    ProjectStatus,
    ProjectUpdate,
    TeamProjectCreate,
)
from app.services.activity_log_service import create_activity_log


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
    db.flush()

    create_activity_log(
        db=db,
        project=project,
        actor=current_user,
        event_type=ActivityLogEventType.PROJECT_CREATED,
        message=f"{current_user.full_name} created project '{project.title}'.",
        metadata={
            "project_type": project.project_type,
            "status": project.status,
        },
        commit=False,
    )

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
    current_user: User,
) -> Project:
    update_data = project_data.model_dump(exclude_unset=True)

    changed_fields: list[str] = []

    for field, value in update_data.items():
        old_value = getattr(project, field)

        if field == "status" and value is not None:
            new_value = value.value
            setattr(project, field, new_value)
        else:
            new_value = value
            setattr(project, field, value)

        if old_value != new_value:
            changed_fields.append(field)

    if changed_fields:
        create_activity_log(
            db=db,
            project=project,
            actor=current_user,
            event_type=ActivityLogEventType.PROJECT_UPDATED,
            message=f"{current_user.full_name} updated project '{project.title}'.",
            metadata={
                "changed_fields": changed_fields,
            },
            commit=False,
        )

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
        created_by=current_user.user_id,
        team_id=team.team_id,
        title=project_data.title,
        description=project_data.description,
        deadline=project_data.deadline,
        status=ProjectStatus.not_started.value,
        project_type="team",
    )

    db.add(project)
    db.flush()

    stmt = (
        select(TeamMember)
        .where(TeamMember.team_id == team.team_id)
        .order_by(TeamMember.joined_at.asc())
    )

    team_members = list(db.execute(stmt).scalars().all())

    for team_member in team_members:
        if team_member.user_id == current_user.user_id:
            project_role = ProjectMemberRole.owner.value
        elif team_member.role in {"owner", "admin"}:
            project_role = ProjectMemberRole.manager.value
        else:
            project_role = ProjectMemberRole.member.value

        project_member = ProjectMember(
            project_id=project.project_id,
            user_id=team_member.user_id,
            role=project_role,
        )

        db.add(project_member)

    create_activity_log(
        db=db,
        project=project,
        actor=current_user,
        event_type=ActivityLogEventType.PROJECT_CREATED,
        message=f"{current_user.full_name} created team project '{project.title}'.",
        metadata={
            "project_type": project.project_type,
            "team_id": team.team_id,
            "status": project.status,
        },
        commit=False,
    )

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
        Project.project_type == "team",
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
    current_user: User,
) -> Project:
    update_data = project_data.model_dump(exclude_unset=True)

    changed_fields: list[str] = []

    for field, value in update_data.items():
        old_value = getattr(project, field)

        if field == "status" and value is not None:
            new_value = value.value
            setattr(project, field, new_value)
        else:
            new_value = value
            setattr(project, field, value)

        if old_value != new_value:
            changed_fields.append(field)

    if changed_fields:
        create_activity_log(
            db=db,
            project=project,
            actor=current_user,
            event_type=ActivityLogEventType.PROJECT_UPDATED,
            message=f"{current_user.full_name} updated project '{project.title}'.",
            metadata={
                "changed_fields": changed_fields,
            },
            commit=False,
        )

    db.commit()
    db.refresh(project)

    return project


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
    return membership.role in {
        ProjectMemberRole.owner.value,
        ProjectMemberRole.manager.value,
    }


def is_project_owner(
    membership: ProjectMember,
) -> bool:
    return membership.role == ProjectMemberRole.owner.value


def update_project_member_role(
    db: Session,
    member: ProjectMember,
    role: ProjectAssignableRole,
) -> ProjectMember:
    member.role = role.value

    db.commit()
    db.refresh(member)

    return member