from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.productivity_insight_schema import ProductivityInsightsResponse
from app.services.productivity_insight_service import generate_my_productivity_insights

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

router = APIRouter(
    prefix="/insights",
    tags=["Productivity Insights"],
)


@router.get(
    "/me",
    response_model=ProductivityInsightsResponse,
)
def get_my_productivity_insights(
    db: DBSession,
    current_user: CurrentUser,
):
    return generate_my_productivity_insights(
        db=db,
        current_user=current_user,
    )
