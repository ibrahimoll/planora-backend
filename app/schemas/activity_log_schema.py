from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class ActivityLogEventType(StrEnum):
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"

    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"
    TASK_DELETED = "task_deleted"

    COMMENT_CREATED = "comment_created"
    COMMENT_UPDATED = "comment_updated"
    COMMENT_DELETED = "comment_deleted"

    ATTACHMENT_UPLOADED = "attachment_uploaded"
    ATTACHMENT_DELETED = "attachment_deleted"

    DEADLINE_REMINDER_GENERATED = "deadline_reminder_generated"

    AI_PLAN_GENERATED = "ai_plan_generated"


class ActivityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    activity_id: int
    project_id: int
    task_id: int | None
    actor_id: int | None

    event_type: ActivityLogEventType

    actor_username_snapshot: str | None
    actor_full_name_snapshot: str | None
    task_title_snapshot: str | None

    message: str
    metadata: dict[str, Any] | None

    created_at: datetime