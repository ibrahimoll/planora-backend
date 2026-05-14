from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.attachment_schema import (
    AttachmentDeleteResponse,
    AttachmentResponse,
)
from app.services.attachment_service import (
    create_attachment,
    delete_attachment,
    get_attachment_by_id,
    get_project_attachments,
    get_task_attachments,
)

router = APIRouter(
    tags=["Attachments"],
)