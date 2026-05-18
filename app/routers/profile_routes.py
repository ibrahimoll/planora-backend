from mimetypes import guess_type
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
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
    PROFILE_PICTURE_URL_PREFIX,
    change_my_password,
    delete_my_account,
    get_profile_picture_local_path,
    update_my_profile,
    upload_my_profile_picture,
)

router = APIRouter(
    prefix="/profile",
    tags=["Profile"],
)

DBSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_verified_user)]
UploadedProfilePicture = Annotated[UploadFile, File(...)]

PROFILE_PICTURE_NOT_FOUND = "Profile picture not found"


@router.get("/picture/{stored_file_name}", include_in_schema=False)
def get_profile_picture(stored_file_name: str):
    file_url = f"{PROFILE_PICTURE_URL_PREFIX}{stored_file_name}"
    file_path = get_profile_picture_local_path(file_url=file_url)

    if file_path is None or not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=PROFILE_PICTURE_NOT_FOUND,
        )

    media_type = guess_type(file_path.name)[0] or "application/octet-stream"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=file_path.name,
    )


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


@router.post("/picture")
def upload_profile_picture(
    db: DBSession,
    current_user: CurrentUser,
    file: UploadedProfilePicture,
) -> ProfileUpdateResponse:
    updated_user = upload_my_profile_picture(
        db=db,
        current_user=current_user,
        file=file,
    )

    return ProfileUpdateResponse(
        message="Profile picture updated successfully.",
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