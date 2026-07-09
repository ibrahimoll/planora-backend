from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.user_summary_schema import UserSummaryResponse
from app.services.profile_service import (
    PROFILE_PICTURE_URL_PREFIX,
    is_profile_picture_data_url,
)


class CommentCreate(BaseModel):
    comment_text: str = Field(..., min_length=1, max_length=5000)


class CommentUpdate(BaseModel):
    comment_text: str | None = Field(
        default=None,
        min_length=1,
        max_length=5000,
    )


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

    @model_validator(mode="after")
    def normalize_profile_picture(self) -> "CommentResponse":
        profile_pic = self.user_profile_pic

        if profile_pic is None and self.user is not None:
            profile_pic = self.user.profile_pic

        if is_profile_picture_data_url(profile_pic):
            profile_pic = (
                f"{PROFILE_PICTURE_URL_PREFIX}{self.user_id}"
            )

        self.user_profile_pic = profile_pic

        if self.user is not None:
            self.user.profile_pic = profile_pic

        return self


class CommentDeleteResponse(BaseModel):
    message: str