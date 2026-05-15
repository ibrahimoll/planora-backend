from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class InvitationRole(StrEnum):
    admin = "admin"
    manager = "manager"
    member = "member"


class TeamInvitationRole(StrEnum):
    admin = "admin"
    member = "member"

class InvitationStatus(StrEnum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"


class TeamInvitationCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    role: TeamInvitationRole = TeamInvitationRole.member


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    invitation_id: int
    invited_by: int
    invited_user_id: int | None
    email: str | None
    team_id: int
    project_id: int | None
    role: InvitationRole
    status: InvitationStatus
    expires_at: datetime
    created_at: datetime
    responded_at: datetime | None


class InvitationMessageResponse(BaseModel):
    message: str