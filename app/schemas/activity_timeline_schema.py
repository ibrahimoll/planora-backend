from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ActivityTimelineType(StrEnum):
    PROJECT_CREATED = "project_created"
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    COMMENT_ADDED = "comment_added"
    ATTACHMENT_UPLOADED = "attachment_uploaded"
    DEADLINE_REMINDER_CREATED = "deadline_reminder_created"


class ActivityTimelineItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_type: ActivityTimelineType
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    occurred_at: datetime
    project_id: int
    task_id: int | None = None
    actor_user_id: int | None = None
    comment_id: int | None = None
    attachment_id: int | None = None
    reminder_id: int | None = None


class ActivityTimelineResponse(BaseModel):
    project_id: int
    total_items: int
    items: list[ActivityTimelineItem]
