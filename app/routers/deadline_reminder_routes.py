from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user, get_current_admin_user
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
CurrentAdmin = Annotated[User, Depends(get_current_admin_user)]
DeadlineReminderLimitQuery = Annotated[int, Query(ge=1, le=100)]

router = APIRouter(
    prefix="/deadline-reminders",
    tags=["Deadline Reminders"],
)

@router.post(
    "/run",
    response_model=DeadlineReminderRunResponse,
)
def run_deadline_reminders(
    request_data: DeadlineReminderRunRequest,
    db: DBSession,
    _current_admin: CurrentAdmin,
):
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
    limit: DeadlineReminderLimitQuery = 50,
):
    return get_my_deadline_reminders(
        db=db,
        current_user=current_user,
        limit=limit,
    )
