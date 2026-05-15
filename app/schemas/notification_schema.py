from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

class NotificationType(StrEnum):
    TASK = "task"
    PROJECT = "project"
    TEAM = "team"
    COMMENT = "comment"
    MENTION = "mention"
    INVITE = "invite"
    DEADLINE = "deadline"
    AI = "ai"
    RISK = "risk"
    SYSTEM = "system"


class NotificationCreate(BaseModel):
    user_id: int
    title: str = Field(..., min_length=1, max_length=150)
    message: str = Field(..., min_length=1, max_length=5000)
    type: NotificationType


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id:int
    user_id: int
    title: str
    message: str
    is_read: bool
    type: NotificationType
    created_at: datetime


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int


class NotificationMessageResponse(BaseModel):
    message: str