from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SmartScheduleStrategy(StrEnum):
    balanced = "balanced"


class SmartScheduleRequest(BaseModel):
    strategy: SmartScheduleStrategy = SmartScheduleStrategy.balanced
    daily_capacity_hours: float = Field(default=4.0, ge=1.0, le=12.0)
    start_date: datetime | None = None
    apply_schedule: bool = False


class SmartScheduleTaskItem(BaseModel):
    task_id: int
    title: str
    priority: str
    status: str
    assigned_to: int | None
    estimated_hours: float
    old_due_date: datetime | None
    suggested_due_date: datetime
    is_after_project_deadline: bool


class SmartSchedulePreviewResponse(BaseModel):
    project_id: int
    strategy: SmartScheduleStrategy
    daily_capacity_hours: float
    total_tasks: int
    schedulable_task_count: int
    completed_task_count: int
    estimated_total_hours: float
    project_deadline: datetime
    first_suggested_due_date: datetime | None
    last_suggested_due_date: datetime | None
    tasks: list[SmartScheduleTaskItem]
    warnings: list[str]


class SmartScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    schedule_id: int
    project_id: int
    generated_by: int | None
    strategy: SmartScheduleStrategy
    schedule_data: dict[str, Any]
    applied_at: datetime | None
    created_at: datetime