from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AIPlanGenerateRequest(BaseModel):
    input_prompt: str | None = Field(default=None, max_length=5000)
    create_tasks: bool = True
    task_count: int = Field(default=6, ge=3, le=12)


class AIPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_id: int
    project_id: int
    generated_by: int | None
    input_prompt: str
    generated_plan: dict[str, Any]
    created_at: datetime