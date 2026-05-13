from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    comment_text: str = Field(..., min_length=1, max_length=5000)


class CommentUpdate(BaseModel):
    comment_text: str | None = Field(default=None, min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    comment_id: int
    task_id: int
    user_id: int
    comment_text: str
    created_at: datetime


class CommentDeleteResponse(BaseModel):
    message: str