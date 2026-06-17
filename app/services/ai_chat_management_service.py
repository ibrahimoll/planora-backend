from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.models.project import Project


def delete_project_chat_history(
    db: Session,
    project: Project,
) -> int:
    result = db.execute(
        delete(ChatMessage).where(ChatMessage.project_id == project.project_id)
    )
    db.commit()

    return int(result.rowcount or 0)
