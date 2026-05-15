from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.deadline_reminder_schema import (
    DeadlineReminderResponse,
    DeadlineReminderRunRequest,
    DeadlineReminderRunResponse,
)
from app.services.deadline_reminder_service import (
    get_my_deadline_reminders,
    run_deadline_reminder_scan,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

router = APIRouter(
    prefix="/deadline-reminders",
    tags=["Deadline Reminders"],
)

ADMIN_ONLY = "Only admins can run deadline reminder scans"


def require_admin_user(current_user: User) -> None:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=ADMIN_ONLY,
        )


@router.post(
    "/run",
    response_model=DeadlineReminderRunResponse,
)
def run_deadline_reminders(
    request_data: DeadlineReminderRunRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    require_admin_user(current_user)

    result = run_deadline_reminder_scan(
        db=db,
        hours_ahead=request_data.hours_ahead,
        include_overdue=request_data.include_overdue,
    )

    return DeadlineReminderRunResponse(**result)


@router.get(
    "/me",
    response_model=list[DeadlineReminderResponse],
)
def list_my_deadline_reminders(
    db: DBSession,
    current_user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=100),
):
    return get_my_deadline_reminders(
        db=db,
        current_user=current_user,
        limit=limit,
    )