from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.invitation_schema import (
    InvitationResponse,
    TeamInvitationCreate,
)
from app.services.invitation_service import (
    accept_team_invitation,
    create_team_invitation,
    get_invitation_by_id,
    get_my_pending_invitations,
    get_pending_team_invitation,
    get_user_by_username,
    is_invitation_expired,
    mark_invitation_as_expired,
    reject_team_invitation,
)
from app.services.team_service import (
    can_manage_team,
    get_team_by_id,
    get_team_membership,
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]

TEAM_NOT_FOUND = "Team not found"
USER_NOT_FOUND = "User not found"
NOT_ALLOWED = "You are not allowed to perform this action"
ALREADY_MEMBER = "User is already a member of this team"
ALREADY_INVITED = "User already has a pending invitation for this team"
INVITATION_NOT_FOUND = "Invitation not found"

router = APIRouter(
    tags=["Invitations"],
)


@router.post(
    "/teams/{team_id}/invitations",
    response_model=InvitationResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def invite_user_to_team(
    team_id: int,
    invitation_data: TeamInvitationCreate,
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

    invited_user = get_user_by_username(
        db=db,
        username=invitation_data.username,
    )

    if invited_user is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=USER_NOT_FOUND,
        )

    if invited_user.user_id == current_user.user_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="You cannot invite yourself.",
        )

    existing_membership = get_team_membership(
        db=db,
        team_id=team_id,
        user_id=invited_user.user_id,
    )

    if existing_membership is not None:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=ALREADY_MEMBER,
        )

    pending_invitation = get_pending_team_invitation(
        db=db,
        team_id=team_id,
        invited_user_id=invited_user.user_id,
    )

    if pending_invitation is not None:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=ALREADY_INVITED,
        )

    return create_team_invitation(
        db=db,
        team=team,
        invited_user=invited_user,
        inviter=current_user,
        invitation_data=invitation_data,
    )


@router.get(
    "/invitations/me",
    response_model=list[InvitationResponse],
)
def list_my_pending_invitations(
    db: DBSession,
    current_user: CurrentUser,
):
    return get_my_pending_invitations(
        db=db,
        current_user=current_user,
    )


@router.post(
    "/invitations/{invitation_id}/accept",
    response_model=InvitationResponse,
)
def accept_invitation(
    invitation_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    invitation = get_invitation_by_id(
        db=db,
        invitation_id=invitation_id,
    )

    if invitation is None or invitation.invited_user_id != current_user.user_id:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=INVITATION_NOT_FOUND,
        )

    if invitation.status != "pending":
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invitation is no longer pending.",
        )

    if is_invitation_expired(invitation):
        return mark_invitation_as_expired(
            db=db,
            invitation=invitation,
        )

    existing_membership = get_team_membership(
        db=db,
        team_id=invitation.team_id,
        user_id=current_user.user_id,
    )

    if existing_membership is not None:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=ALREADY_MEMBER,
        )

    return accept_team_invitation(
        db=db,
        invitation=invitation,
        current_user=current_user,
    )


@router.post(
    "/invitations/{invitation_id}/reject",
    response_model=InvitationResponse,
)
def reject_invitation(
    invitation_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    invitation = get_invitation_by_id(
        db=db,
        invitation_id=invitation_id,
    )

    if invitation is None or invitation.invited_user_id != current_user.user_id:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=INVITATION_NOT_FOUND,
        )

    if invitation.status != "pending":
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invitation is no longer pending.",
        )

    if is_invitation_expired(invitation):
        return mark_invitation_as_expired(
            db=db,
            invitation=invitation,
        )

    return reject_team_invitation(
        db=db,
        invitation=invitation,
        current_user=current_user,
    )