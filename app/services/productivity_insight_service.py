from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.productivity_insight_schema import (
    InsightHealthStatus,
    ProductivityInsightsResponse,
    ProductivitySummary,
    ProjectInsightItem,
    WorkloadInsight,
)


ACTIVE_PROJECT_STATUSES = {"not_started", "in_progress", "on_hold"}


def decimal_to_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0

    return float(value)


def calculate_percentage(completed: int, total: int) -> float:
    if total == 0:
        return 0.0

    return round((completed / total) * 100, 2)


def is_task_overdue(task: Task, now: datetime) -> bool:
    return (
        task.due_date is not None
        and task.status != "completed"
        and task.due_date < now
    )


def get_accessible_projects(
    db: Session,
    current_user: User,
) -> list[Project]:
    team_project_ids_stmt = select(ProjectMember.project_id).where(
        ProjectMember.user_id == current_user.user_id,
    )

    stmt = (
        select(Project)
        .where(
            or_(
                and_(
                    Project.project_type == "personal",
                    Project.created_by == current_user.user_id,
                ),
                and_(
                    Project.project_type == "team",
                    Project.project_id.in_(team_project_ids_stmt),
                ),
            )
        )
        .order_by(Project.created_at.desc())
    )

    return list(db.execute(stmt).scalars().all())


def get_tasks_for_projects(
    db: Session,
    project_ids: list[int],
) -> list[Task]:
    if not project_ids:
        return []

    stmt = select(Task).where(Task.project_id.in_(project_ids))

    return list(db.execute(stmt).scalars().all())


def get_project_health_status(
    project: Project,
    completion_percentage: float,
    overdue_tasks: int,
    blocked_tasks: int,
    now: datetime,
) -> InsightHealthStatus:
    if project.status == "completed":
        return InsightHealthStatus.excellent

    if project.status == "cancelled":
        return InsightHealthStatus.at_risk

    deadline_passed = project.deadline < now

    if deadline_passed or overdue_tasks > 0 or blocked_tasks >= 2:
        return InsightHealthStatus.at_risk

    if completion_percentage >= 80:
        return InsightHealthStatus.excellent

    if completion_percentage >= 50:
        return InsightHealthStatus.good

    return InsightHealthStatus.needs_attention


def build_project_insights(
    projects: list[Project],
    tasks: list[Task],
    current_user: User,
    now: datetime,
) -> list[ProjectInsightItem]:
    tasks_by_project: dict[int, list[Task]] = {
        project.project_id: []
        for project in projects
    }

    for task in tasks:
        tasks_by_project.setdefault(task.project_id, []).append(task)

    project_items: list[ProjectInsightItem] = []

    for project in projects:
        project_tasks = tasks_by_project.get(project.project_id, [])

        total_tasks = len(project_tasks)
        completed_tasks = len(
            [
                task
                for task in project_tasks
                if task.status == "completed"
            ]
        )
        assigned_tasks = len(
            [
                task
                for task in project_tasks
                if task.assigned_to == current_user.user_id
            ]
        )
        overdue_tasks = len(
            [
                task
                for task in project_tasks
                if is_task_overdue(task=task, now=now)
            ]
        )
        blocked_tasks = len(
            [
                task
                for task in project_tasks
                if task.status == "blocked"
            ]
        )
        completion_percentage = calculate_percentage(
            completed=completed_tasks,
            total=total_tasks,
        )

        project_items.append(
            ProjectInsightItem(
                project_id=project.project_id,
                title=project.title,
                project_type=project.project_type,
                status=project.status,
                deadline=project.deadline,
                total_tasks=total_tasks,
                completed_tasks=completed_tasks,
                assigned_tasks=assigned_tasks,
                overdue_tasks=overdue_tasks,
                blocked_tasks=blocked_tasks,
                completion_percentage=completion_percentage,
                health_status=get_project_health_status(
                    project=project,
                    completion_percentage=completion_percentage,
                    overdue_tasks=overdue_tasks,
                    blocked_tasks=blocked_tasks,
                    now=now,
                ),
            )
        )

    return project_items


