from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class ProductivityStatus(str, Enum):
    excellent = "excellent"
    good = "good"
    needs_attention = "needs_attention"
    at_risk = "at_risk"


class ProgressTaskStatusCounts(BaseModel):
    todo: int
    in_progress: int
    completed: int
    blocked: int


class ProgressHoursSummary(BaseModel):
    estimated_hours_total: float
    actual_hours_total: float
    remaining_estimated_hours: float


class UserProgressItem(BaseModel):
    user_id: int
    username: str
    full_name: str
    role: str
    tasks_completed: int
    tasks_total: int
    completion_percentage: float


class ProjectProgressSummary(BaseModel):
    project_id: int
    title: str
    project_type: str
    status: str
    deadline: datetime
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    overdue_tasks: int
    completion_percentage: float
    productivity_status: ProductivityStatus


class ProjectProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project: ProjectProgressSummary
    task_status_counts: ProgressTaskStatusCounts
    hours: ProgressHoursSummary
    current_user_progress: UserProgressItem
    members: list[UserProgressItem]
    recommendations: list[str]
    generated_at: datetime