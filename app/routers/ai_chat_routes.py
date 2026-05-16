from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.ai_chat_schema import (
    AIChatHistoryResponse,
    AIChatRequest,
    AIChatResponse,
)
from app.services.ai_chat_service import (
    create_ai_chat_exchange,
    get_project_chat_history,
)
from app.services.project_service import (
    get_my_personal_project_by_id,
    get_project_membership,
    get_team_project_by_id,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

PROJECT_NOT_FOUND = "Project not found"
NOT_ALLOWED = "You are not allowed to perform this action"

router = APIRouter(
    tags=["AI Chat Assistant"],
)


@router.post(
    "/projects/{project_id}/chat",
    response_model=AIChatResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def chat_with_personal_project_ai(
    project_id: int,
    chat_data: AIChatRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_my_personal_project_by_id(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    user_message, ai_message, assistant_context = create_ai_chat_exchange(
        db=db,
        project=project,
        current_user=current_user,
        chat_data=chat_data,
    )

    return {
        "user_message": user_message,
        "ai_message": ai_message,
        "assistant_context": assistant_context,
    }


@router.get(
    "/projects/{project_id}/chat",
    response_model=AIChatHistoryResponse,
)
def read_personal_project_chat_history(
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    project = get_my_personal_project_by_id(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )

    if project is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    messages = get_project_chat_history(
        db=db,
        project=project,
        limit=limit,
        offset=offset,
    )

    return {"messages": messages}


@router.post(
    "/teams/{team_id}/projects/{project_id}/chat",
    response_model=AIChatResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def chat_with_team_project_ai(
    team_id: int,
    project_id: int,
    chat_data: AIChatRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    project = get_team_project_by_id(
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

    user_message, ai_message, assistant_context = create_ai_chat_exchange(
        db=db,
        project=project,
        current_user=current_user,
        chat_data=chat_data,
    )

    return {
        "user_message": user_message,
        "ai_message": ai_message,
        "assistant_context": assistant_context,
    }


@router.get(
    "/teams/{team_id}/projects/{project_id}/chat",
    response_model=AIChatHistoryResponse,
)
def read_team_project_chat_history(
    team_id: int,
    project_id: int,
    db: DBSession,
    current_user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    project = get_team_project_by_id(
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

    messages = get_project_chat_history(
        db=db,
        project=project,
        limit=limit,
        offset=offset,
    )

    return {"messages": messages}