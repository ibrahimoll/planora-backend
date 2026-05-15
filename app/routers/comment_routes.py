from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.comment import Comment
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.comment_schema import CommentCreate, CommentDeleteResponse, CommentResponse, CommentUpdate
from app.services.comment_service import create_comment_for_task, delete_comment, get_comment_for_task_by_id, get_comments_for_task, update_comment
from app.services.project_service import can_manage_project, get_project_membership
from app.services.task_service import get_my_personal_project_for_tasks, get_task_for_personal_project_by_id, get_task_for_team_project_by_id, get_team_project_for_tasks

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

PROJECT_NOT_FOUND = "Project not found"
TASK_NOT_FOUND = "Task not found"
COMMENT_NOT_FOUND = "Comment not found"
NOT_ALLOWED = "You are not allowed to perform this action"

router = APIRouter(tags=["Task Comments"])


def require_personal_task_access(db: Session, project_id: int, task_id: int, current_user: User) -> Task:
    project = get_my_personal_project_for_tasks(db=db, project_id=project_id, current_user=current_user)
    if project is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=PROJECT_NOT_FOUND)

    task = get_task_for_personal_project_by_id(db=db, project=project, task_id=task_id)
    if task is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=TASK_NOT_FOUND)

    return task


def require_team_task_access(db: Session, team_id: int, project_id: int, task_id: int, current_user: User) -> tuple[Task, ProjectMember]:
    project = get_team_project_for_tasks(db=db, team_id=team_id, project_id=project_id)
    if project is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=PROJECT_NOT_FOUND)

    membership = get_project_membership(db=db, project_id=project_id, user_id=current_user.user_id)
    if membership is None:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=NOT_ALLOWED)

    task = get_task_for_team_project_by_id(db=db, project=project, task_id=task_id)
    if task is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=TASK_NOT_FOUND)

    return task, membership


def get_comment_or_404(db: Session, task: Task, comment_id: int) -> Comment:
    comment = get_comment_for_task_by_id(db=db, task=task, comment_id=comment_id)
    if comment is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=COMMENT_NOT_FOUND)

    return comment


def can_modify_team_comment(comment: Comment, membership: ProjectMember, current_user: User) -> bool:
    return comment.user_id == current_user.user_id or can_manage_project(membership)


@router.post("/projects/{project_id}/tasks/{task_id}/comments", response_model=CommentResponse, status_code=http_status.HTTP_201_CREATED)
def create_personal_task_comment(project_id: int, task_id: int, comment_data: CommentCreate, db: DBSession, current_user: CurrentUser):
    task = require_personal_task_access(db=db, project_id=project_id, task_id=task_id, current_user=current_user)
    return create_comment_for_task(db=db, task=task, current_user=current_user, comment_data=comment_data)


@router.get("/projects/{project_id}/tasks/{task_id}/comments", response_model=list[CommentResponse])
def list_personal_task_comments(project_id: int, task_id: int, db: DBSession, current_user: CurrentUser):
    task = require_personal_task_access(db=db, project_id=project_id, task_id=task_id, current_user=current_user)
    return get_comments_for_task(db=db, task=task)


@router.get("/projects/{project_id}/tasks/{task_id}/comments/{comment_id}", response_model=CommentResponse)
def get_personal_task_comment(project_id: int, task_id: int, comment_id: int, db: DBSession, current_user: CurrentUser):
    task = require_personal_task_access(db=db, project_id=project_id, task_id=task_id, current_user=current_user)
    return get_comment_or_404(db=db, task=task, comment_id=comment_id)


@router.patch("/projects/{project_id}/tasks/{task_id}/comments/{comment_id}", response_model=CommentResponse)
def update_personal_task_comment(project_id: int, task_id: int, comment_id: int, comment_data: CommentUpdate, db: DBSession, current_user: CurrentUser):
    task = require_personal_task_access(db=db, project_id=project_id, task_id=task_id, current_user=current_user)
    comment = get_comment_or_404(db=db, task=task, comment_id=comment_id)
    return update_comment(db=db, task=task, current_user=current_user, comment=comment, comment_data=comment_data)


@router.delete("/projects/{project_id}/tasks/{task_id}/comments/{comment_id}", response_model=CommentDeleteResponse)
def delete_personal_task_comment(project_id: int, task_id: int, comment_id: int, db: DBSession, current_user: CurrentUser):
    task = require_personal_task_access(db=db, project_id=project_id, task_id=task_id, current_user=current_user)
    comment = get_comment_or_404(db=db, task=task, comment_id=comment_id)
    delete_comment(db=db, task=task, current_user=current_user, comment=comment)
    return CommentDeleteResponse(message="Comment deleted successfully.")


@router.post("/teams/{team_id}/projects/{project_id}/tasks/{task_id}/comments", response_model=CommentResponse, status_code=http_status.HTTP_201_CREATED)
def create_team_task_comment(team_id: int, project_id: int, task_id: int, comment_data: CommentCreate, db: DBSession, current_user: CurrentUser):
    task, _membership = require_team_task_access(db=db, team_id=team_id, project_id=project_id, task_id=task_id, current_user=current_user)
    return create_comment_for_task(db=db, task=task, current_user=current_user, comment_data=comment_data)


@router.get("/teams/{team_id}/projects/{project_id}/tasks/{task_id}/comments", response_model=list[CommentResponse])
def list_team_task_comments(team_id: int, project_id: int, task_id: int, db: DBSession, current_user: CurrentUser):
    task, _membership = require_team_task_access(db=db, team_id=team_id, project_id=project_id, task_id=task_id, current_user=current_user)
    return get_comments_for_task(db=db, task=task)


@router.get("/teams/{team_id}/projects/{project_id}/tasks/{task_id}/comments/{comment_id}", response_model=CommentResponse)
def get_team_task_comment(team_id: int, project_id: int, task_id: int, comment_id: int, db: DBSession, current_user: CurrentUser):
    task, _membership = require_team_task_access(db=db, team_id=team_id, project_id=project_id, task_id=task_id, current_user=current_user)
    return get_comment_or_404(db=db, task=task, comment_id=comment_id)


@router.patch("/teams/{team_id}/projects/{project_id}/tasks/{task_id}/comments/{comment_id}", response_model=CommentResponse)
def update_team_task_comment(team_id: int, project_id: int, task_id: int, comment_id: int, comment_data: CommentUpdate, db: DBSession, current_user: CurrentUser):
    task, membership = require_team_task_access(db=db, team_id=team_id, project_id=project_id, task_id=task_id, current_user=current_user)
    comment = get_comment_or_404(db=db, task=task, comment_id=comment_id)
    if not can_modify_team_comment(comment=comment, membership=membership, current_user=current_user):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=NOT_ALLOWED)

    return update_comment(db=db, task=task, current_user=current_user, comment=comment, comment_data=comment_data)


@router.delete("/teams/{team_id}/projects/{project_id}/tasks/{task_id}/comments/{comment_id}", response_model=CommentDeleteResponse)
def delete_team_task_comment(team_id: int, project_id: int, task_id: int, comment_id: int, db: DBSession, current_user: CurrentUser):
    task, membership = require_team_task_access(db=db, team_id=team_id, project_id=project_id, task_id=task_id, current_user=current_user)
    comment = get_comment_or_404(db=db, task=task, comment_id=comment_id)
    if not can_modify_team_comment(comment=comment, membership=membership, current_user=current_user):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=NOT_ALLOWED)

    delete_comment(db=db, task=task, current_user=current_user, comment=comment)
    return CommentDeleteResponse(message="Comment deleted successfully.")
