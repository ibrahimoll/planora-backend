from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ProjectStatus(str, Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"
    on_hold = "on_hold"
    cancelled = "cancelled"


class ProjectType(str, Enum):
    personal = "personal"
    team = "team"


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    deadline: datetime


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    deadline: datetime | None = None
    status: ProjectStatus | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: int
    created_by: int
    team_id: int | None
    title: str
    description: str | None
    deadline: datetime
    status: ProjectStatus
    project_type: ProjectType
    created_at: datetime
    updated_at: datetime


class ProjectDeleteResponse(BaseModel):
    message: str