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


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def _existing_indexes(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _create_index_if_missing(
    index_name: str,
    table_name: str,
    columns: list[str],
) -> None:
    existing_indexes = _existing_indexes(table_name)
    if index_name not in existing_indexes:
        op.create_index(index_name, table_name, columns)


def upgrade() -> None:
    # Some deployed databases already have this table from an earlier schema sync,
    # but the Alembic version row was never advanced. Make this migration safe so
    # `alembic upgrade head` can continue instead of failing with DuplicateTable.
    if not _table_exists("report_exports"):
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

    _create_index_if_missing(
        "idx_report_exports_project_id",
        "report_exports",
        ["project_id"],
    )
    _create_index_if_missing(
        "idx_report_exports_exported_by",
        "report_exports",
        ["exported_by"],
    )
    _create_index_if_missing(
        "idx_report_exports_created_at",
        "report_exports",
        ["created_at"],
    )
    _create_index_if_missing(
        "idx_report_exports_report_type",
        "report_exports",
        ["report_type"],
    )
    _create_index_if_missing(
        "idx_report_exports_export_format",
        "report_exports",
        ["export_format"],
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_report_exports_export_format")
    op.execute("DROP INDEX IF EXISTS idx_report_exports_report_type")
    op.execute("DROP INDEX IF EXISTS idx_report_exports_created_at")
    op.execute("DROP INDEX IF EXISTS idx_report_exports_exported_by")
    op.execute("DROP INDEX IF EXISTS idx_report_exports_project_id")
    op.execute("DROP TABLE IF EXISTS report_exports")
