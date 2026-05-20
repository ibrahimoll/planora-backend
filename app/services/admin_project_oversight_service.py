from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.admin_log import AdminLog
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.risk_analysis import RiskAnalysis
from app.models.task import Task
from app.models.team import Team
from app.models.user import User
from app.schemas.admin_project_oversight_schema import (
    AdminProjectDetailResponse,
    AdminProjectOwnerResponse,
    AdminProjectRiskResponse,
    AdminProjectStatusUpdateResponse,
    AdminProjectSummaryResponse,
    AdminProjectTaskStatsResponse,
    AdminProjectTeamResponse,
    AdminProjectListResponse,
)


def _count_query(db: Session, stmt) -> int:
    value = db.scalar(stmt)
    return int(value or 0)


def _count_where(db: Session, model: type, *conditions) -> int:
    stmt = select(func.count()).select_from(model)

    if conditions:
        stmt = stmt.where(*conditions)

    return _count_query(db, stmt)


def _count_select(db: Session, stmt) -> int:
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    return _count_query(db, count_stmt)

def _get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    return project


def _get_project_owner(db: Session, project: Project) -> AdminProjectOwnerResponse:
    owner = db.get(User, project.created_by)

    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project owner is missing.",
        )

    return AdminProjectOwnerResponse(
        user_id=owner.user_id,
        username=owner.username,
        email=owner.email,
        full_name=owner.full_name,
    )


def _get_project_team(
    db: Session,
    project: Project,
) -> AdminProjectTeamResponse | None:
    if project.team_id is None:
        return None

    team = db.get(Team, project.team_id)

    if team is None:
        return None

    return AdminProjectTeamResponse(
        team_id=team.team_id,
        name=team.name,
        created_by=team.created_by,
    )


def _get_latest_risk(
    db: Session,
    project_id: int,
) -> AdminProjectRiskResponse | None:
    stmt = (
        select(RiskAnalysis)
        .where(RiskAnalysis.project_id == project_id)
        .order_by(RiskAnalysis.created_at.desc())
        .limit(1)
    )

    risk = db.scalar(stmt)

    if risk is None:
        return None

    return AdminProjectRiskResponse(
        risk_id=risk.risk_id,
        risk_level=risk.risk_level,
        predicted_delay_days=risk.predicted_delay_days,
        created_at=risk.created_at,
    )


def _get_task_stats(
    db: Session,
    project_id: int,
) -> AdminProjectTaskStatsResponse:
    now = datetime.now(timezone.utc)

    total_tasks = _count_where(
        db,
        Task,
        Task.project_id == project_id,
    )

    completed_tasks = _count_where(
        db,
        Task,
        Task.project_id == project_id,
        Task.status == "completed",
    )

    completion_percentage = 0.0
    if total_tasks > 0:
        completion_percentage = round((completed_tasks / total_tasks) * 100, 2)

    return AdminProjectTaskStatsResponse(
        total_tasks=total_tasks,
        todo_tasks=_count_where(
            db,
            Task,
            Task.project_id == project_id,
            Task.status == "todo",
        ),
        in_progress_tasks=_count_where(
            db,
            Task,
            Task.project_id == project_id,
            Task.status == "in_progress",
        ),
        completed_tasks=completed_tasks,
        blocked_tasks=_count_where(
            db,
            Task,
            Task.project_id == project_id,
            Task.status == "blocked",
        ),
        overdue_tasks=_count_where(
            db,
            Task,
            Task.project_id == project_id,
            Task.status != "completed",
            Task.due_date.is_not(None),
            Task.due_date < now,
        ),
        completion_percentage=completion_percentage,
    )


def _build_project_summary(
    db: Session,
    project: Project,
) -> AdminProjectSummaryResponse:
    return AdminProjectSummaryResponse(
        project_id=project.project_id,
        title=project.title,
        deadline=project.deadline,
        status=project.status,
        project_type=project.project_type,
        created_at=project.created_at,
        updated_at=project.updated_at,
        owner=_get_project_owner(db=db, project=project),
        team=_get_project_team(db=db, project=project),
        task_stats=_get_task_stats(db=db, project_id=project.project_id),
        latest_risk=_get_latest_risk(db=db, project_id=project.project_id),
    )


def _build_project_detail(
    db: Session,
    project: Project,
) -> AdminProjectDetailResponse:
    summary = _build_project_summary(db=db, project=project)

    members_count = _count_where(
        db,
        ProjectMember,
        ProjectMember.project_id == project.project_id,
    )

    return AdminProjectDetailResponse(
        project_id=summary.project_id,
        title=summary.title,
        description=project.description,
        deadline=summary.deadline,
        status=summary.status,
        project_type=summary.project_type,
        created_at=summary.created_at,
        updated_at=summary.updated_at,
        owner=summary.owner,
        team=summary.team,
        task_stats=summary.task_stats,
        latest_risk=summary.latest_risk,
        members_count=members_count,
    )


def get_admin_projects(
    db: Session,
    limit: int,
    offset: int,
    project_type: str | None = None,
    status_filter: str | None = None,
    owner_id: int | None = None,
    team_id: int | None = None,
    search: str | None = None,
) -> AdminProjectListResponse:
    stmt = select(Project)

    if project_type is not None:
        stmt = stmt.where(Project.project_type == project_type)

    if status_filter is not None:
        stmt = stmt.where(Project.status == status_filter)

    if owner_id is not None:
        stmt = stmt.where(Project.created_by == owner_id)

    if team_id is not None:
        stmt = stmt.where(Project.team_id == team_id)

    if search is not None and search.strip():
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Project.title.ilike(pattern),
                Project.description.ilike(pattern),
            )
        )

    total = _count_select(db, stmt)

    projects = list(
        db.execute(
            stmt.order_by(Project.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        .scalars()
        .all()
    )

    return AdminProjectListResponse(
        items=[
            _build_project_summary(db=db, project=project)
            for project in projects
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


def get_admin_project_detail(
    db: Session,
    project_id: int,
) -> AdminProjectDetailResponse:
    project = _get_project_or_404(db=db, project_id=project_id)
    return _build_project_detail(db=db, project=project)


def update_project_status_by_admin(
    db: Session,
    admin: User,
    project_id: int,
    new_status: str,
) -> AdminProjectStatusUpdateResponse:
    project = _get_project_or_404(db=db, project_id=project_id)
    old_status = project.status

    project.status = new_status
    project.updated_at = datetime.now(timezone.utc)

    log = AdminLog(
        admin_id=admin.user_id,
        target_user_id=project.created_by,
        action=(
            f"changed_project_status:project_id={project.project_id}:"
            f"old_status={old_status}:new_status={new_status}"
        ),
    )

    db.add(log)
    db.commit()
    db.refresh(project)
    db.refresh(log)

    return AdminProjectStatusUpdateResponse(
        message="Project status updated successfully.",
        project=_build_project_detail(db=db, project=project),
        admin_log_id=log.log_id,
    )