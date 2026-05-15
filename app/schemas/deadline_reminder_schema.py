from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DeadlineReminderType(StrEnum):
    DUE_SOON = "due_soon"
    OVERDUE = "overdue"


class DeadlineReminderRunRequest(BaseModel):
    hours_ahead: int = Field(default=24, ge=1, le=168)
    include_overdue: bool = True


class DeadlineReminderRunResponse(BaseModel):
    due_soon_created: int
    overdue_created: int
    total_created: int


class DeadlineReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reminder_id: int
    task_id: int
    project_id: int
    user_id: int
    reminder_type: DeadlineReminderType
    due_date_snapshot: datetime
    generated_at: datetime