from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user_summary_schema import UserSummaryResponse


class CommentCreate(BaseModel):
    comment_text: str = Field(..., min_length=1, max_length=5000)


class CommentUpdate(BaseModel):
    comment_text: str | None = Field(default=None, min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    comment_id: int
    task_id: int
    user_id: int
    user_username: str | None = None
    user_full_name: str | None = None
    user_profile_pic: str | None = None
    comment_text: str
    created_at: datetime
    user: UserSummaryResponse | None = None


class CommentDeleteResponse(BaseModel):
    message: str
