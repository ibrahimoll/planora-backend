from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.project_schema import ProjectResponse, ProjectType


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
    success: bool = True
    message: str = ""
    summary: str
    tasks_created: int
    tasks_skipped_as_duplicates: int = 0
    improvement_summary: str | None = None
    rejected_generic_count: int = 0
    rejected_unrelated_count: int = 0
    ai_generation_status: str = "generated"
    tasks: list[AIPlanGeneratedTaskResponse]


class AIPlanPreviewRequest(BaseModel):
    project_idea: str = Field(..., min_length=12, max_length=5000)
    deadline: datetime
    project_type: ProjectType = ProjectType.personal
    team_id: int | None = None
    available_hours_per_week: int = Field(default=8, ge=1, le=168)
    preferred_task_count: int = Field(default=8, ge=3, le=12)
    requirements: str | None = Field(default=None, max_length=5000)
    include_milestones: bool = True


class AIPlanPreviewTaskResponse(BaseModel):
    suggested_order: int
    title: str
    description: str | None
    priority: str
    estimated_hours: float | None
    status: str = "todo"
    due_date: datetime | None
    assigned_to: int | None = None


class AIPlanPreviewResponse(BaseModel):
    success: bool = True
    message: str = ""
    ai_generation_status: str = "generated"
    source: str
    domain: str
    project_title: str
    description: str | None
    project_type: ProjectType
    team_id: int | None
    deadline: datetime
    summary: str
    tasks: list[AIPlanPreviewTaskResponse]
    milestones: list[dict[str, Any]]
    risks: list[dict[str, str]]
    recommendations: list[str]
    project_idea: str
    requirements: str | None = None
    available_hours_per_week: int
    preferred_task_count: int
    rejected_generic_count: int = 0
    rejected_unrelated_count: int = 0


class AIPlanAcceptPreviewRequest(BaseModel):
    preview: AIPlanPreviewResponse


class AIPlanAcceptPreviewResponse(AIPlanGenerateResponse):
    project: ProjectResponse
