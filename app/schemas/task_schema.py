from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    completed = "completed"
    blocked = "blocked"


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    priority: TaskPriority = TaskPriority.medium
    estimated_hours: float | None = Field(default=None, ge=0)
    actual_hours: float | None = Field(default=None, ge=0)
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    priority: TaskPriority | None = None
    estimated_hours: float | None = Field(default=None, ge=0)
    actual_hours: float | None = Field(default=None, ge=0)
    status: TaskStatus | None = None
    due_date: datetime | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: int
    project_id: int
    assigned_to: int | None
    created_by: int
    title: str
    description: str | None
    priority: TaskPriority
    estimated_hours: float | None
    actual_hours: float | None
    status: TaskStatus
    due_date: datetime | None
    completed_at: datetime | None
    created_at: datetime


class TaskDeleteResponse(BaseModel):
    message: str