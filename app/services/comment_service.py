from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.comment_mention import CommentMention
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.activity_log_schema import ActivityLogEventType
from app.schemas.comment_schema import CommentCreate, CommentUpdate
from app.schemas.notification_schema import NotificationType
from app.services.activity_log_service import create_activity_log
from app.services.notification_service import create_notification

MENTION_PATTERN = re.compile(r"(?<![\w@])@([A-Za-z0-9_.-]{1,50})")


def extract_mentioned_usernames(comment_text: str) -> list[str]:
    usernames: list[str] = []

    for match in MENTION_PATTERN.finditer(comment_text):
        username = match.group(1)

        if username not in usernames:
            usernames.append(username)

    return usernames


def get_existing_mention_user_ids(
    db: Session,
    comment: Comment,
) -> set[int]:
    stmt = select(CommentMention.mentioned_user_id).where(
        CommentMention.comment_id == comment.comment_id,
    )

    return set(db.execute(stmt).scalars().all())


def get_mentionable_users_for_task(
    db: Session,
    task: Task,
    current_user: User,
    usernames: list[str],
) -> list[User]:
    if not usernames:
        return []

    if task.project.project_type == "personal":
        if current_user.username in usernames:
            return [current_user]

        return []

    stmt = (
        select(User)
        .join(ProjectMember, ProjectMember.user_id == User.user_id)
        .where(
            ProjectMember.project_id == task.project_id,
            User.username.in_(usernames),
            User.is_active.is_(True),
        )
    )

    return list(db.execute(stmt).scalars().all())


def replace_comment_mentions(
    db: Session,
    comment: Comment,
    task: Task,
    current_user: User,
    previous_mentioned_user_ids: set[int] | None = None,
) -> None:
    if previous_mentioned_user_ids is None:
        previous_mentioned_user_ids = set()

    existing_mentions = list(
        db.execute(
            select(CommentMention).where(
                CommentMention.comment_id == comment.comment_id,
            )
        )
        .scalars()
        .all()
    )

    for existing_mention in existing_mentions:
        db.delete(existing_mention)

    db.flush()

    mentioned_usernames = extract_mentioned_usernames(comment.comment_text)

    mentioned_users = get_mentionable_users_for_task(
        db=db,
        task=task,
        current_user=current_user,
        usernames=mentioned_usernames,
    )

    for mentioned_user in mentioned_users:
        mention = CommentMention(
            comment_id=comment.comment_id,
            project_id=task.project_id,
            task_id=task.task_id,
            mentioned_user_id=mentioned_user.user_id,
            mentioned_by=current_user.user_id,
        )

        db.add(mention)

        should_notify = (
            mentioned_user.user_id != current_user.user_id
            and mentioned_user.user_id not in previous_mentioned_user_ids
        )

        if should_notify:
            create_notification(
                db=db,
                user_id=mentioned_user.user_id,
                title="You were mentioned in a comment",
                message=(
                    f"{current_user.full_name} mentioned you "
                    f"on task '{task.title}'."
                ),
                notification_type=NotificationType.MENTION,
                commit=False,
            )


def create_comment_for_task(
    db: Session,
    task: Task,
    current_user: User,
    comment_data: CommentCreate,
) -> Comment:
    comment = Comment(
        task_id=task.task_id,
        user_id=current_user.user_id,
        comment_text=comment_data.comment_text,
    )

    db.add(comment)
    db.flush()

    replace_comment_mentions(
        db=db,
        comment=comment,
        task=task,
        current_user=current_user,
    )

    create_activity_log(
        db=db,
        project=task.project,
        actor=current_user,
        task=task,
        event_type=ActivityLogEventType.COMMENT_CREATED,
        message=f"{current_user.full_name} commented on task '{task.title}'.",
        metadata={"comment_id": comment.comment_id},
        commit=False,
    )

    db.commit()
    db.refresh(comment)

    return comment


def get_comments_for_task(
    db: Session,
    task: Task,
) -> list[Comment]:
    stmt = (
        select(Comment)
        .where(Comment.task_id == task.task_id)
        .order_by(Comment.created_at.asc())
    )

    return list(db.execute(stmt).scalars().all())


def get_comment_for_task_by_id(
    db: Session,
    task: Task,
    comment_id: int,
) -> Comment | None:
    stmt = select(Comment).where(
        Comment.comment_id == comment_id,
        Comment.task_id == task.task_id,
    )

    return db.execute(stmt).scalars().first()


def update_comment(
    db: Session,
    task: Task,
    current_user: User,
    comment: Comment,
    comment_data: CommentUpdate,
) -> Comment:
    previous_mentioned_user_ids = get_existing_mention_user_ids(
        db=db,
        comment=comment,
    )

    update_data = comment_data.model_dump(exclude_unset=True)

    comment_text_was_updated = False

    for field, value in update_data.items():
        if value is None:
            continue

        setattr(comment, field, value)

        if field == "comment_text":
            comment_text_was_updated = True

    if comment_text_was_updated:
        db.flush()

        replace_comment_mentions(
            db=db,
            comment=comment,
            task=task,
            current_user=current_user,
            previous_mentioned_user_ids=previous_mentioned_user_ids,
        )

        create_activity_log(
            db=db,
            project=task.project,
            actor=current_user,
            task=task,
            event_type=ActivityLogEventType.COMMENT_UPDATED,
            message=f"{current_user.full_name} updated a comment on task '{task.title}'.",
            metadata={"comment_id": comment.comment_id},
            commit=False,
        )

    db.commit()
    db.refresh(comment)

    return comment


def delete_comment(
    db: Session,
    task: Task,
    current_user: User,
    comment: Comment,
) -> None:
    create_activity_log(
        db=db,
        project=task.project,
        actor=current_user,
        task=task,
        event_type=ActivityLogEventType.COMMENT_DELETED,
        message=f"{current_user.full_name} deleted a comment on task '{task.title}'.",
        metadata={"comment_id": comment.comment_id},
        commit=False,
    )

    db.delete(comment)
    db.commit()
