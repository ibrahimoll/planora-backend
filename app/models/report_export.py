from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class ReportExport(Base):
    __tablename__ = "report_exports"

    __table_args__ = (
        CheckConstraint(
            "report_type IN ('project')",
            name="chk_report_exports_report_type",
        ),
        CheckConstraint(
            "export_format IN ('json')",
            name="chk_report_exports_export_format",
        ),
    )

    report_export_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    exported_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    report_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'project'"),
        index=True,
    )

    export_format: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'json'"),
        index=True,
    )

    project_title_snapshot: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    project_status_snapshot: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    project_type_snapshot: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    task_count_snapshot: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    completion_percentage_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        server_default=text("0"),
    )

    exported_by_username_snapshot: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    exported_by_full_name_snapshot: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    project: Mapped["Project"] = relationship(
        back_populates="report_exports",
    )

    exporter: Mapped["User | None"] = relationship(
        back_populates="report_exports",
    )