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

BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BASE_DIR / "uploads" / "attachments"
STORAGE_URL_PREFIX = "/uploads/attachments/"
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
UPLOAD_CHUNK_SIZE_BYTES = 1024 * 1024

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


def clean_original_file_name(file_name: str | None) -> str:
    original_name = (file_name or "").replace("\\", "/").split("/")[-1].strip()

    if not original_name:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="File name is required.",
        )

    if len(original_name) > 255:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="File name must be 255 characters or less.",
        )

    return original_name


def validate_upload_file(file: UploadFile) -> tuple[str, str]:
    original_name = clean_original_file_name(file.filename)
    suffix = Path(original_name).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="File type is not allowed.",
        )

    return original_name, suffix


def save_uploaded_file(file: UploadFile) -> tuple[str, str, str | None]:
    original_file_name, suffix = validate_upload_file(file=file)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    stored_file_name = f"{uuid.uuid4().hex}{suffix}"
    storage_path = UPLOAD_DIR / stored_file_name

    bytes_written = 0

    try:
        with storage_path.open("xb") as output_file:
            while chunk := file.file.read(UPLOAD_CHUNK_SIZE_BYTES):
                bytes_written += len(chunk)

                if bytes_written > MAX_FILE_SIZE_BYTES:
                    raise HTTPException(
                        status_code=http_status.HTTP_400_BAD_REQUEST,
                        detail="File size must be 10MB or less.",
                    )

                output_file.write(chunk)
    except Exception:
        storage_path.unlink(missing_ok=True)
        raise

    if bytes_written == 0:
        storage_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="File cannot be empty.",
        )

    file_url = f"{STORAGE_URL_PREFIX}{stored_file_name}"
    file_type = file.content_type

    return original_file_name, file_url, file_type


def get_stored_file_name(file_url: str) -> str | None:
    if not file_url.startswith(STORAGE_URL_PREFIX):
        return None

    stored_file_name = file_url.replace(STORAGE_URL_PREFIX, "", 1)

    if not stored_file_name or stored_file_name != Path(stored_file_name).name:
        return None

    return stored_file_name


def get_local_file_path(file_url: str) -> Path | None:
    stored_file_name = get_stored_file_name(file_url)

    if stored_file_name is None:
        return None

    upload_dir = UPLOAD_DIR.resolve()
    file_path = (UPLOAD_DIR / stored_file_name).resolve()

    try:
        file_path.relative_to(upload_dir)
    except ValueError:
        return None

    return file_path


def delete_local_file(file_url: str) -> None:
    file_path = get_local_file_path(file_url)

    if file_path is not None and file_path.exists() and file_path.is_file():
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

    try:
        db.add(attachment)
        db.commit()
        db.refresh(attachment)
    except Exception:
        db.rollback()
        delete_local_file(file_url=file_url)
        raise

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


def get_attachment_by_file_url(
    db: Session,
    file_url: str,
) -> Attachment | None:
    stmt = select(Attachment).where(Attachment.file_url == file_url)

    return db.execute(stmt).scalars().first()


def delete_attachment(
    db: Session,
    attachment: Attachment,
) -> None:
    file_url = attachment.file_url

    db.delete(attachment)
    db.commit()

    delete_local_file(file_url=file_url)
