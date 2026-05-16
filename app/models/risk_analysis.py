from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


class RiskAnalysis(Base):
    __tablename__ = "risk_analysis"

    __table_args__ = (
        CheckConstraint(
            "risk_level IN ('low', 'medium', 'high')",
            name="chk_risk_analysis_level",
        ),
        CheckConstraint(
            "predicted_delay_days >= 0",
            name="chk_risk_analysis_predicted_delay",
        ),
    )

    risk_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    predicted_delay_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    recommendation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    project: Mapped["Project"] = relationship(
        back_populates="risk_analyses",
    )