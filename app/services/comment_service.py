from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.task import Task
from app.models.user import User
from app.schemas.comment_schema import CommentCreate, CommentUpdate


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
    comment: Comment,
    comment_data: CommentUpdate,
) -> Comment:
    update_data = comment_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if value is None:
            continue

        setattr(comment, field, value)

    db.commit()
    db.refresh(comment)

    return comment


def delete_comment(
    db: Session,
    comment: Comment,
) -> None:
    db.delete(comment)
    db.commit()