from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class AdminUserCountsResponse(BaseModel):
    projects_created: int
    assigned_tasks: int
    created_tasks: int
    notifications: int
    admin_logs_as_target: int


class AdminUserDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_email_verified: bool
    profile_pic: str | None
    created_at: datetime
    counts: AdminUserCountsResponse


class AdminUserRoleUpdateRequest(BaseModel):
    role: Literal["user", "admin"]


class AdminUserActionResponse(BaseModel):
    message: str
    user: AdminUserDetailResponse
    admin_log_id: int