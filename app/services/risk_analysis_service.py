from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from math import ceil

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.risk_analysis import RiskAnalysis
from app.models.task import Task
from app.models.user import User
from app.schemas.notification_schema import NotificationType
from app.schemas.risk_analysis_schema import RiskAnalysisPreviewResponse, RiskLevel
from app.services.notification_service import (
    create_notification,
    send_push_for_notification,
)

DAILY_WORK_CAPACITY_HOURS = 4.0


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _number_to_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0

    return float(value)


def get_accessible_project_for_risk_analysis(
    db: Session,
    project_id: int,
    current_user: User,
) -> Project | None:
    project = db.get(Project, project_id)

    if project is None:
        return None

    if project.project_type == "personal":
        if project.created_by != current_user.user_id:
            return None

        return project

    membership_stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == current_user.user_id,
    )

    membership = db.execute(membership_stmt).scalars().first()

    if membership is None:
        return None

    return project


def get_project_tasks_for_risk_analysis(
    db: Session,
    project_id: int,
) -> list[Task]:
    stmt = select(Task).where(Task.project_id == project_id)

    return list(db.execute(stmt).scalars().all())


def calculate_risk_preview(
    project: Project,
    tasks: list[Task],
) -> RiskAnalysisPreviewResponse:
    now = datetime.now(timezone.utc)
    deadline = _to_utc(project.deadline)

    total_tasks = len(tasks)
    completed_tasks = len([task for task in tasks if task.status == "completed"])
    blocked_tasks = len([task for task in tasks if task.status == "blocked"])

    overdue_tasks = len(
        [
            task
            for task in tasks
            if task.status != "completed"
            and task.due_date is not None
            and _to_utc(task.due_date) < now
        ]
    )

    remaining_tasks = [
        task
        for task in tasks
        if task.status != "completed"
    ]

    remaining_estimated_hours = sum(
        _number_to_float(task.estimated_hours)
        for task in remaining_tasks
    )

    days_until_deadline = max(
        0,
        ceil((deadline - now).total_seconds() / 86400),
    )

    estimated_needed_days = (
        ceil(remaining_estimated_hours / DAILY_WORK_CAPACITY_HOURS)
        if remaining_estimated_hours > 0
        else 0
    )

    predicted_delay_days = max(
        0,
        estimated_needed_days - days_until_deadline,
    )

    completion_percentage = (
        (completed_tasks / total_tasks) * 100
        if total_tasks > 0
        else 0
    )

    if total_tasks == 0:
        risk_level = RiskLevel.medium
        reason = (
            "The project has no tasks, so the system cannot confirm whether "
            "the work is on track."
        )
        recommendation = (
            "Create tasks for the project, add due dates, and run the risk "
            "analysis again."
        )
    elif deadline < now and completed_tasks < total_tasks:
        risk_level = RiskLevel.high
        reason = "The project deadline has passed while some tasks are still incomplete."
        recommendation = (
            "Update the project deadline or immediately complete the remaining "
            "high-priority tasks."
        )
    elif overdue_tasks > 0 or blocked_tasks >= 2 or predicted_delay_days >= 3:
        risk_level = RiskLevel.high
        reason = (
            "The project has overdue tasks, blocked work, or the remaining workload "
            "is too large for the available time."
        )
        recommendation = (
            "Focus on overdue and blocked tasks first, reduce scope, or extend "
            "the deadline."
        )
    elif completion_percentage < 50 and days_until_deadline <= 3:
        risk_level = RiskLevel.high
        reason = "Less than half of the tasks are completed and the deadline is very close."
        recommendation = (
            "Complete high-priority tasks first and move non-essential work to "
            "a later phase."
        )
    elif overdue_tasks == 0 and blocked_tasks == 0 and predicted_delay_days == 0:
        risk_level = RiskLevel.low
        reason = (
            "The project has no overdue or blocked tasks and the remaining work "
            "fits within the deadline."
        )
        recommendation = "Keep monitoring progress and continue completing tasks as planned."
    else:
        risk_level = RiskLevel.medium
        reason = (
            "The project is mostly stable, but some progress or workload indicators "
            "need attention."
        )
        recommendation = (
            "Review remaining tasks, adjust priorities, and keep the deadline "
            "under observation."
        )

    return RiskAnalysisPreviewResponse(
        project_id=project.project_id,
        risk_level=risk_level,
        predicted_delay_days=predicted_delay_days,
        reason=reason,
        recommendation=recommendation,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        overdue_tasks=overdue_tasks,
        blocked_tasks=blocked_tasks,
        remaining_estimated_hours=round(remaining_estimated_hours, 2),
        days_until_deadline=days_until_deadline,
    )


def get_risk_notification_user_ids(
    db: Session,
    project: Project,
) -> list[int]:
    if project.project_type == "personal":
        return [project.created_by]

    stmt = select(ProjectMember.user_id).where(
        ProjectMember.project_id == project.project_id,
    )

    return sorted(set(db.execute(stmt).scalars().all()))


def create_high_risk_notifications(
    db: Session,
    project: Project,
    risk_analysis: RiskAnalysis,
) -> list[Notification]:
    user_ids = get_risk_notification_user_ids(
        db=db,
        project=project,
    )

    title = "High project risk detected"
    message = (
        f"Project '{project.title}' is currently high risk. "
        f"Predicted delay: {risk_analysis.predicted_delay_days} day(s). "
        f"Recommendation: {risk_analysis.recommendation}"
    )

    notifications: list[Notification] = []

    for user_id in user_ids:
        notification = create_notification(
            db=db,
            user_id=user_id,
            title=title,
            message=message,
            notification_type=NotificationType.RISK,
            commit=False,
            send_push=False,
        )

        notifications.append(notification)

    return notifications


def create_risk_analysis_for_project(
    db: Session,
    project: Project,
) -> RiskAnalysis:
    tasks = get_project_tasks_for_risk_analysis(
        db=db,
        project_id=project.project_id,
    )

    preview = calculate_risk_preview(
        project=project,
        tasks=tasks,
    )

    risk_analysis = RiskAnalysis(
        project_id=project.project_id,
        risk_level=preview.risk_level.value,
        predicted_delay_days=preview.predicted_delay_days,
        reason=preview.reason,
        recommendation=preview.recommendation,
    )

    db.add(risk_analysis)
    db.flush()

    notifications_to_push: list[Notification] = []

    if risk_analysis.risk_level == RiskLevel.high.value:
        notifications_to_push = create_high_risk_notifications(
            db=db,
            project=project,
            risk_analysis=risk_analysis,
        )

    db.commit()
    db.refresh(risk_analysis)

    for notification in notifications_to_push:
        send_push_for_notification(
            db=db,
            notification=notification,
        )

    return risk_analysis


def preview_risk_analysis_for_project(
    db: Session,
    project: Project,
) -> RiskAnalysisPreviewResponse:
    tasks = get_project_tasks_for_risk_analysis(
        db=db,
        project_id=project.project_id,
    )

    return calculate_risk_preview(
        project=project,
        tasks=tasks,
    )


def get_risk_analyses_for_project(
    db: Session,
    project: Project,
) -> list[RiskAnalysis]:
    stmt = (
        select(RiskAnalysis)
        .where(RiskAnalysis.project_id == project.project_id)
        .order_by(RiskAnalysis.created_at.desc(), RiskAnalysis.risk_id.desc())
    )

    return list(db.execute(stmt).scalars().all())