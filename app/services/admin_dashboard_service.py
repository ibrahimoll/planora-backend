from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.admin_log import AdminLog
from app.models.notification import Notification
from app.models.project import Project
from app.models.risk_analysis import RiskAnalysis
from app.models.task import Task
from app.models.team import Team
from app.models.user import User
from app.schemas.admin_dashboard_schema import (
    AdminDashboardOverviewResponse,
    AdminNotificationStats,
    AdminProjectStats,
    AdminRiskStats,
    AdminTaskStats,
    AdminUserStats,
)


def count_query(db: Session, stmt: Select[tuple[int]]) -> int:
    value = db.scalar(stmt)
    return int(value or 0)


def count_all(db: Session, model: type) -> int:
    return count_query(
        db,
        select(func.count()).select_from(model),
    )


def count_where(db: Session, model: type, *conditions) -> int:
    stmt = select(func.count()).select_from(model)

    if conditions:
        stmt = stmt.where(*conditions)

    return count_query(db, stmt)


def get_admin_dashboard_overview(
    db: Session,
) -> AdminDashboardOverviewResponse:
    now = datetime.now(timezone.utc)

    total_users = count_all(db, User)
    active_users = count_where(db, User, User.is_active.is_(True))
    verified_users = count_where(db, User, User.is_email_verified.is_(True))
    admin_users = count_where(db, User, User.role == "admin")

    total_projects = count_all(db, Project)
    total_tasks = count_all(db, Task)

    total_notifications = count_all(db, Notification)
    unread_notifications = count_where(
        db,
        Notification,
        Notification.is_read.is_(False),
    )

    return AdminDashboardOverviewResponse(
        users=AdminUserStats(
            total_users=total_users,
            active_users=active_users,
            inactive_users=total_users - active_users,
            verified_users=verified_users,
            unverified_users=total_users - verified_users,
            admin_users=admin_users,
        ),
        projects=AdminProjectStats(
            total_projects=total_projects,
            personal_projects=count_where(
                db,
                Project,
                Project.project_type == "personal",
            ),
            team_projects=count_where(
                db,
                Project,
                Project.project_type == "team",
            ),
            not_started_projects=count_where(
                db,
                Project,
                Project.status == "not_started",
            ),
            in_progress_projects=count_where(
                db,
                Project,
                Project.status == "in_progress",
            ),
            completed_projects=count_where(
                db,
                Project,
                Project.status == "completed",
            ),
            on_hold_projects=count_where(
                db,
                Project,
                Project.status == "on_hold",
            ),
            cancelled_projects=count_where(
                db,
                Project,
                Project.status == "cancelled",
            ),
        ),
        tasks=AdminTaskStats(
            total_tasks=total_tasks,
            todo_tasks=count_where(db, Task, Task.status == "todo"),
            in_progress_tasks=count_where(
                db,
                Task,
                Task.status == "in_progress",
            ),
            completed_tasks=count_where(db, Task, Task.status == "completed"),
            blocked_tasks=count_where(db, Task, Task.status == "blocked"),
            overdue_tasks=count_where(
                db,
                Task,
                Task.status != "completed",
                Task.due_date.is_not(None),
                Task.due_date < now,
            ),
        ),
        teams_total=count_all(db, Team),
        risks=AdminRiskStats(
            total_risk_records=count_all(db, RiskAnalysis),
            low_risk_records=count_where(
                db,
                RiskAnalysis,
                RiskAnalysis.risk_level == "low",
            ),
            medium_risk_records=count_where(
                db,
                RiskAnalysis,
                RiskAnalysis.risk_level == "medium",
            ),
            high_risk_records=count_where(
                db,
                RiskAnalysis,
                RiskAnalysis.risk_level == "high",
            ),
        ),
        notifications=AdminNotificationStats(
            total_notifications=total_notifications,
            unread_notifications=unread_notifications,
            read_notifications=total_notifications - unread_notifications,
        ),
        generated_at=now,
    )


def get_admin_users(
    db: Session,
    limit: int,
    offset: int,
) -> list[User]:
    stmt = (
        select(User)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    return list(db.execute(stmt).scalars().all())


def get_recent_activity_logs(
    db: Session,
    limit: int,
) -> list[ActivityLog]:
    stmt = (
        select(ActivityLog)
        .order_by(ActivityLog.created_at.desc())
        .limit(limit)
    )

    return list(db.execute(stmt).scalars().all())


def get_admin_logs(
    db: Session,
    limit: int,
) -> list[AdminLog]:
    stmt = (
        select(AdminLog)
        .order_by(AdminLog.created_at.desc())
        .limit(limit)
    )

    return list(db.execute(stmt).scalars().all())


def create_admin_log(
    db: Session,
    admin_id: int,
    action: str,
    target_user_id: int | None = None,
) -> AdminLog:
    log = AdminLog(
        admin_id=admin_id,
        target_user_id=target_user_id,
        action=action,
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return log