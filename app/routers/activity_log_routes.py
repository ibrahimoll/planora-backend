from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.activity_log_schema import (
    ActivityLogEventType,
    ActivityLogResponse,
)
from app.services.activity_log_service import (
    build_activity_log_response,
    get_accessible_project_for_activity,
    get_project_activity_logs,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

PROJECT_NOT_FOUND = 
ActivityEventTypeQuery = Annotated[ActivityLogEventType | None, Query(default=None)]
ActivityLimitQuery = Annotated[int, Query(default=50, ge=1, le=100)]
ActivityOffsetQuery = Annotated[int, Query(default=0, ge=0)]

PROJECT_NOT_FOUND = "Project not found"

router = APIRouter(
    prefix="/projects",
    tags=["Activity Timeline"],
)


@router.get(
    "/{project_id}/activity",
    response_model=list[ActivityLogResponse],
)
def list_project_activity(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
    event_type: ActivityEventTypeQuery = None,
    limit: ActivityLimitQuery = 50,
    offset: ActivityOffsetQuery = 0,
):
    project = get_accessible_project_for_activity(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    activity_logs = get_project_activity_logs(
        db=db,
        project=project,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )

    return [
        build_activity_log_response(activity_log)
        for activity_log in activity_logs
    ]
