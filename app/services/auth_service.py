from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
    verify_verification_code,
)
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    RegisterRequest,
    ResendVerificationCodeRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from app.services.email_service import (
    send_password_reset_email,
    send_verification_email,
)
from app.services.email_verification_service import (
    create_email_verification_code,
    get_latest_active_verification_code,
)
from app.services.password_reset_service import (
    create_password_reset_code,
    get_latest_active_password_reset_code,
    mark_unused_password_reset_codes_as_used,
    verify_password_reset_code,
)

INVALID_VERIFICATION_CODE_MESSAGE = "Invalid verification code."
INVALID_PASSWORD_RESET_CODE_MESSAGE = "Invalid password reset code."


def register_user(db: Session, data: RegisterRequest) -> User:
    normalized_email = data.email.lower()

    existing_username = db.scalar(
        select(User).where(User.username == data.username)
    )
    if existing_username is not None:
        raise ValueError("Username is already taken.")

    existing_email = db.scalar(
        select(User).where(User.email == normalized_email)
    )
    if existing_email is not None:
        raise ValueError("Email is already registered.")

    user = User(
        username=data.username,
        email=normalized_email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role="user",
        is_active=True,
        is_email_verified=False,
    )

    db.add(user)
    db.flush()

    plain_code = create_email_verification_code(db, user.user_id)

    try:
        send_verification_email(
            recipient_email=user.email,
            code=plain_code,
        )
    except Exception:
        db.rollback()
        raise

    db.commit()
    db.refresh(user)

    return user


def verify_email(db: Session, data: VerifyEmailRequest) -> User:
    normalized_email = data.email.lower()

    user = db.scalar(
        select(User).where(User.email == normalized_email)
    )
    if user is None:
        raise ValueError(INVALID_VERIFICATION_CODE_MESSAGE)

    if user.is_email_verified:
        raise ValueError("Email is already verified.")

    latest_code = get_latest_active_verification_code(
        db,
        user.user_id,
    )

    if latest_code is None:
        raise ValueError(INVALID_VERIFICATION_CODE_MESSAGE)

    if not verify_verification_code(data.code, latest_code.code_hash):
        raise ValueError(INVALID_VERIFICATION_CODE_MESSAGE)

    latest_code.used_at = datetime.now(timezone.utc)
    user.is_email_verified = True

    db.commit()
    db.refresh(user)

    return user


def resend_verification_code(
    db: Session,
    data: ResendVerificationCodeRequest,
) -> None:
    normalized_email = data.email.lower()

    user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    if user is None:
        return

    if user.is_email_verified:
        return

    plain_code = create_email_verification_code(db, user.user_id)

    try:
        send_verification_email(
            recipient_email=user.email,
            code=plain_code,
        )
    except Exception:
        db.rollback()
        raise

    db.commit()


def request_password_reset(
    db: Session,
    data: ForgotPasswordRequest,
) -> None:
    normalized_email = data.email.lower()

    user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    if user is None or not user.is_active:
        return

    mark_unused_password_reset_codes_as_used(
        db,
        user.user_id,
    )

    plain_code = create_password_reset_code(
        db,
        user.user_id,
    )

    try:
        send_password_reset_email(
            recipient_email=user.email,
            code=plain_code,
        )
    except Exception:
        db.rollback()
        raise

    db.commit()


def reset_password(
    db: Session,
    data: ResetPasswordRequest,
) -> User:
    normalized_email = data.email.lower()

    user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    if user is None:
        raise ValueError(INVALID_PASSWORD_RESET_CODE_MESSAGE)

    if not user.is_active:
        raise ValueError("Account is deactivated.")

    latest_code = get_latest_active_password_reset_code(
        db,
        user.user_id,
    )

    if latest_code is None:
        raise ValueError(INVALID_PASSWORD_RESET_CODE_MESSAGE)

    if not verify_password_reset_code(
        data.code,
        latest_code.code_hash,
    ):
        raise ValueError(INVALID_PASSWORD_RESET_CODE_MESSAGE)

    latest_code.used_at = datetime.now(timezone.utc)
    user.password_hash = hash_password(data.new_password)

    db.commit()
    db.refresh(user)

    return user


def login_user(db: Session, identifier: str, password: str) -> str:
    identifier = identifier.strip()

    if "@" in identifier:
        user = db.scalar(
            select(User).where(User.email == identifier.lower())
        )
    else:
        user = db.scalar(
            select(User).where(User.username == identifier)
        )

    if user is None or not verify_password(password, user.password_hash):
        raise ValueError("Invalid username/email or password.")

    if not user.is_email_verified:
        raise ValueError("Email is not verified.")

    if not user.is_active:
        raise ValueError("Account is deactivated.")

    return create_access_token(user.user_id)
