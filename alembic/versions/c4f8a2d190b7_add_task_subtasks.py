"""add task subtasks

Revision ID: c4f8a2d190b7
Revises: 4cbea5887651
Create Date: 2026-06-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "c4f8a2d190b7"
down_revision = "4cbea5887651"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subtasks",
        sa.Column("subtask_id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "task_id",
            sa.BigInteger(),
            sa.ForeignKey("tasks.task_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.BigInteger(),
            sa.ForeignKey("users.user_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column(
            "is_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "((is_completed AND completed_at IS NOT NULL) OR "
            "(NOT is_completed AND completed_at IS NULL))",
            name="chk_subtasks_completed_at_logic",
        ),
    )
    op.create_index("idx_subtasks_task_id", "subtasks", ["task_id"])
    op.create_index("idx_subtasks_created_by", "subtasks", ["created_by"])


def downgrade() -> None:
    op.drop_index("idx_subtasks_created_by", table_name="subtasks")
    op.drop_index("idx_subtasks_task_id", table_name="subtasks")
    op.drop_table("subtasks")
