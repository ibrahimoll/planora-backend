from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import case, distinct, func, select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.risk_analysis import RiskAnalysis
from app.models.task import Task
from app.models.team import Team
from app.models.user import User
from app.schemas.admin_project_oversight_schema import AdminProjectSummaryResponse
from app.schemas.admin_risk_report_schema import (
    AdminHighRiskProjectResponse,
    AdminProjectSummaryReportResponse,
    AdminRiskCenterSummaryResponse,
    AdminSystemSummaryReportResponse,
    AdminUserSummaryReportResponse,
)
from app.services.admin_project_oversight_service import _build_project_summary


def _count_query(db: Session, stmt) -> int:
    value = db.scalar(stmt)
    return int(value or 0)


def _count_where(db: Session, model: type, *conditions) -> int:
    stmt = select(func.count()).select_from(model)
    if conditions:
        stmt = stmt.where(*conditions)
    return _count_query(db, stmt)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def get_admin_risk_summary(db: Session) -> AdminRiskCenterSummaryResponse:
    now = _now_utc()

    high_project_ids = select(distinct(RiskAnalysis.project_id)).where(RiskAnalysis.risk_level == "high")
    medium_project_ids = select(distinct(RiskAnalysis.project_id)).where(RiskAnalysis.risk_level == "medium")
    low_project_ids = select(distinct(RiskAnalysis.project_id)).where(RiskAnalysis.risk_level == "low")
    any_risk_project_ids = select(distinct(RiskAnalysis.project_id))
    blocked_project_ids = select(distinct(Task.project_id)).where(Task.status == "blocked")

    return AdminRiskCenterSummaryResponse(
        total_projects=_count_where(db, Project),
        projects_with_risk_records=_count_query(db, select(func.count()).select_from(any_risk_project_ids.subquery())),
        high_risk_projects=_count_query(db, select(func.count()).select_from(high_project_ids.subquery())),
        medium_risk_projects=_count_query(db, select(func.count()).select_from(medium_project_ids.subquery())),
        low_risk_projects=_count_query(db, select(func.count()).select_from(low_project_ids.subquery())),
        overdue_active_projects=_count_where(
            db,
            Project,
            Project.status != "completed",
            Project.deadline < now,
        ),
        blocked_task_projects=_count_query(db, select(func.count()).select_from(blocked_project_ids.subquery())),
        generated_at=now,
    )


def get_admin_high_risk_projects(db: Session, limit: int, offset: int) -> list[AdminHighRiskProjectResponse]:
    latest_risk_subquery = (
        select(
            RiskAnalysis.project_id,
            func.max(RiskAnalysis.created_at).label("latest_created_at"),
        )
        .group_by(RiskAnalysis.project_id)
        .subquery()
    )

    stmt = (
        select(RiskAnalysis)
        .join(
            latest_risk_subquery,
            (RiskAnalysis.project_id == latest_risk_subquery.c.project_id)
            & (RiskAnalysis.created_at == latest_risk_subquery.c.latest_created_at),
        )
        .where(RiskAnalysis.risk_level == "high")
        .order_by(RiskAnalysis.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    risks = list(db.execute(stmt).scalars().all())
    responses: list[AdminHighRiskProjectResponse] = []

    for risk in risks:
        project = db.get(Project, risk.project_id)
        if project is None:
            continue
        responses.append(
            AdminHighRiskProjectResponse(
                project=_build_project_summary(db=db, project=project),
                risk_id=risk.risk_id,
                risk_level=risk.risk_level,
                predicted_delay_days=risk.predicted_delay_days,
                reason=risk.reason,
                recommendation=risk.recommendation,
                created_at=risk.created_at,
            )
        )

    return responses


def get_admin_system_summary_report(db: Session) -> AdminSystemSummaryReportResponse:
    now = _now_utc()
    return AdminSystemSummaryReportResponse(
        users_total=_count_where(db, User),
        users_active=_count_where(db, User, User.is_active.is_(True)),
        users_inactive=_count_where(db, User, User.is_active.is_(False)),
        admins_total=_count_where(db, User, User.role == "admin"),
        projects_total=_count_where(db, Project),
        team_projects=_count_where(db, Project, Project.project_type == "team"),
        personal_projects=_count_where(db, Project, Project.project_type == "personal"),
        tasks_total=_count_where(db, Task),
        overdue_tasks=_count_where(db, Task, Task.status != "completed", Task.due_date.is_not(None), Task.due_date < now),
        blocked_tasks=_count_where(db, Task, Task.status == "blocked"),
        high_risk_records=_count_where(db, RiskAnalysis, RiskAnalysis.risk_level == "high"),
        teams_total=_count_where(db, Team),
        generated_at=now,
    )


def get_admin_projects_summary_report(db: Session) -> AdminProjectSummaryReportResponse:
    now = _now_utc()
    projects_total = _count_where(db, Project)

    task_completion_by_project = (
        select(
            Task.project_id.label("project_id"),
            func.count(Task.task_id).label("total_tasks"),
            func.sum(
                case((Task.status == "completed", 1), else_=0)
            ).label("completed_tasks"),
        )
        .group_by(Task.project_id)
        .subquery()
    )

    completion_total = db.scalar(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            task_completion_by_project.c.total_tasks > 0,
                            (task_completion_by_project.c.completed_tasks * 100.0)
                            / task_completion_by_project.c.total_tasks,
                        ),
                        else_=0.0,
                    )
                ),
                0.0,
            )
        )
        .select_from(Project)
        .outerjoin(
            task_completion_by_project,
            Project.project_id == task_completion_by_project.c.project_id,
        )
    )

    return AdminProjectSummaryReportResponse(
        projects_total=projects_total,
        not_started=_count_where(db, Project, Project.status == "not_started"),
        in_progress=_count_where(db, Project, Project.status == "in_progress"),
        completed=_count_where(db, Project, Project.status == "completed"),
        on_hold=_count_where(db, Project, Project.status == "on_hold"),
        cancelled=_count_where(db, Project, Project.status == "cancelled"),
        average_completion_percentage=(
            round(float(completion_total or 0.0) / projects_total, 2)
            if projects_total
            else 0.0
        ),
        generated_at=now,
    )


def get_admin_users_summary_report(db: Session) -> AdminUserSummaryReportResponse:
    assigned_user_ids = select(distinct(Task.assigned_to)).where(Task.assigned_to.is_not(None))
    return AdminUserSummaryReportResponse(
        users_total=_count_where(db, User),
        active_users=_count_where(db, User, User.is_active.is_(True)),
        inactive_users=_count_where(db, User, User.is_active.is_(False)),
        verified_users=_count_where(db, User, User.is_email_verified.is_(True)),
        unverified_users=_count_where(db, User, User.is_email_verified.is_(False)),
        admin_users=_count_where(db, User, User.role == "admin"),
        users_with_assigned_tasks=_count_query(db, select(func.count()).select_from(assigned_user_ids.subquery())),
        generated_at=_now_utc(),
    )
