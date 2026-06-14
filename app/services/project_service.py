from __future__ import annotations

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.user import User
from app.schemas.activity_log_schema import ActivityLogEventType
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

    owner_member = ProjectMember(
        project_id=project.project_id,
        user_id=current_user.user_id,
        role=ProjectMemberRole.owner.value,
    )

    db.add(owner_member)

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
    repair_accessible_personal_projects_with_multiple_members(
        db=db,
        current_user=current_user,
    )

    member_exists = (
        select(ProjectMember.member_id)
        .where(
            ProjectMember.project_id == Project.project_id,
            ProjectMember.user_id == current_user.user_id,
        )
        .exists()
    )
    stmt = select(Project).where(
        Project.project_type == "personal",
        or_(
            Project.created_by == current_user.user_id,
            member_exists,
        ),
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
    member_exists = (
        select(ProjectMember.member_id)
        .where(
            ProjectMember.project_id == Project.project_id,
            ProjectMember.user_id == current_user.user_id,
        )
        .exists()
    )
    stmt = select(Project).where(
        Project.project_id == project_id,
        Project.project_type == "personal",
        or_(
            Project.created_by == current_user.user_id,
            member_exists,
        ),
    )

    project = db.execute(stmt).scalars().first()

    if project is None:
        return None

    return repair_personal_project_with_multiple_members(db=db, project=project)


def get_owned_personal_project_by_id(
    db: Session,
    project_id: int,
    current_user: User,
) -> Project | None:
    stmt = select(Project).where(
        Project.project_id == project_id,
        Project.project_type == "personal",
        Project.created_by == current_user.user_id,
    )

    return db.execute(stmt).scalars().first()


def get_manageable_personal_project_by_id(
    db: Session,
    project_id: int,
    current_user: User,
) -> Project | None:
    project = get_my_personal_project_by_id(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        return None

    if project.project_type != "personal":
        return None

    if project.created_by == current_user.user_id:
        return project

    membership = get_project_membership(
        db=db,
        project_id=project_id,
        user_id=current_user.user_id,
    )

    if membership is not None and can_manage_project(membership):
        return project

    return None


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
        .options(selectinload(ProjectMember.user))
        .where(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.joined_at.asc())
    )

    return list(db.execute(stmt).scalars().all())


def get_user_by_email_or_username(
    db: Session,
    email_or_username: str,
) -> User | None:
    lookup = email_or_username.strip().lower()

    stmt = select(User).where(
        func.lower(User.email) == lookup,
    )

    user = db.execute(stmt).scalars().first()

    if user is not None:
        return user

    stmt = select(User).where(
        func.lower(User.username) == lookup,
    )

    return db.execute(stmt).scalars().first()


def add_project_member(
    db: Session,
    project: Project,
    user: User,
    role: ProjectAssignableRole,
) -> ProjectMember:
    member = ProjectMember(
        project_id=project.project_id,
        user_id=user.user_id,
        role=role.value,
    )

    db.add(member)
    db.commit()
    db.refresh(member)
    db.refresh(member, attribute_names=["user"])

    return member


def _team_role_for_project_membership(
    membership: ProjectMember,
    project_owner_id: int,
) -> str:
    if membership.user_id == project_owner_id:
        return "owner"

    if membership.role == ProjectMemberRole.owner.value:
        return "admin"

    if membership.role == ProjectMemberRole.manager.value:
        return "admin"

    return "member"


def repair_personal_project_with_multiple_members(
    db: Session,
    project: Project,
) -> Project:
    if project.project_type != "personal":
        return project

    project_members = get_project_members(
        db=db,
        project_id=project.project_id,
    )
    unique_member_ids = {member.user_id for member in project_members}

    if len(unique_member_ids) <= 1:
        return project

    owner_id = project.created_by
    owner_membership = next(
        (member for member in project_members if member.user_id == owner_id),
        None,
    )

    if owner_membership is None:
        owner_membership = ProjectMember(
            project_id=project.project_id,
            user_id=owner_id,
            role=ProjectMemberRole.owner.value,
        )
        db.add(owner_membership)
        db.flush()
        project_members.append(owner_membership)
    elif owner_membership.role != ProjectMemberRole.owner.value:
        owner_membership.role = ProjectMemberRole.owner.value

    team = Team(
        name=f"{project.title} Team"[:100],
        created_by=owner_id,
    )
    db.add(team)
    db.flush()

    team_member_roles: dict[int, str] = {}

    for membership in project_members:
        team_member_roles[membership.user_id] = _team_role_for_project_membership(
            membership=membership,
            project_owner_id=owner_id,
        )

    team_member_roles[owner_id] = "owner"

    for user_id, team_role in team_member_roles.items():
        db.add(
            TeamMember(
                team_id=team.team_id,
                user_id=user_id,
                role=team_role,
            )
        )

    project.team_id = team.team_id
    project.project_type = "team"

    actor = db.get(User, owner_id)
    if actor is not None:
        create_activity_log(
            db=db,
            project=project,
            actor=actor,
            event_type=ActivityLogEventType.PROJECT_UPDATED,
            message=(
                f"{actor.full_name} converted project '{project.title}' "
                "to a team project because it already had collaborators."
            ),
            metadata={
                "project_type": project.project_type,
                "team_id": team.team_id,
                "repair": "personal_project_with_multiple_members",
                "member_count": len(team_member_roles),
            },
            commit=False,
        )

    db.commit()
    db.refresh(project)

    return project


def repair_accessible_personal_projects_with_multiple_members(
    db: Session,
    current_user: User,
) -> None:
    member_exists = (
        select(ProjectMember.member_id)
        .where(
            ProjectMember.project_id == Project.project_id,
            ProjectMember.user_id == current_user.user_id,
        )
        .exists()
    )
    member_count = (
        select(func.count(ProjectMember.member_id))
        .where(ProjectMember.project_id == Project.project_id)
        .correlate(Project)
        .scalar_subquery()
    )
    stmt = select(Project).where(
        Project.project_type == "personal",
        member_count > 1,
        or_(
            Project.created_by == current_user.user_id,
            member_exists,
        ),
    )

    for project in db.execute(stmt).scalars().all():
        repair_personal_project_with_multiple_members(db=db, project=project)


def convert_personal_project_to_team_and_invite(
    db: Session,
    project: Project,
    current_user: User,
    user_to_add: User,
    role: ProjectAssignableRole,
) -> Project:
    existing_project_memberships = get_project_members(
        db=db,
        project_id=project.project_id,
    )
    team_name = f"{project.title} Team"
    team = Team(
        name=team_name[:100],
        created_by=current_user.user_id,
    )

    db.add(team)
    db.flush()

    team_member_roles: dict[int, str] = {
        current_user.user_id: "owner",
        user_to_add.user_id: "member",
    }

    for membership in existing_project_memberships:
        if membership.user_id == current_user.user_id:
            team_member_roles[membership.user_id] = "owner"
        elif membership.role == ProjectMemberRole.manager.value:
            team_member_roles.setdefault(membership.user_id, "admin")
        else:
            team_member_roles.setdefault(membership.user_id, "member")

    for user_id, team_role in team_member_roles.items():
        db.add(
            TeamMember(
                team_id=team.team_id,
                user_id=user_id,
                role=team_role,
            )
        )

    owner_project_membership = get_project_membership(
        db=db,
        project_id=project.project_id,
        user_id=current_user.user_id,
    )

    if owner_project_membership is None:
        db.add(
            ProjectMember(
                project_id=project.project_id,
                user_id=current_user.user_id,
                role=ProjectMemberRole.owner.value,
            )
        )
    elif owner_project_membership.role != ProjectMemberRole.owner.value:
        owner_project_membership.role = ProjectMemberRole.owner.value

    invited_project_member = ProjectMember(
        project_id=project.project_id,
        user_id=user_to_add.user_id,
        role=role.value,
    )
    db.add(invited_project_member)

    project.team_id = team.team_id
    project.project_type = "team"

    create_activity_log(
        db=db,
        project=project,
        actor=current_user,
        event_type=ActivityLogEventType.PROJECT_UPDATED,
        message=(
            f"{current_user.full_name} converted project '{project.title}' "
            "to a team project."
        ),
        metadata={
            "project_type": project.project_type,
            "team_id": team.team_id,
            "invited_user_id": user_to_add.user_id,
        },
        commit=False,
    )

    db.commit()
    db.refresh(project)

    return project


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


def remove_project_member(
    db: Session,
    member: ProjectMember,
) -> None:
    db.delete(member)
    db.commit()
