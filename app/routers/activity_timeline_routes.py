from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.activity_timeline_schema import ActivityTimelineResponse
from app.services.activity_timeline_service import (
    get_accessible_project_for_activity_timeline,
    get_project_activity_timeline,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

PROJECT_NOT_FOUND = "Project not found"

router = APIRouter(
    prefix="/projects/{project_id}/activity",
    tags=["Activity Timeline"],
)


@router.get(
    "",
    response_model=ActivityTimelineResponse,
)
def list_project_activity_timeline(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=100),
):
    project = get_accessible_project_for_activity_timeline(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    return get_project_activity_timeline(
        db=db,
        project=project,
        limit=limit,
    )
