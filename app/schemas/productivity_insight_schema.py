from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class InsightHealthStatus(str, Enum):
    excellent = "excellent"
    good = "good"
    needs_attention = "needs_attention"
    at_risk = "at_risk"


class ProductivitySummary(BaseModel):
    total_projects: int
    active_projects: int
    completed_projects: int
    total_tasks: int
    assigned_tasks: int
    completed_assigned_tasks: int
    overdue_assigned_tasks: int
    blocked_assigned_tasks: int
    completion_percentage: float


class WorkloadInsight(BaseModel):
    assigned_incomplete_tasks: int
    estimated_hours_remaining: float
    high_priority_open_tasks: int
    overloaded: bool


class ProjectInsightItem(BaseModel):
    project_id: int
    title: str
    project_type: str
    status: str
    deadline: datetime
    total_tasks: int
    completed_tasks: int
    assigned_tasks: int
    overdue_tasks: int
    blocked_tasks: int
    completion_percentage: float
    health_status: InsightHealthStatus


class ProductivityInsightsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    summary: ProductivitySummary
    workload: WorkloadInsight
    projects: list[ProjectInsightItem]
    recommendations: list[str]
    generated_at: datetime
