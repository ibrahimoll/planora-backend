from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.attachment import Attachment
from app.models.comment import Comment
from app.models.deadline_reminder import DeadlineReminder
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.report_schema import (
    ProjectReportResponse,
    ReportActivitySummary,
    ReportHoursSummary,
    ReportMemberItem,
    ReportProgressSummary,
    ReportProjectStatus,
    ReportProjectSummary,
    ReportProjectType,
    ReportTaskItem,
    ReportTaskPriorityCounts,
    ReportTaskStatusCounts,
    ReportExportHistoryItem,
    ReportExportHistoryListResponse,
)
from app.models.report_export import ReportExport

def decimal_to_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0

    return float(value)


def decimal_snapshot_to_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0

    return float(value)


def get_accessible_project_for_report(
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
    stmt = (
        select(Task)
        .where(Task.project_id == project_id)
        .order_by(Task.created_at.asc())
    )

    return list(db.execute(stmt).scalars().all())


def get_project_members_for_report(
    db: Session,
    project: Project,
) -> list[ReportMemberItem]:
    if project.project_type == "personal":
        creator = db.get(User, project.created_by)

        if creator is None:
            return []

        return [
            ReportMemberItem(
                user_id=creator.user_id,
                username=creator.username,
                email=creator.email,
                full_name=creator.full_name,
                role="owner",
            )
        ]

    stmt = (
        select(ProjectMember, User)
        .join(User, ProjectMember.user_id == User.user_id)
        .where(ProjectMember.project_id == project.project_id)
        .order_by(ProjectMember.joined_at.asc())
    )

    rows = db.execute(stmt).all()

    return [
        ReportMemberItem(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=member.role,
        )
        for member, user in rows
    ]


def count_project_comments(
    db: Session,
    project_id: int,
) -> int:
    stmt = (
        select(func.count(Comment.comment_id))
        .join(Task, Comment.task_id == Task.task_id)
        .where(Task.project_id == project_id)
    )

    return int(db.execute(stmt).scalar_one())


def count_project_attachments(
    db: Session,
    project_id: int,
) -> int:
    stmt = select(func.count(Attachment.attachment_id)).where(
        Attachment.project_id == project_id,
    )

    return int(db.execute(stmt).scalar_one())


def count_project_deadline_reminders(
    db: Session,
    project_id: int,
) -> int:
    stmt = select(func.count(DeadlineReminder.reminder_id)).where(
        DeadlineReminder.project_id == project_id,
    )

    return int(db.execute(stmt).scalar_one())

def is_task_overdue(
    task: Task,
    now: datetime,
) -> bool:
    return (
        task.due_date is not None
        and task.status != "completed"
        and task.due_date < now
    )


def build_task_report_item(task: Task) -> ReportTaskItem:
    return ReportTaskItem(
        task_id=task.task_id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        assigned_to=task.assigned_to,
        estimated_hours=(
            None
            if task.estimated_hours is None
            else decimal_to_float(task.estimated_hours)
        ),
        actual_hours=(
            None
            if task.actual_hours is None
            else decimal_to_float(task.actual_hours)
        ),
        due_date=task.due_date,
        completed_at=task.completed_at,
        created_at=task.created_at,
    )


def generate_project_report(
    db: Session,
    project: Project,
) -> ProjectReportResponse:
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

    priority_counts = {
        "low": 0,
        "medium": 0,
        "high": 0,
    }

    estimated_hours_total = 0.0
    actual_hours_total = 0.0

    task_items: list[ReportTaskItem] = []

    for task in tasks:
        if task.status in status_counts:
            status_counts[task.status] += 1

        if task.priority in priority_counts:
            priority_counts[task.priority] += 1

        if task.status == "completed":
            completed_tasks += 1

        if is_task_overdue(task=task, now=now):
            overdue_tasks += 1

        estimated_hours_total += decimal_to_float(task.estimated_hours)
        actual_hours_total += decimal_to_float(task.actual_hours)

        task_items.append(build_task_report_item(task))

    pending_tasks = total_tasks - completed_tasks

    if total_tasks == 0:
        completion_percentage = 0.0
    else:
        completion_percentage = round((completed_tasks / total_tasks) * 100, 2)

    return ProjectReportResponse(
        generated_at=now,
        project=ReportProjectSummary(
            project_id=project.project_id,
            title=project.title,
            description=project.description,
            status=ReportProjectStatus(project.status),
            project_type=ReportProjectType(project.project_type),
            deadline=project.deadline,
            created_at=project.created_at,
            updated_at=project.updated_at,
        ),
        progress=ReportProgressSummary(
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            pending_tasks=pending_tasks,
            overdue_tasks=overdue_tasks,
            completion_percentage=completion_percentage,
        ),
        task_status_counts=ReportTaskStatusCounts(
            todo=status_counts["todo"],
            in_progress=status_counts["in_progress"],
            completed=status_counts["completed"],
            blocked=status_counts["blocked"],
        ),
        task_priority_counts=ReportTaskPriorityCounts(
            low=priority_counts["low"],
            medium=priority_counts["medium"],
            high=priority_counts["high"],
        ),
        hours=ReportHoursSummary(
            estimated_hours_total=round(estimated_hours_total, 2),
            actual_hours_total=round(actual_hours_total, 2),
        ),
        activity=ReportActivitySummary(
            comments_count=count_project_comments(
                db=db,
                project_id=project.project_id,
            ),
            attachments_count=count_project_attachments(
                db=db,
                project_id=project.project_id,
            ),
            deadline_reminders_count=count_project_deadline_reminders(
                db=db,
                project_id=project.project_id,
            ),
        ),
        members=get_project_members_for_report(
            db=db,
            project=project,
        ),
        tasks=task_items,
    )


def create_report_export_history(
    db: Session,
    project: Project,
    current_user: User,
    report: ProjectReportResponse,
) -> ReportExport:
    export = ReportExport(
        project_id=project.project_id,
        exported_by=current_user.user_id,
        report_type="project",
        export_format="json",
        project_title_snapshot=project.title,
        project_status_snapshot=project.status,
        project_type_snapshot=project.project_type,
        task_count_snapshot=report.progress.total_tasks,
        completion_percentage_snapshot=report.progress.completion_percentage,
        exported_by_username_snapshot=current_user.username,
        exported_by_full_name_snapshot=current_user.full_name,
        metadata_json={
            "completed_tasks": report.progress.completed_tasks,
            "pending_tasks": report.progress.pending_tasks,
            "overdue_tasks": report.progress.overdue_tasks,
            "estimated_hours_total": report.hours.estimated_hours_total,
            "actual_hours_total": report.hours.actual_hours_total,
        },
    )

    db.add(export)
    db.commit()
    db.refresh(export)

    return export


def build_report_export_history_item(
    export: ReportExport,
) -> ReportExportHistoryItem:
    return ReportExportHistoryItem(
        report_export_id=export.report_export_id,
        project_id=export.project_id,
        exported_by=export.exported_by,
        report_type=export.report_type,
        export_format=export.export_format,
        project_title_snapshot=export.project_title_snapshot,
        project_status_snapshot=export.project_status_snapshot,
        project_type_snapshot=export.project_type_snapshot,
        task_count_snapshot=export.task_count_snapshot,
        completion_percentage_snapshot=decimal_snapshot_to_float(
            export.completion_percentage_snapshot
        ),
        exported_by_username_snapshot=export.exported_by_username_snapshot,
        exported_by_full_name_snapshot=export.exported_by_full_name_snapshot,
        created_at=export.created_at,
    )


def list_my_report_exports(
    db: Session,
    current_user: User,
    limit: int,
    offset: int,
) -> ReportExportHistoryListResponse:
    base_stmt = select(ReportExport).where(
        ReportExport.exported_by == current_user.user_id,
    )

    total_stmt = select(func.count()).select_from(base_stmt.subquery())

    data_stmt = (
        base_stmt
        .order_by(ReportExport.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    total = int(db.execute(total_stmt).scalar_one())
    exports = list(db.execute(data_stmt).scalars().all())

    return ReportExportHistoryListResponse(
        items=[build_report_export_history_item(export) for export in exports],
        total=total,
        limit=limit,
        offset=offset,
    )


def list_project_report_exports(
    db: Session,
    project: Project,
    limit: int,
    offset: int,
) -> ReportExportHistoryListResponse:
    base_stmt = select(ReportExport).where(
        ReportExport.project_id == project.project_id,
    )

    total_stmt = select(func.count()).select_from(base_stmt.subquery())

    data_stmt = (
        base_stmt
        .order_by(ReportExport.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    total = int(db.execute(total_stmt).scalar_one())
    exports = list(db.execute(data_stmt).scalars().all())

    return ReportExportHistoryListResponse(
        items=[build_report_export_history_item(export) for export in exports],
        total=total,
        limit=limit,
        offset=offset,
    )