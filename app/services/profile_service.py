from pathlib import Path
import uuid

from fastapi import HTTPException, UploadFile
from fastapi import status as http_status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.profile_schema import (
    ChangePasswordRequest,
    DeleteAccountRequest,
    ProfileUpdate,
)

DELETE_ACCOUNT_CONFIRMATION_TEXT = "DELETE MY ACCOUNT"

BASE_DIR = Path(__file__).resolve().parents[2]
PROFILE_PICTURE_UPLOAD_DIR = BASE_DIR / "uploads" / "profile_pictures"
PROFILE_PICTURE_URL_PREFIX = "/profile/picture/"
MAX_PROFILE_PICTURE_SIZE_BYTES = 3 * 1024 * 1024
UPLOAD_CHUNK_SIZE_BYTES = 1024 * 1024

ALLOWED_PROFILE_PICTURE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}

ALLOWED_PROFILE_PICTURE_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
}


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
        current_user.profile_pic = profile_data.profile_pic or None

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
        current_user.password_hash,
    ):
        raise ValueError("Old password is incorrect.")

    if verify_password(
        password_data.new_password,
        current_user.password_hash,
    ):
        raise ValueError("New password must be different from the old password.")

    current_user.password_hash = hash_password(password_data.new_password)

    db.commit()


def delete_my_account(
    db: Session,
    current_user: User,
    delete_data: DeleteAccountRequest,
) -> None:
    if not verify_password(
        delete_data.current_password,
        current_user.password_hash,
    ):
        raise ValueError("Current password is incorrect.")

    if delete_data.confirmation_text != DELETE_ACCOUNT_CONFIRMATION_TEXT:
        raise ValueError("Invalid account deletion confirmation text.")

    current_user.is_active = False

    db.commit()


def clean_profile_picture_file_name(file_name: str | None) -> str:
    original_name = (file_name or "").replace("\\", "/").split("/")[-1].strip()

    if not original_name:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Profile picture file name is required.",
        )

    if len(original_name) > 255:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Profile picture file name must be 255 characters or less.",
        )

    return original_name


def validate_profile_picture(file: UploadFile) -> tuple[str, str]:
    original_name = clean_profile_picture_file_name(file.filename)
    suffix = Path(original_name).suffix.lower()

    if suffix not in ALLOWED_PROFILE_PICTURE_EXTENSIONS:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Profile picture must be PNG, JPG, JPEG, or WEBP.",
        )

    if file.content_type not in ALLOWED_PROFILE_PICTURE_CONTENT_TYPES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Profile picture content type is not allowed.",
        )

    return original_name, suffix


def save_profile_picture_file(file: UploadFile) -> str:
    _, suffix = validate_profile_picture(file=file)

    PROFILE_PICTURE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    stored_file_name = f"{uuid.uuid4().hex}{suffix}"
    storage_path = PROFILE_PICTURE_UPLOAD_DIR / stored_file_name

    bytes_written = 0

    try:
        with storage_path.open("xb") as output_file:
            while chunk := file.file.read(UPLOAD_CHUNK_SIZE_BYTES):
                bytes_written += len(chunk)

                if bytes_written > MAX_PROFILE_PICTURE_SIZE_BYTES:
                    raise HTTPException(
                        status_code=http_status.HTTP_400_BAD_REQUEST,
                        detail="Profile picture must be 3MB or less.",
                    )

                output_file.write(chunk)
    except Exception:
        storage_path.unlink(missing_ok=True)
        raise

    if bytes_written == 0:
        storage_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Profile picture cannot be empty.",
        )

    return f"{PROFILE_PICTURE_URL_PREFIX}{stored_file_name}"


def get_profile_picture_stored_file_name(file_url: str) -> str | None:
    if not file_url.startswith(PROFILE_PICTURE_URL_PREFIX):
        return None

    stored_file_name = file_url.replace(PROFILE_PICTURE_URL_PREFIX, "", 1)

    if not stored_file_name or stored_file_name != Path(stored_file_name).name:
        return None

    return stored_file_name


def get_profile_picture_local_path(file_url: str) -> Path | None:
    stored_file_name = get_profile_picture_stored_file_name(file_url)

    if stored_file_name is None:
        return None

    upload_dir = PROFILE_PICTURE_UPLOAD_DIR.resolve()
    file_path = (PROFILE_PICTURE_UPLOAD_DIR / stored_file_name).resolve()

    try:
        file_path.relative_to(upload_dir)
    except ValueError:
        return None

    return file_path


def delete_profile_picture_file(file_url: str | None) -> None:
    if not file_url:
        return

    file_path = get_profile_picture_local_path(file_url=file_url)

    if file_path is not None and file_path.exists() and file_path.is_file():
        file_path.unlink()


def upload_my_profile_picture(
    db: Session,
    current_user: User,
    file: UploadFile,
) -> User:
    old_profile_pic = current_user.profile_pic
    new_profile_pic = save_profile_picture_file(file=file)

    try:
        current_user.profile_pic = new_profile_pic
        db.commit()
        db.refresh(current_user)
    except Exception:
        db.rollback()
        delete_profile_picture_file(new_profile_pic)
        raise

    if old_profile_pic and old_profile_pic != new_profile_pic:
        delete_profile_picture_file(old_profile_pic)

    return current_user