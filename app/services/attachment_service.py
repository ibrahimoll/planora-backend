from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from fastapi import status as http_status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.attachment import Attachment
from app.models.project import Project
from app.models.task import Task
from app.models.user import User

UPLOAD_DIR = Path("uploads/attachments")
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".txt",
    ".zip",
}


def validate_upload_file(file: UploadFile) -> str:
    original_name = file.filename or ""

    if not original_name:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="File name is required.",
        )

    suffix = Path(original_name).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="File type is not allowed.",
        )

    return suffix


def save_uploaded_file(file: UploadFile) -> tuple[str, str, str | None]:
    suffix = validate_upload_file(file=file)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    stored_file_name = f"{uuid.uuid4().hex}{suffix}"
    storage_path = UPLOAD_DIR / stored_file_name

    content = file.file.read()

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="File size must be 10MB or less.",
        )

    storage_path.write_bytes(content)

    original_file_name = file.filename or stored_file_name
    file_url = f"/uploads/attachments/{stored_file_name}"
    file_type = file.content_type

    return original_file_name, file_url, file_type


def delete_local_file(file_url: str) -> None:
    prefix = "/uploads/attachments/"

    if not file_url.startswith(prefix):
        return

    stored_file_name = file_url.replace(prefix, "", 1)
    file_path = UPLOAD_DIR / stored_file_name

    if file_path.exists() and file_path.is_file():
        file_path.unlink()


def create_attachment(
    db: Session,
    project: Project,
    current_user: User,
    file: UploadFile,
    task: Task | None = None,
) -> Attachment:
    file_name, file_url, file_type = save_uploaded_file(file=file)

    attachment = Attachment(
        project_id=project.project_id,
        task_id=task.task_id if task is not None else None,
        uploaded_by=current_user.user_id,
        file_name=file_name,
        file_url=file_url,
        file_type=file_type,
    )

    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return attachment


def get_project_attachments(
    db: Session,
    project: Project,
) -> list[Attachment]:
    stmt = (
        select(Attachment)
        .where(
            Attachment.project_id == project.project_id,
            Attachment.task_id.is_(None),
        )
        .order_by(Attachment.uploaded_at.desc())
    )

    return list(db.execute(stmt).scalars().all())


def get_task_attachments(
    db: Session,
    project: Project,
    task: Task,
) -> list[Attachment]:
    stmt = (
        select(Attachment)
        .where(
            Attachment.project_id == project.project_id,
            Attachment.task_id == task.task_id,
        )
        .order_by(Attachment.uploaded_at.desc())
    )

    return list(db.execute(stmt).scalars().all())


def get_attachment_by_id(
    db: Session,
    project: Project,
    attachment_id: int,
    task: Task | None = None,
) -> Attachment | None:
    stmt = select(Attachment).where(
        Attachment.attachment_id == attachment_id,
        Attachment.project_id == project.project_id,
    )

    if task is None:
        stmt = stmt.where(Attachment.task_id.is_(None))
    else:
        stmt = stmt.where(Attachment.task_id == task.task_id)

    return db.execute(stmt).scalars().first()


def delete_attachment(
    db: Session,
    attachment: Attachment,
) -> None:
    file_url = attachment.file_url

    db.delete(attachment)
    db.commit()

    delete_local_file(file_url=file_url)