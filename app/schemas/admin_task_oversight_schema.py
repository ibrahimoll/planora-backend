from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from app.schemas.pagination_schema import PaginationMeta

TaskStatus = Literal["todo", "in_progress", "completed", "blocked"]
TaskPriority = Literal["low", "medium", "high"]


class AdminTaskUserResponse(BaseModel):
    user_id: int
    username: str
    email: str
    full_name: str


class AdminTaskProjectResponse(BaseModel):
    project_id: int
    title: str
    status: str
    project_type: str
    team_id: int | None
    team_name: str | None


class AdminTaskSummaryResponse(BaseModel):
    task_id: int
    title: str
    priority: str
    status: str
    due_date: datetime | None
    completed_at: datetime | None
    created_at: datetime
    estimated_hours: float | None
    actual_hours: float | None
    is_overdue: bool
    project: AdminTaskProjectResponse
    assignee: AdminTaskUserResponse | None
    creator: AdminTaskUserResponse


class AdminTaskDetailResponse(AdminTaskSummaryResponse):
    description: str | None
    comments_count: int
    attachments_count: int


class AdminTaskStatusUpdateRequest(BaseModel):
    status: TaskStatus


class AdminTaskAssignmentUpdateRequest(BaseModel):
    assigned_to: int | None


class AdminTaskActionResponse(BaseModel):
    message: str
    task: AdminTaskDetailResponse
    admin_log_id: int


class AdminTaskListResponse(PaginationMeta):
    items: list[AdminTaskSummaryResponse]