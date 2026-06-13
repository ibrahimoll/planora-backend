import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.oauth_account import OAuthAccount
from app.models.user import User
from app.schemas.auth import SocialLoginRequest
from app.services.google_auth_service import GoogleUserInfo, verify_google_id_token
from app.services.profile_picture_service import build_default_profile_pic


def create_unusable_password_hash() -> str:
    random_secret = secrets.token_urlsafe(64)
    return hash_password(random_secret)


def login_with_google(db: Session, data: SocialLoginRequest) -> str:
    google_user: GoogleUserInfo = verify_google_id_token(data.id_token)

    oauth_account = db.scalar(
        select(OAuthAccount).where(
            OAuthAccount.provider == "google",
            OAuthAccount.provider_user_id == google_user.provider_user_id,
        )
    )

    if oauth_account is not None:
        user = oauth_account.user

        if not user.is_active:
            raise ValueError("Account is deactivated.")

        if not user.is_email_verified:
            user.is_email_verified = True
            db.commit()
            db.refresh(user)

        return create_access_token(user.user_id)

    existing_user = db.scalar(
        select(User).where(User.email == google_user.email)
    )

    if existing_user is not None:
        if not existing_user.is_active:
            raise ValueError("Account is deactivated.")

        existing_user.is_email_verified = True

        if existing_user.profile_pic is None:
            existing_user.profile_pic = build_default_profile_pic(
                existing_user.full_name
            )

        oauth_account = OAuthAccount(
            user_id=existing_user.user_id,
            provider="google",
            provider_user_id=google_user.provider_user_id,
            provider_email=google_user.email,
        )

        db.add(oauth_account)
        db.commit()
        db.refresh(existing_user)

        return create_access_token(existing_user.user_id)

    full_name = (
        google_user.full_name
        or data.full_name
        or google_user.email.split("@")[0]
    )

    username = data.username or generate_unique_username(db, google_user.email)

    existing_username = db.scalar(
        select(User).where(User.username == username)
    )

    if existing_username is not None:
        raise ValueError("Username is already taken.")

    user = User(
        username=username,
        email=google_user.email,
        password_hash=create_unusable_password_hash(),
        full_name=full_name,
        role="user",
        is_active=True,
        is_email_verified=True,
        profile_pic=build_default_profile_pic(full_name),
    )

    db.add(user)
    db.flush()

    oauth_account = OAuthAccount(
        user_id=user.user_id,
        provider="google",
        provider_user_id=google_user.provider_user_id,
        provider_email=google_user.email,
    )

    db.add(oauth_account)
    db.commit()
    db.refresh(user)

    return create_access_token(user.user_id)


def generate_unique_username(db: Session, email: str) -> str:
    base = email.split("@")[0].lower()
    base = "".join(ch for ch in base if ch.isalnum() or ch == "_")

    if len(base) < 3:
        base = f"user{secrets.randbelow(9999):04d}"

    candidate = base[:50]
    suffix = 1

    while db.scalar(select(User).where(User.username == candidate)) is not None:
        suffix_text = str(suffix)
        max_base_length = 50 - len(suffix_text) - 1
        candidate = f"{base[:max_base_length]}_{suffix_text}"
        suffix += 1

    return candidate