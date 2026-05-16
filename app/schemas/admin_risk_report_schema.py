from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.admin_project_oversight_schema import AdminProjectSummaryResponse


class AdminRiskCenterSummaryResponse(BaseModel):
    total_projects: int
    projects_with_risk_records: int
    high_risk_projects: int
    medium_risk_projects: int
    low_risk_projects: int
    overdue_active_projects: int
    blocked_task_projects: int
    generated_at: datetime


class AdminHighRiskProjectResponse(BaseModel):
    project: AdminProjectSummaryResponse
    risk_id: int
    risk_level: str
    predicted_delay_days: int
    reason: str
    recommendation: str
    created_at: datetime


class AdminSystemSummaryReportResponse(BaseModel):
    users_total: int
    users_active: int
    users_inactive: int
    admins_total: int
    projects_total: int
    team_projects: int
    personal_projects: int
    tasks_total: int
    overdue_tasks: int
    blocked_tasks: int
    high_risk_records: int
    teams_total: int
    generated_at: datetime


class AdminProjectSummaryReportResponse(BaseModel):
    projects_total: int
    not_started: int
    in_progress: int
    completed: int
    on_hold: int
    cancelled: int
    average_completion_percentage: float
    generated_at: datetime


class AdminUserSummaryReportResponse(BaseModel):
    users_total: int
    active_users: int
    inactive_users: int
    verified_users: int
    unverified_users: int
    admin_users: int
    users_with_assigned_tasks: int
    generated_at: datetime
