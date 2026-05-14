from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.profile_schema import ChangePasswordRequest, ProfileUpdate
from app.schemas.profile_schema import ChangePasswordRequest, ProfileUpdate
from app.schemas.profile_schema import DeleteAccountRequest
from app.schemas.profile_schema import (
    ChangePasswordRequest,
    DeleteAccountRequest,
    ProfileUpdate,
)

DELETE_ACCOUNT_CONFIRMATION_TEXT = "DELETE MY ACCOUNT"

def update_my_profile(
        db: Session,
        current_user: User,
        profile_data: ProfileUpdate,
) -> User:
    if profile_data.username is not None:
        existing_user = db.scalar(
            select(User).where(
                User.username == profile_data.username,
                User.user_id != current_user.user_id,
            )
        )

        if existing_user is not None:
            raise ValueError("Username is already taken.")
        
        current_user.username = profile_data.username

    if profile_data.full_name is not None:
        current_user.full_name = profile_data.full_name

    if profile_data.profile_pic is not None:
        current_user.profile_pic = profile_data.profile_pic

    db.commit()
    db.refresh(current_user)

    return current_user

def change_my_password(
        db: Session,
        current_user: User,
        password_data: ChangePasswordRequest,
) -> None:
    if not verify_password(
        password_data.old_password,
        current_user.password_hash
    ):
        raise ValueError("Old password is incorrect.")
    
    if verify_password(
        password_data.new_password,
        current_user.password_hash
    ):
        raise ValueError("New password must be different from the old password.")
    
    current_user.password_hash = hash_password(password_data.new_password)

    db.commit()

def delete_my_account(
        db: Session,
        current_user: User,
        delete_data: DeleteAccountRequest,
) -> None:
    if delete_data.confirmation_text != DELETE_ACCOUNT_CONFIRMATION_TEXT:
        raise ValueError("Invalid account deletion confirmation text.")
    
    current_user.is_active = False

    db.commit()