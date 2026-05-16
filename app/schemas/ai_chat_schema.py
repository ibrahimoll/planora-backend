from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AIChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("Message cannot be empty.")

        return cleaned


class AIChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: int
    user_id: int | None
    project_id: int
    message: str
    sender_type: str
    created_at: datetime


class AIChatResponse(BaseModel):
    user_message: AIChatMessageResponse
    ai_message: AIChatMessageResponse
    assistant_context: dict[str, Any]


class AIChatHistoryResponse(BaseModel):
    messages: list[AIChatMessageResponse]