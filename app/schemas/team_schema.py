from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field

class TeamRole(str, Enum):
    owner = "owner"
    admin = "admin"
    member = "member"

class TeamCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)

class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)

class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team_id: int
    name: str
    created_by: int
    created_at: datetime

class TeamDeleteResponse(BaseModel):
    message: str

class TeamMemberAdd(BaseModel):
    email: EmailStr
    role: TeamRole = TeamRole.member

class TeamMemberUpdate(BaseModel):
    role: TeamRole

class TeamMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    team_member_id: int
    team_id: int
    user_id: int
    role: TeamRole
    joined_at: datetime