from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.report_export import ReportExport
    from app.models.user import User


class ReportRequest(Base):
    __tablename__ = "report_requests"

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'ready', 'rejected')",
            name="chk_report_requests_status",
        ),
    )

    report_request_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'pending'"), index=True)
    link_signature: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True)
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_export_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("report_exports.report_export_id", ondelete="SET NULL"), nullable=True, index=True)
    resolved_by_admin_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    project: Mapped["Project"] = relationship()
    requester: Mapped["User | None"] = relationship(foreign_keys=[requested_by_user_id])
    resolver: Mapped["User | None"] = relationship(foreign_keys=[resolved_by_admin_id])
    report_export: Mapped["ReportExport | None"] = relationship()
