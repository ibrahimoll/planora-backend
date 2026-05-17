from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DevicePlatform(StrEnum):
    ANDROID = "android"
    IOS = "ios"
    WEB = "web"


class DeviceTokenCreate(BaseModel):
    token: str = Field(..., min_length=10, max_length=5000)
    platform: DevicePlatform


class DeviceTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    device_token_id: int
    user_id: int
    token: str
    platform: DevicePlatform
    is_active: bool
    last_used_at: datetime
    created_at: datetime


class NotificationPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    preference_id: int
    user_id: int
    task_notifications: bool
    project_notifications: bool
    team_notifications: bool
    comment_notifications: bool
    mention_notifications: bool
    invite_notifications: bool
    deadline_notifications: bool
    ai_notifications: bool
    risk_notifications: bool
    system_notifications: bool
    push_enabled: bool
    email_enabled: bool
    updated_at: datetime
    created_at: datetime


class NotificationPreferenceUpdate(BaseModel):
    task_notifications: bool | None = None
    project_notifications: bool | None = None
    team_notifications: bool | None = None
    comment_notifications: bool | None = None
    mention_notifications: bool | None = None
    invite_notifications: bool | None = None
    deadline_notifications: bool | None = None
    ai_notifications: bool | None = None
    risk_notifications: bool | None = None
    system_notifications: bool | None = None
    push_enabled: bool | None = None
    email_enabled: bool | None = None


class PushNotificationMessageResponse(BaseModel):
    message: str