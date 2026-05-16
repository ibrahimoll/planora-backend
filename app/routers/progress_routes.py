from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.progress_schema import ProjectProgressResponse
from app.services.progress_service import (
    generate_project_progress,
    get_accessible_project_for_progress,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

PROJECT_NOT_FOUND = "Project not found"

router = APIRouter(
    prefix="/projects",
    tags=["Progress"],
)


@router.get(
    "/{project_id}/progress",
    response_model=ProjectProgressResponse,
)
def get_project_progress(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_accessible_project_for_progress(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    return generate_project_progress(
        db=db,
        project=project,
        current_user=current_user,
    )