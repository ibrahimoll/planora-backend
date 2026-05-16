from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class RiskLevel(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class RiskAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    risk_id: int
    project_id: int
    risk_level: RiskLevel
    predicted_delay_days: int
    reason: str
    recommendation: str
    created_at: datetime


class RiskAnalysisPreviewResponse(BaseModel):
    project_id: int
    risk_level: RiskLevel
    predicted_delay_days: int
    reason: str
    recommendation: str
    total_tasks: int
    completed_tasks: int
    overdue_tasks: int
    blocked_tasks: int
    remaining_estimated_hours: float
    days_until_deadline: int