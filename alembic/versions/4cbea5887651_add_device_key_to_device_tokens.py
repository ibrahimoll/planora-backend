"""add device key to device tokens

Revision ID: 4cbea5887651
Revises: 8b2c6d9f0a11
Create Date: 2026-05-23 21:11:18.074263

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4cbea5887651"
down_revision: Union[str, Sequence[str], None] = "8b2c6d9f0a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def _has_unique_constraint(table_name: str, constraint_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return constraint_name in {
        constraint["name"] for constraint in inspector.get_unique_constraints(table_name)
    }


def upgrade() -> None:
    if not _has_column("device_tokens", "device_key"):
        op.add_column(
            "device_tokens",
            sa.Column("device_key", sa.String(length=100), nullable=True),
        )

    if not _has_index("device_tokens", "ix_device_tokens_device_key"):
        op.create_index(
            "ix_device_tokens_device_key",
            "device_tokens",
            ["device_key"],
        )

    if not _has_unique_constraint("device_tokens", "uq_device_tokens_user_device_key"):
        op.create_unique_constraint(
            "uq_device_tokens_user_device_key",
            "device_tokens",
            ["user_id", "device_key"],
        )


def downgrade() -> None:
    if _has_unique_constraint("device_tokens", "uq_device_tokens_user_device_key"):
        op.drop_constraint(
            "uq_device_tokens_user_device_key",
            "device_tokens",
            type_="unique",
        )

    if _has_index("device_tokens", "ix_device_tokens_device_key"):
        op.drop_index("ix_device_tokens_device_key", table_name="device_tokens")

    if _has_column("device_tokens", "device_key"):
        op.drop_column("device_tokens", "device_key")
