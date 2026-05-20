from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from app.schemas.pagination_schema import PaginationMeta

class AdminUserStats(BaseModel):
    total_users: int
    active_users: int
    inactive_users: int
    verified_users: int
    unverified_users: int
    admin_users: int


class AdminProjectStats(BaseModel):
    total_projects: int
    personal_projects: int
    team_projects: int
    not_started_projects: int
    in_progress_projects: int
    completed_projects: int
    on_hold_projects: int
    cancelled_projects: int


class AdminTaskStats(BaseModel):
    total_tasks: int
    todo_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    blocked_tasks: int
    overdue_tasks: int


class AdminRiskStats(BaseModel):
    total_risk_records: int
    low_risk_records: int
    medium_risk_records: int
    high_risk_records: int


class AdminNotificationStats(BaseModel):
    total_notifications: int
    unread_notifications: int
    read_notifications: int


class AdminDashboardOverviewResponse(BaseModel):
    users: AdminUserStats
    projects: AdminProjectStats
    tasks: AdminTaskStats
    teams_total: int
    risks: AdminRiskStats
    notifications: AdminNotificationStats
    generated_at: datetime


class AdminUserSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_email_verified: bool
    created_at: datetime


class AdminActivityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    activity_id: int
    project_id: int
    task_id: int | None
    actor_id: int | None
    event_type: str
    message: str
    created_at: datetime


class AdminLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_id: int
    admin_id: int
    target_user_id: int | None
    action: str
    created_at: datetime


class AdminUserListResponse(PaginationMeta):
    items: list[AdminUserSummaryResponse]


class AdminLogListResponse(PaginationMeta):
    items: list[AdminLogResponse]