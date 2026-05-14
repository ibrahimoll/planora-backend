from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_active_verified_user
from app.models.user import User
from app.schemas.profile_schema import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    DeleteAccountRequest,
    DeleteAccountResponse,
    ProfileResponse,
    ProfileUpdate,
    ProfileUpdateResponse,
)
from app.services.profile_service import (
    change_my_password,
    update_my_profile,
    delete_my_account,
)

router = APIRouter(
    prefix="/profile",
    tags=["Profile"],
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]


@router.get("")
def get_my_profile(
    current_user: CurrentUser,
) -> ProfileResponse:
    return ProfileResponse.model_validate(current_user)


@router.patch("")
def update_profile(
    profile_data: ProfileUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> ProfileUpdateResponse:
    try:
        updated_user = update_my_profile(
            db=db,
            current_user=current_user,
            profile_data=profile_data,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    return ProfileUpdateResponse(
        message="Profile updated successfully.",
        user=ProfileResponse.model_validate(updated_user),
    )


@router.patch("/password")
def update_password(
    password_data: ChangePasswordRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> ChangePasswordResponse:
    try:
        change_my_password(
            db=db,
            current_user=current_user,
            password_data=password_data,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return ChangePasswordResponse(
        message="Password changed successfully.",
    )

@router.delete("")
def delete_account(
    delete_data: DeleteAccountRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> DeleteAccountResponse:
    try:
        delete_my_account(
            db=db,
            current_user=current_user,
            delete_data=delete_data,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return DeleteAccountResponse(
        message="Account deleted successfully.",
    )