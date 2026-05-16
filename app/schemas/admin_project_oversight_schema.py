from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


ProjectStatus = Literal[
    "not_started",
    "in_progress",
    "completed",
    "on_hold",
    "cancelled",
]

ProjectType = Literal["personal", "team"]


class AdminProjectOwnerResponse(BaseModel):
    user_id: int
    username: str
    email: str
    full_name: str


class AdminProjectTeamResponse(BaseModel):
    team_id: int
    name: str
    created_by: int


class AdminProjectTaskStatsResponse(BaseModel):
    total_tasks: int
    todo_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    blocked_tasks: int
    overdue_tasks: int
    completion_percentage: float


class AdminProjectRiskResponse(BaseModel):
    risk_id: int
    risk_level: str
    predicted_delay_days: int
    created_at: datetime


class AdminProjectSummaryResponse(BaseModel):
    project_id: int
    title: str
    deadline: datetime
    status: str
    project_type: str
    created_at: datetime
    updated_at: datetime
    owner: AdminProjectOwnerResponse
    team: AdminProjectTeamResponse | None
    task_stats: AdminProjectTaskStatsResponse
    latest_risk: AdminProjectRiskResponse | None


class AdminProjectDetailResponse(AdminProjectSummaryResponse):
    description: str | None
    members_count: int


class AdminProjectStatusUpdateRequest(BaseModel):
    status: ProjectStatus


class AdminProjectStatusUpdateResponse(BaseModel):
    message: str
    project: AdminProjectDetailResponse
    admin_log_id: int