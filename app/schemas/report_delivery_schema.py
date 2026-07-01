from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ReportDeliveryRequest(BaseModel):
    address: str
    name: str | None = None
    note: str | None = None


class ReportDeliveryResponse(BaseModel):
    success: bool = True
    message: str
    project_id: int
    project_title: str
    address: str
    delivered_at: datetime
    export_id: int | None = None


class ReportRequestTokenResponse(BaseModel):
    project_id: int
    address: str
    name: str | None = None
    request_id: int | None = None
    status: str | None = None
