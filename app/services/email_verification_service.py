from datetime import datetime, timedelta, timezone
import secrets
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import hash_verification_code
from app.models.email_verification_code import EmailVerificationCode

def generate_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"

def create_email_verification_code(db: Session, user_id: int) -> str:
    plain_code = generate_verification_code()

    verification_code = EmailVerificationCode(
        user_id=user_id,
        code_hash=hash_verification_code(plain_code),
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=settings.verification_code_expire_minutes),
    )

    db.add(verification_code)
    db.commit()

    return plain_code

def get_latest_active_verification_code(
        db: Session,
        user_id: int,
    ) -> EmailVerificationCode| None:
    now = datetime.now(timezone.utc)

    statement = (
        select(EmailVerificationCode)
        .where(
            EmailVerificationCode.user_id == user_id,
            EmailVerificationCode.used_at.is_(None),
            EmailVerificationCode.expires_at > now,
        )
        .order_by(
        EmailVerificationCode.created_at.desc(),
        EmailVerificationCode.verification_id.desc(),
        )
        .limit(1)
    )

    return db.scalar(statement)