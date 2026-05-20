"""add report export history

Revision ID: 8b2c6d9f0a11
Revises: 7562179d6e8d
Create Date: 2026-05-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "8b2c6d9f0a11"
down_revision = "7562179d6e8d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_exports",
        sa.Column("report_export_id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "project_id",
            sa.BigInteger(),
            sa.ForeignKey("projects.project_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exported_by",
            sa.BigInteger(),
            sa.ForeignKey("users.user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "report_type",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'project'"),
        ),
        sa.Column(
            "export_format",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'json'"),
        ),
        sa.Column("project_title_snapshot", sa.String(length=200), nullable=False),
        sa.Column("project_status_snapshot", sa.String(length=30), nullable=False),
        sa.Column("project_type_snapshot", sa.String(length=20), nullable=False),
        sa.Column(
            "task_count_snapshot",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "completion_percentage_snapshot",
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("exported_by_username_snapshot", sa.String(length=50), nullable=True),
        sa.Column("exported_by_full_name_snapshot", sa.String(length=150), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "report_type IN ('project')",
            name="chk_report_exports_report_type",
        ),
        sa.CheckConstraint(
            "export_format IN ('json')",
            name="chk_report_exports_export_format",
        ),
    )

    op.create_index(
        "idx_report_exports_project_id",
        "report_exports",
        ["project_id"],
    )
    op.create_index(
        "idx_report_exports_exported_by",
        "report_exports",
        ["exported_by"],
    )
    op.create_index(
        "idx_report_exports_created_at",
        "report_exports",
        ["created_at"],
    )
    op.create_index(
        "idx_report_exports_report_type",
        "report_exports",
        ["report_type"],
    )
    op.create_index(
        "idx_report_exports_export_format",
        "report_exports",
        ["export_format"],
    )


def downgrade() -> None:
    op.drop_index("idx_report_exports_export_format", table_name="report_exports")
    op.drop_index("idx_report_exports_report_type", table_name="report_exports")
    op.drop_index("idx_report_exports_created_at", table_name="report_exports")
    op.drop_index("idx_report_exports_exported_by", table_name="report_exports")
    op.drop_index("idx_report_exports_project_id", table_name="report_exports")
    op.drop_table("report_exports")