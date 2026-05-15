from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.attachment import Attachment
from app.models.comment import Comment
from app.models.deadline_reminder import DeadlineReminder
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.activity_timeline_schema import (
    ActivityTimelineItem,
    ActivityTimelineResponse,
    ActivityTimelineType,
)


def get_accessible_project_for_activity_timeline(
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


def build_project_created_item(project: Project) -> ActivityTimelineItem:
    return ActivityTimelineItem(
        item_type=ActivityTimelineType.PROJECT_CREATED,
        title="Project created",
        description=f'Project "{project.title}" was created.',
        occurred_at=project.created_at,
        project_id=project.project_id,
        actor_user_id=project.created_by,
    )


def get_task_activity_items(
    db: Session,
    project_id: int,
) -> list[ActivityTimelineItem]:
    stmt = select(Task).where(Task.project_id == project_id)
    tasks = db.execute(stmt).scalars().all()

    items: list[ActivityTimelineItem] = []

    for task in tasks:
        items.append(
            ActivityTimelineItem(
                item_type=ActivityTimelineType.TASK_CREATED,
                title="Task created",
                description=f'Task "{task.title}" was created.',
                occurred_at=task.created_at,
                project_id=task.project_id,
                task_id=task.task_id,
                actor_user_id=task.created_by,
            )
        )

        if task.completed_at is not None:
            items.append(
                ActivityTimelineItem(
                    item_type=ActivityTimelineType.TASK_COMPLETED,
                    title="Task completed",
                    description=f'Task "{task.title}" was completed.',
                    occurred_at=task.completed_at,
                    project_id=task.project_id,
                    task_id=task.task_id,
                    actor_user_id=task.assigned_to,
                )
            )

    return items


def get_comment_activity_items(
    db: Session,
    project_id: int,
) -> list[ActivityTimelineItem]:
    stmt = (
        select(Comment, Task)
        .join(Task, Comment.task_id == Task.task_id)
        .where(Task.project_id == project_id)
    )

    rows = db.execute(stmt).all()

    return [
        ActivityTimelineItem(
            item_type=ActivityTimelineType.COMMENT_ADDED,
            title="Comment added",
            description=comment.comment_text,
            occurred_at=comment.created_at,
            project_id=task.project_id,
            task_id=task.task_id,
            actor_user_id=comment.user_id,
            comment_id=comment.comment_id,
        )
        for comment, task in rows
    ]


def get_attachment_activity_items(
    db: Session,
    project_id: int,
) -> list[ActivityTimelineItem]:
    stmt = select(Attachment).where(Attachment.project_id == project_id)
    attachments = db.execute(stmt).scalars().all()

    return [
        ActivityTimelineItem(
            item_type=ActivityTimelineType.ATTACHMENT_UPLOADED,
            title="Attachment uploaded",
            description=f'File "{attachment.file_name}" was uploaded.',
            occurred_at=attachment.uploaded_at,
            project_id=attachment.project_id,
            task_id=attachment.task_id,
            actor_user_id=attachment.uploaded_by,
            attachment_id=attachment.attachment_id,
        )
        for attachment in attachments
    ]


def get_deadline_reminder_activity_items(
    db: Session,
    project_id: int,
) -> list[ActivityTimelineItem]:
    stmt = select(DeadlineReminder).where(DeadlineReminder.project_id == project_id)
    reminders = db.execute(stmt).scalars().all()

    return [
        ActivityTimelineItem(
            item_type=ActivityTimelineType.DEADLINE_REMINDER_CREATED,
            title="Deadline reminder created",
            description=(
                f"{reminder.reminder_type} reminder created for task "
                f"{reminder.task_id}."
            ),
            occurred_at=reminder.generated_at,
            project_id=reminder.project_id,
            task_id=reminder.task_id,
            actor_user_id=reminder.user_id,
            reminder_id=reminder.reminder_id,
        )
        for reminder in reminders
    ]


def get_project_activity_timeline(
    db: Session,
    project: Project,
    limit: int = 50,
) -> ActivityTimelineResponse:
    items = [build_project_created_item(project)]
    items.extend(get_task_activity_items(db=db, project_id=project.project_id))
    items.extend(get_comment_activity_items(db=db, project_id=project.project_id))
    items.extend(get_attachment_activity_items(db=db, project_id=project.project_id))
    items.extend(
        get_deadline_reminder_activity_items(
            db=db,
            project_id=project.project_id,
        )
    )

    items.sort(key=lambda item: item.occurred_at, reverse=True)
    limited_items = items[:limit]

    return ActivityTimelineResponse(
        project_id=project.project_id,
        total_items=len(limited_items),
        items=limited_items,
    )
