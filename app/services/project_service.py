from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.user import User
from app.schemas.project_schema import ProjectCreate, ProjectStatus, ProjectUpdate


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