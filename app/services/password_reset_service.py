import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.password_reset_code import PasswordResetCode


def generate_password_reset_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_password_reset_code(code: str) -> str:
    return hmac.new(
        settings.password_reset_code_secret.encode(),
        code.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_password_reset_code(code: str, stored_code_hash: str) -> bool:
    submitted_code_hash = hash_password_reset_code(code)

    return hmac.compare_digest(
        submitted_code_hash,
        stored_code_hash,
    )


def create_password_reset_code(
    db: Session,
    user_id: int,
) -> str:
    raw_code = generate_password_reset_code()

    reset_code = PasswordResetCode(
        user_id=user_id,
        code_hash=hash_password_reset_code(raw_code),
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=settings.password_reset_code_expire_minutes),
    )

    db.add(reset_code)
    db.flush()

    return raw_code


# Backward-compatible aliases while callers are migrated away from reset-link terminology.
generate_password_reset_token = generate_password_reset_code
hash_password_reset_token = hash_password_reset_code
verify_password_reset_token = verify_password_reset_code
create_password_reset_token = create_password_reset_code


def get_latest_active_password_reset_code(
    db: Session,
    user_id: int,
) -> PasswordResetCode | None:
    return db.scalar(
        select(PasswordResetCode)
        .where(
            PasswordResetCode.user_id == user_id,
            PasswordResetCode.used_at.is_(None),
            PasswordResetCode.expires_at > datetime.now(timezone.utc),
        )
        .order_by(
            PasswordResetCode.created_at.desc(),
            PasswordResetCode.reset_code_id.desc(),
        )
        .limit(1)
    )


def mark_unused_password_reset_codes_as_used(
    db: Session,
    user_id: int,
) -> None:
    active_codes = db.scalars(
        select(PasswordResetCode).where(
            PasswordResetCode.user_id == user_id,
            PasswordResetCode.used_at.is_(None),
        )
    ).all()

    now = datetime.now(timezone.utc)

    for code in active_codes:
        code.used_at = now
