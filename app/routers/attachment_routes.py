from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi import status as http_status
from fastapi.responses import FileResponse
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
    STORAGE_URL_PREFIX,
    create_attachment,
    delete_attachment,
    get_attachment_by_file_url,
    get_attachment_by_id,
    get_local_file_path,
    get_project_attachments,
    get_task_attachments,
)
from app.services.project_service import (
    can_manage_project,
    get_project_membership,
)
from app.services.task_service import (
    get_my_personal_project_for_tasks,
    get_task_for_personal_project_by_id,
    get_task_for_team_project_by_id,
    get_team_project_for_tasks,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]
UploadedFile = Annotated[UploadFile, File(...)]

PROJECT_NOT_FOUND = "Project not found"
TASK_NOT_FOUND = "Task not found"
ATTACHMENT_NOT_FOUND = "Attachment not found"
NOT_ALLOWED = "You are not allowed to perform this action"
ATTACHMENT_DELETED = "Attachment deleted successfully."

router = APIRouter(
    tags=["Attachments"],
)


def require_personal_project_access(
    db: Session,
    project_id: int,
    current_user: User,
) -> Project:
    project = get_my_personal_project_for_tasks(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    return project


def require_personal_task_access(
    db: Session,
    project: Project,
    task_id: int,
) -> Task:
    task = get_task_for_personal_project_by_id(
        db=db,
        project=project,
        task_id=task_id,
    )

    if task is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=TASK_NOT_FOUND,
        )

    return task


def require_team_project_access(
    db: Session,
    team_id: int,
    project_id: int,
    current_user: User,
) -> tuple[Project, ProjectMember]:
    project = get_team_project_for_tasks(
        db=db,
        team_id=team_id,
        project_id=project_id,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    membership = get_project_membership(
        db=db,
        project_id=project_id,
        user_id=current_user.user_id,
    )

    if membership is None:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    return project, membership


def require_team_task_access(
    db: Session,
    project: Project,
    task_id: int,
) -> Task:
    task = get_task_for_team_project_by_id(
        db=db,
        project=project,
        task_id=task_id,
    )

    if task is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=TASK_NOT_FOUND,
        )

    return task


def can_delete_team_attachment(
    attachment_uploaded_by: int,
    current_user: User,
    membership: ProjectMember,
) -> bool:
    return (
        attachment_uploaded_by == current_user.user_id
        or can_manage_project(membership)
    )


def can_access_attachment_file(
    db: Session,
    attachment_project: Project,
    current_user: User,
) -> bool:
    if attachment_project.project_type == "personal":
        return attachment_project.created_by == current_user.user_id

    if attachment_project.project_type == "team":
        membership = get_project_membership(
            db=db,
            project_id=attachment_project.project_id,
            user_id=current_user.user_id,
        )

        return membership is not None

    return False


@router.get(
    f"{STORAGE_URL_PREFIX}{{stored_file_name}}",
    include_in_schema=False,
)
def download_attachment_file(
    stored_file_name: str,
    db: DBSession,
    current_user: CurrentUser,
):
    attachment = get_attachment_by_file_url(
        db=db,
        file_url=f"{STORAGE_URL_PREFIX}{stored_file_name}",
    )

    if attachment is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=ATTACHMENT_NOT_FOUND,
        )

    if not can_access_attachment_file(
        db=db,
        attachment_project=attachment.project,
        current_user=current_user,
    ):
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=ATTACHMENT_NOT_FOUND,
        )

    file_path = get_local_file_path(file_url=attachment.file_url)

    if file_path is None or not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=ATTACHMENT_NOT_FOUND,
        )

    return FileResponse(
        path=file_path,
        media_type=attachment.file_type or "application/octet-stream",
        filename=attachment.file_name,
    )


