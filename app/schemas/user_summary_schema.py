from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr


class UserSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    email: EmailStr
    full_name: str
    profile_pic: str | None
