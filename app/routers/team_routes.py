from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.team_schema import (
    TeamCreate,
    TeamDeleteResponse,
    TeamMemberAdd,
    TeamMemberResponse,
    TeamMemberUpdate,
    TeamResponse,
    TeamUpdate,
)
from app.services.team_service import (
    add_team_member,
    can_manage_team,
    create_team,
    delete_team,
    get_my_teams,
    get_team_by_id,
    get_team_members,
    get_team_membership,
    get_user_by_email,
    is_team_owner,
    remove_team_member,
    update_team,
    update_team_member_role,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

TEAM_NOT_FOUND = "Team not found"
MEMBER_NOT_FOUND = "Team member not found"
USER_NOT_FOUND = "User not found"
NOT_ALLOWED = "You are not allowed to perform this action"
ALREADY_MEMBER = "User is already a member of this team"

router = APIRouter(
    prefix="/teams",
    tags=["Teams"],
)


@router.post(
    "",
    response_model=TeamResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def create_new_team(
    team_data: TeamCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    return create_team(
        db=db,
        team_data=team_data,
        current_user=current_user,
    )


@router.get(
    "",
    response_model=list[TeamResponse],
)
def get_teams(
    db: DBSession,
    current_user: CurrentUser,
):
    return get_my_teams(
        db=db,
        current_user=current_user,
    )


@router.get(
    "/{team_id}",
    response_model=TeamResponse,
)
def get_team(
    team_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    team = get_team_by_id(
        db=db,
        team_id=team_id,
    )

    if team is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=TEAM_NOT_FOUND,
        )

    membership = get_team_membership(
        db=db,
        team_id=team_id,
        user_id=current_user.user_id,
    )

    if membership is None:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    return team


@router.patch(
    "/{team_id}",
    response_model=TeamResponse,
)
def update_existing_team(
    team_id: int,
    team_data: TeamUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    team = get_team_by_id(
        db=db,
        team_id=team_id,
    )

    if team is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=TEAM_NOT_FOUND,
        )

    membership = get_team_membership(
        db=db,
        team_id=team_id,
        user_id=current_user.user_id,
    )

    if membership is None or not can_manage_team(membership):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    return update_team(
        db=db,
        team=team,
        team_data=team_data,
    )


@router.delete(
    "/{team_id}",
    response_model=TeamDeleteResponse,
)
def delete_existing_team(
    team_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    team = get_team_by_id(
        db=db,
        team_id=team_id,
    )

    if team is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=TEAM_NOT_FOUND,
        )

    membership = get_team_membership(
        db=db,
        team_id=team_id,
        user_id=current_user.user_id,
    )

    if membership is None or not is_team_owner(membership):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    delete_team(
        db=db,
        team=team,
    )

    return TeamDeleteResponse(
        message="Team deleted successfully.",
    )


@router.get(
    "/{team_id}/members",
    response_model=list[TeamMemberResponse],
)
def list_team_members(
    team_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    team = get_team_by_id(
        db=db,
        team_id=team_id,
    )

    if team is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=TEAM_NOT_FOUND,
        )

    membership = get_team_membership(
        db=db,
        team_id=team_id,
        user_id=current_user.user_id,
    )

    if membership is None:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    return get_team_members(
        db=db,
        team_id=team_id,
    )


@router.post(
    "/{team_id}/members",
    response_model=TeamMemberResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def add_member_to_team(
    team_id: int,
    member_data: TeamMemberAdd,
    db: DBSession,
    current_user: CurrentUser,
):
    team = get_team_by_id(
        db=db,
        team_id=team_id,
    )

    if team is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=TEAM_NOT_FOUND,
        )

    current_membership = get_team_membership(
        db=db,
        team_id=team_id,
        user_id=current_user.user_id,
    )

    if current_membership is None or not can_manage_team(current_membership):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    user_to_add = get_user_by_email(
        db=db,
        email=member_data.email,
    )

    if user_to_add is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=USER_NOT_FOUND,
        )

    existing_membership = get_team_membership(
        db=db,
        team_id=team_id,
        user_id=user_to_add.user_id,
    )

    if existing_membership is not None:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=ALREADY_MEMBER,
        )

    return add_team_member(
        db=db,
        team=team,
        user=user_to_add,
        role=member_data.role,
    )


@router.patch(
    "/{team_id}/members/{user_id}",
    response_model=TeamMemberResponse,
)
def update_member_role(
    team_id: int,
    user_id: int,
    member_data: TeamMemberUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    current_membership = get_team_membership(
        db=db,
        team_id=team_id,
        user_id=current_user.user_id,
    )

    if current_membership is None or not is_team_owner(current_membership):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    member = get_team_membership(
        db=db,
        team_id=team_id,
        user_id=user_id,
    )

    if member is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=MEMBER_NOT_FOUND,
        )

    if member.user_id == current_user.user_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Owner cannot change their own role.",
        )

    return update_team_member_role(
        db=db,
        member=member,
        role=member_data.role,
    )


@router.delete(
    "/{team_id}/members/{user_id}",
    response_model=TeamDeleteResponse,
)
def remove_member_from_team(
    team_id: int,
    user_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    current_membership = get_team_membership(
        db=db,
        team_id=team_id,
        user_id=current_user.user_id,
    )

    if current_membership is None or not can_manage_team(current_membership):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    member = get_team_membership(
        db=db,
        team_id=team_id,
        user_id=user_id,
    )

    if member is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=MEMBER_NOT_FOUND,
        )

    if member.role == "owner":
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Owner cannot be removed from the team.",
        )

    remove_team_member(
        db=db,
        member=member,
    )

    return TeamDeleteResponse(
        message="Team member removed successfully.",
    )