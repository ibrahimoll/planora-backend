from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attachment_id: int
    project_id: int
    task_id: int | None
    uploaded_by: int
    file_name: str
    file_url: str
    file_type: str | None
    uploaded_at: datetime


class AttachmentDeleteResponse(BaseModel):
    message: str