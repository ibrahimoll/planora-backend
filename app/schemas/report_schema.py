from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ReportProjectType(StrEnum):
    personal = "personal"
    team = "team"


class ReportProjectStatus(StrEnum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"
    on_hold = "on_hold"
    cancelled = "cancelled"


class ReportTaskStatusCounts(BaseModel):
    todo: int
    in_progress: int
    completed: int
    blocked: int


class ReportTaskPriorityCounts(BaseModel):
    low: int
    medium: int
    high: int


class ReportProjectSummary(BaseModel):
    project_id: int
    title: str
    description: str | None
    status: ReportProjectStatus
    project_type: ReportProjectType
    deadline: datetime
    created_at: datetime
    updated_at: datetime


class ReportProgressSummary(BaseModel):
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    overdue_tasks: int
    completion_percentage: float


class ReportHoursSummary(BaseModel):
    estimated_hours_total: float
    actual_hours_total: float


class ReportActivitySummary(BaseModel):
    comments_count: int
    attachments_count: int
    deadline_reminders_count: int


class ReportMemberItem(BaseModel):
    user_id: int
    username: str
    email: str
    full_name: str
    role: str


class ReportTaskItem(BaseModel):
    task_id: int
    title: str
    description: str | None
    status: str
    priority: str
    assigned_to: int | None
    estimated_hours: float | None
    actual_hours: float | None
    due_date: datetime | None
    completed_at: datetime | None
    created_at: datetime


class ProjectReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    generated_at: datetime
    project: ReportProjectSummary
    progress: ReportProgressSummary
    task_status_counts: ReportTaskStatusCounts
    task_priority_counts: ReportTaskPriorityCounts
    hours: ReportHoursSummary
    activity: ReportActivitySummary
    members: list[ReportMemberItem]
    tasks: list[ReportTaskItem]