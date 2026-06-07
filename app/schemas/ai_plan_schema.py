from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AIPlanGenerateRequest(BaseModel):
    input_prompt: str | None = Field(default=None, max_length=5000)
    create_tasks: bool = True
    task_count: int = Field(default=6, ge=3, le=12)
    prompt: str | None = Field(default=None, max_length=5000)
    generate_tasks: bool | None = None
    overwrite_existing_tasks: bool = False
    preferred_task_count: int | None = Field(default=None, ge=3, le=12)
    include_milestones: bool = True

    @model_validator(mode="after")
    def normalize_new_generate_contract(self) -> "AIPlanGenerateRequest":
        if self.prompt is not None:
            self.input_prompt = self.prompt

        if self.generate_tasks is not None:
            self.create_tasks = self.generate_tasks

        if self.preferred_task_count is not None:
            self.task_count = self.preferred_task_count

        return self


class AIPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_id: int
    project_id: int
    generated_by: int | None
    input_prompt: str
    generated_plan: dict[str, Any]
    created_at: datetime


class AIPlanGeneratedTaskResponse(BaseModel):
    task_id: int
    title: str
    description: str | None
    priority: str
    estimated_hours: float | None
    status: str
    due_date: datetime | None


class AIPlanGenerateResponse(BaseModel):
    project_id: int
    plan_id: int
    summary: str
    tasks_created: int
    tasks: list[AIPlanGeneratedTaskResponse]