def build_recommendations(
    summary: ProductivitySummary,
    workload: WorkloadInsight,
    projects: list[ProjectInsightItem],
) -> list[str]:
    recommendations: list[str] = []

    at_risk_projects = [
        project
        for project in projects
        if project.health_status == InsightHealthStatus.at_risk
    ]

    if summary.overdue_assigned_tasks > 0:
        recommendations.append(
            "Start with your overdue assigned tasks before taking new work."
        )

    if workload.high_priority_open_tasks > 0:
        recommendations.append(
            "Focus on high-priority open tasks to improve project stability."
        )

    if workload.overloaded:
        recommendations.append(
            "Your workload is high. Consider rescheduling tasks or splitting work into smaller parts."
        )

    if at_risk_projects:
        recommendations.append(
            "Review at-risk projects and update blocked or overdue tasks."
        )

    if summary.assigned_tasks == 0 and summary.total_projects > 0:
        recommendations.append(
            "You have projects but no assigned tasks. Create or assign tasks to make progress measurable."
        )

    if summary.completion_percentage >= 80 and not recommendations:
        recommendations.append(
            "Your productivity looks strong. Keep the same pace and monitor upcoming deadlines."
        )

    if not recommendations:
        recommendations.append(
            "Your productivity is stable. Keep completing tasks consistently."
        )

    return recommendations


def generate_my_productivity_insights(
    db: Session,
    current_user: User,
) -> ProductivityInsightsResponse:
    now = datetime.now(timezone.utc)

    projects = get_accessible_projects(
        db=db,
        current_user=current_user,
    )
    project_ids = [project.project_id for project in projects]

    tasks = get_tasks_for_projects(
        db=db,
        project_ids=project_ids,
    )

    assigned_tasks = [
        task
        for task in tasks
        if task.assigned_to == current_user.user_id
    ]
    completed_assigned_tasks = [
        task
        for task in assigned_tasks
        if task.status == "completed"
    ]
    incomplete_assigned_tasks = [
        task
        for task in assigned_tasks
        if task.status != "completed"
    ]
    overdue_assigned_tasks = [
        task
        for task in assigned_tasks
        if is_task_overdue(task=task, now=now)
    ]
    blocked_assigned_tasks = [
        task
        for task in assigned_tasks
        if task.status == "blocked"
    ]
    high_priority_open_tasks = [
        task
        for task in incomplete_assigned_tasks
        if task.priority == "high"
    ]

    estimated_hours_remaining = round(
        sum(
            decimal_to_float(task.estimated_hours)
            for task in incomplete_assigned_tasks
        ),
        2,
    )

    summary = ProductivitySummary(
        total_projects=len(projects),
        active_projects=len(
            [
                project
                for project in projects
                if project.status in ACTIVE_PROJECT_STATUSES
            ]
        ),
        completed_projects=len(
            [
                project
                for project in projects
                if project.status == "completed"
            ]
        ),
        total_tasks=len(tasks),
        assigned_tasks=len(assigned_tasks),
        completed_assigned_tasks=len(completed_assigned_tasks),
        overdue_assigned_tasks=len(overdue_assigned_tasks),
        blocked_assigned_tasks=len(blocked_assigned_tasks),
        completion_percentage=calculate_percentage(
            completed=len(completed_assigned_tasks),
            total=len(assigned_tasks),
        ),
    )

    workload = WorkloadInsight(
        assigned_incomplete_tasks=len(incomplete_assigned_tasks),
        estimated_hours_remaining=estimated_hours_remaining,
        high_priority_open_tasks=len(high_priority_open_tasks),
        overloaded=(
            len(incomplete_assigned_tasks) >= 10
            or estimated_hours_remaining > 20
        ),
    )

    project_items = build_project_insights(
        projects=projects,
        tasks=tasks,
        current_user=current_user,
        now=now,
    )

    return ProductivityInsightsResponse(
        summary=summary,
        workload=workload,
        projects=project_items,
        recommendations=build_recommendations(
            summary=summary,
            workload=workload,
            projects=project_items,
        ),
        generated_at=now,
    )
