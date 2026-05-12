from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import(
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User

class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    __table_args__ = (
        CheckConstraint(
            "provider ='google'",
            name="chk_oauth_accounts_provider",
        ),
        UniqueConstraint(
            "provider",
            "provider_user_id",
            name="uq_oauth_accounts_provider_user",
        ),
    )

    oauth_account_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key= True,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable= False,
    )

    provider: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    provider_user_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    provider_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(
        back_populates="oauth_accounts",
    )