@router.post(
    "/projects/{project_id}/attachments",
    response_model=AttachmentResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def upload_personal_project_attachment(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
    file: UploadedFile,
):
    project = require_personal_project_access(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    return create_attachment(
        db=db,
        project=project,
        current_user=current_user,
        file=file,
    )


@router.get(
    "/projects/{project_id}/attachments",
    response_model=list[AttachmentResponse],
)
def list_personal_project_attachments(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = require_personal_project_access(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    return get_project_attachments(
        db=db,
        project=project,
    )


@router.delete(
    "/projects/{project_id}/attachments/{attachment_id}",
    response_model=AttachmentDeleteResponse,
)
def delete_personal_project_attachment(
    project_id: int,
    attachment_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = require_personal_project_access(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    attachment = get_attachment_by_id(
        db=db,
        project=project,
        attachment_id=attachment_id,
    )

    if attachment is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=ATTACHMENT_NOT_FOUND,
        )

    delete_attachment(
        db=db,
        attachment=attachment,
    )

    return AttachmentDeleteResponse(
        message=ATTACHMENT_DELETED,
    )


@router.post(
    "/projects/{project_id}/tasks/{task_id}/attachments",
    response_model=AttachmentResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def upload_personal_task_attachment(
    project_id: int,
    task_id: int,
    db: DBSession,
    current_user: CurrentUser,
    file: UploadedFile,
):
    project = require_personal_project_access(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    task = require_personal_task_access(
        db=db,
        project=project,
        task_id=task_id,
    )

    return create_attachment(
        db=db,
        project=project,
        task=task,
        current_user=current_user,
        file=file,
    )


@router.get(
    "/projects/{project_id}/tasks/{task_id}/attachments",
    response_model=list[AttachmentResponse],
)
def list_personal_task_attachments(
    project_id: int,
    task_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = require_personal_project_access(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    task = require_personal_task_access(
        db=db,
        project=project,
        task_id=task_id,
    )

    return get_task_attachments(
        db=db,
        project=project,
        task=task,
    )


@router.delete(
    "/projects/{project_id}/tasks/{task_id}/attachments/{attachment_id}",
    response_model=AttachmentDeleteResponse,
)
def delete_personal_task_attachment(
    project_id: int,
    task_id: int,
    attachment_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = require_personal_project_access(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    task = require_personal_task_access(
        db=db,
        project=project,
        task_id=task_id,
    )

    attachment = get_attachment_by_id(
        db=db,
        project=project,
        task=task,
        attachment_id=attachment_id,
    )

    if attachment is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=ATTACHMENT_NOT_FOUND,
        )

    delete_attachment(
        db=db,
        attachment=attachment,
    )

    return AttachmentDeleteResponse(
        message=ATTACHMENT_DELETED,
    )


@router.post(
    "/teams/{team_id}/projects/{project_id}/attachments",
    response_model=AttachmentResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def upload_team_project_attachment(
    team_id: int,
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
    file: UploadedFile,
):
    project, _membership = require_team_project_access(
        db=db,
        team_id=team_id,
        project_id=project_id,
        current_user=current_user,
    )

    return create_attachment(
        db=db,
        project=project,
        current_user=current_user,
        file=file,
    )


@router.get(
    "/teams/{team_id}/projects/{project_id}/attachments",
    response_model=list[AttachmentResponse],
)
def list_team_project_attachments(
    team_id: int,
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project, _membership = require_team_project_access(
        db=db,
        team_id=team_id,
        project_id=project_id,
        current_user=current_user,
    )

    return get_project_attachments(
        db=db,
        project=project,
    )


@router.delete(
    "/teams/{team_id}/projects/{project_id}/attachments/{attachment_id}",
    response_model=AttachmentDeleteResponse,
)
def delete_team_project_attachment(
    team_id: int,
    project_id: int,
    attachment_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project, membership = require_team_project_access(
        db=db,
        team_id=team_id,
        project_id=project_id,
        current_user=current_user,
    )

    attachment = get_attachment_by_id(
        db=db,
        project=project,
        attachment_id=attachment_id,
    )

    if attachment is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=ATTACHMENT_NOT_FOUND,
        )

    if not can_delete_team_attachment(
        attachment_uploaded_by=attachment.uploaded_by,
        current_user=current_user,
        membership=membership,
    ):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    delete_attachment(
        db=db,
        attachment=attachment,
    )

    return AttachmentDeleteResponse(
        message=ATTACHMENT_DELETED,
    )


@router.post(
    "/teams/{team_id}/projects/{project_id}/tasks/{task_id}/attachments",
    response_model=AttachmentResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def upload_team_task_attachment(
    team_id: int,
    project_id: int,
    task_id: int,
    db: DBSession,
    current_user: CurrentUser,
    file: UploadedFile,
):
    project, _membership = require_team_project_access(
        db=db,
        team_id=team_id,
        project_id=project_id,
        current_user=current_user,
    )

    task = require_team_task_access(
        db=db,
        project=project,
        task_id=task_id,
    )

    return create_attachment(
        db=db,
        project=project,
        task=task,
        current_user=current_user,
        file=file,
    )


@router.get(
    "/teams/{team_id}/projects/{project_id}/tasks/{task_id}/attachments",
    response_model=list[AttachmentResponse],
)
def list_team_task_attachments(
    team_id: int,
    project_id: int,
    task_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project, _membership = require_team_project_access(
        db=db,
        team_id=team_id,
        project_id=project_id,
        current_user=current_user,
    )

    task = require_team_task_access(
        db=db,
        project=project,
        task_id=task_id,
    )

    return get_task_attachments(
        db=db,
        project=project,
        task=task,
    )


@router.delete(
    "/teams/{team_id}/projects/{project_id}/tasks/{task_id}/attachments/{attachment_id}",
    response_model=AttachmentDeleteResponse,
)
def delete_team_task_attachment(
    team_id: int,
    project_id: int,
    task_id: int,
    attachment_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project, membership = require_team_project_access(
        db=db,
        team_id=team_id,
        project_id=project_id,
        current_user=current_user,
    )

    task = require_team_task_access(
        db=db,
        project=project,
        task_id=task_id,
    )

    attachment = get_attachment_by_id(
        db=db,
        project=project,
        task=task,
        attachment_id=attachment_id,
    )

    if attachment is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=ATTACHMENT_NOT_FOUND,
        )

    if not can_delete_team_attachment(
        attachment_uploaded_by=attachment.uploaded_by,
        current_user=current_user,
        membership=membership,
    ):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    delete_attachment(
        db=db,
        attachment=attachment,
    )

    return AttachmentDeleteResponse(
        message=ATTACHMENT_DELETED,
    )
