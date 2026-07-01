from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ReportRequestStatus(StrEnum):
    pending = "pending"
    ready = "ready"
    rejected = "rejected"


class ReportRequestUserSummary(BaseModel):
    user_id: int | None = None
    full_name: str | None = None
    email: str | None = None
    username: str | None = None


class ReportRequestProjectSummary(BaseModel):
    project_id: int
    title: str
    project_type: str
    status: str


class ReportRequestItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_request_id: int
    project: ReportRequestProjectSummary
    requester: ReportRequestUserSummary
    status: ReportRequestStatus
    admin_note: str | None = None
    rejection_reason: str | None = None
    report_export_id: int | None = None
    requested_at: datetime
    resolved_at: datetime | None = None


class ReportRequestListResponse(BaseModel):
    items: list[ReportRequestItem]
    total: int = Field(ge=0)


class ReportRequestRejectRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class ReportRequestReadyRequest(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class ReportRequestActionResponse(BaseModel):
    success: bool = True
    message: str
    request: ReportRequestItem
