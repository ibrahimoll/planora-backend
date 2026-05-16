from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.models.user_progress import UserProgress
from app.schemas.progress_schema import (
    ProductivityStatus,
    ProgressHoursSummary,
    ProgressTaskStatusCounts,
    ProjectProgressResponse,
    ProjectProgressSummary,
    UserProgressItem,
)


def decimal_to_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0

    return float(value)


def calculate_percentage(completed: int, total: int) -> float:
    if total == 0:
        return 0.0

    return round((completed / total) * 100, 2)


def get_accessible_project_for_progress(
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


def get_project_tasks(
    db: Session,
    project_id: int,
) -> list[Task]:
    stmt = select(Task).where(Task.project_id == project_id)
    return list(db.execute(stmt).scalars().all())


def is_task_overdue(
    task: Task,
    now: datetime,
) -> bool:
    return (
        task.due_date is not None
        and task.status != "completed"
        and task.due_date < now
    )


def get_productivity_status(
    completion_percentage: float,
    overdue_tasks: int,
    blocked_tasks: int,
) -> ProductivityStatus:
    if overdue_tasks > 0 or blocked_tasks >= 3:
        return ProductivityStatus.at_risk

    if completion_percentage >= 80:
        return ProductivityStatus.excellent

    if completion_percentage >= 50:
        return ProductivityStatus.good

    return ProductivityStatus.needs_attention


def build_recommendations(
    completion_percentage: float,
    overdue_tasks: int,
    blocked_tasks: int,
    remaining_estimated_hours: float,
) -> list[str]:
    recommendations: list[str] = []

    if overdue_tasks > 0:
        recommendations.append(
            "Review overdue tasks and update their due dates or priority."
        )

    if blocked_tasks > 0:
        recommendations.append(
            "Resolve blocked tasks before creating more new work."
        )

    if completion_percentage < 50:
        recommendations.append(
            "Focus on completing high-priority tasks to improve project progress."
        )

    if remaining_estimated_hours > 20:
        recommendations.append(
            "The remaining workload is high. Consider splitting work into smaller tasks."
        )

    if not recommendations:
        recommendations.append(
            "Project progress looks stable. Keep monitoring task completion regularly."
        )

    return recommendations


def upsert_user_progress(
    db: Session,
    user_id: int,
    project_id: int,
    tasks_completed: int,
    tasks_total: int,
) -> UserProgress:
    completion_percentage = calculate_percentage(
        completed=tasks_completed,
        total=tasks_total,
    )

    stmt = select(UserProgress).where(
        UserProgress.user_id == user_id,
        UserProgress.project_id == project_id,
    )

    progress = db.execute(stmt).scalars().first()

    if progress is None:
        progress = UserProgress(
            user_id=user_id,
            project_id=project_id,
            tasks_completed=tasks_completed,
            tasks_total=tasks_total,
            completion_percentage=completion_percentage,
        )
        db.add(progress)
    else:
        progress.tasks_completed = tasks_completed
        progress.tasks_total = tasks_total
        progress.completion_percentage = Decimal(str(completion_percentage))

    return progress


def get_project_members(
    db: Session,
    project: Project,
) -> list[tuple[User, str]]:
    if project.project_type == "personal":
        creator = db.get(User, project.created_by)

        if creator is None:
            return []

        return [(creator, "owner")]

    stmt = (
        select(User, ProjectMember.role)
        .join(ProjectMember, ProjectMember.user_id == User.user_id)
        .where(ProjectMember.project_id == project.project_id)
        .order_by(ProjectMember.joined_at.asc())
    )

    return [(user, role) for user, role in db.execute(stmt).all()]


def build_user_progress_items(
    db: Session,
    project: Project,
    tasks: list[Task],
) -> list[UserProgressItem]:
    members = get_project_members(db=db, project=project)
    items: list[UserProgressItem] = []

    for user, role in members:
        assigned_tasks = [
            task
            for task in tasks
            if task.assigned_to == user.user_id
        ]

        tasks_total = len(assigned_tasks)
        tasks_completed = len(
            [
                task
                for task in assigned_tasks
                if task.status == "completed"
            ]
        )

        progress = upsert_user_progress(
            db=db,
            user_id=user.user_id,
            project_id=project.project_id,
            tasks_completed=tasks_completed,
            tasks_total=tasks_total,
        )

        items.append(
            UserProgressItem(
                user_id=user.user_id,
                username=user.username,
                full_name=user.full_name,
                role=role,
                tasks_completed=progress.tasks_completed,
                tasks_total=progress.tasks_total,
                completion_percentage=decimal_to_float(
                    progress.completion_percentage
                ),
            )
        )

    return items


def generate_project_progress(
    db: Session,
    project: Project,
    current_user: User,
) -> ProjectProgressResponse:
    now = datetime.now(timezone.utc)
    tasks = get_project_tasks(db=db, project_id=project.project_id)

    total_tasks = len(tasks)
    completed_tasks = 0
    overdue_tasks = 0

    status_counts = {
        "todo": 0,
        "in_progress": 0,
        "completed": 0,
        "blocked": 0,
    }

    estimated_hours_total = 0.0
    actual_hours_total = 0.0
    completed_estimated_hours = 0.0

    for task in tasks:
        if task.status in status_counts:
            status_counts[task.status] += 1

        if task.status == "completed":
            completed_tasks += 1
            completed_estimated_hours += decimal_to_float(task.estimated_hours)

        if is_task_overdue(task=task, now=now):
            overdue_tasks += 1

        estimated_hours_total += decimal_to_float(task.estimated_hours)
        actual_hours_total += decimal_to_float(task.actual_hours)

    pending_tasks = total_tasks - completed_tasks
    completion_percentage = calculate_percentage(
        completed=completed_tasks,
        total=total_tasks,
    )

    remaining_estimated_hours = max(
        estimated_hours_total - completed_estimated_hours,
        0.0,
    )

    productivity_status = get_productivity_status(
        completion_percentage=completion_percentage,
        overdue_tasks=overdue_tasks,
        blocked_tasks=status_counts["blocked"],
    )

    member_progress = build_user_progress_items(
        db=db,
        project=project,
        tasks=tasks,
    )

    db.commit()

    current_user_progress = next(
        (
            item
            for item in member_progress
            if item.user_id == current_user.user_id
        ),
        UserProgressItem(
            user_id=current_user.user_id,
            username=current_user.username,
            full_name=current_user.full_name,
            role="member",
            tasks_completed=0,
            tasks_total=0,
            completion_percentage=0.0,
        ),
    )

    return ProjectProgressResponse(
        project=ProjectProgressSummary(
            project_id=project.project_id,
            title=project.title,
            project_type=project.project_type,
            status=project.status,
            deadline=project.deadline,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            pending_tasks=pending_tasks,
            overdue_tasks=overdue_tasks,
            completion_percentage=completion_percentage,
            productivity_status=productivity_status,
        ),
        task_status_counts=ProgressTaskStatusCounts(
            todo=status_counts["todo"],
            in_progress=status_counts["in_progress"],
            completed=status_counts["completed"],
            blocked=status_counts["blocked"],
        ),
        hours=ProgressHoursSummary(
            estimated_hours_total=round(estimated_hours_total, 2),
            actual_hours_total=round(actual_hours_total, 2),
            remaining_estimated_hours=round(remaining_estimated_hours, 2),
        ),
        current_user_progress=current_user_progress,
        members=member_progress,
        recommendations=build_recommendations(
            completion_percentage=completion_percentage,
            overdue_tasks=overdue_tasks,
            blocked_tasks=status_counts["blocked"],
            remaining_estimated_hours=remaining_estimated_hours,
        ),
        generated_at=now,
    )