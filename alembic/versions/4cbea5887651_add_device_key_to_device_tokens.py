"""add device key to device tokens

Revision ID: 4cbea5887651
Revises: 8b2c6d9f0a11
Create Date: 2026-05-23 21:11:18.074263

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4cbea5887651'
down_revision: Union[str, Sequence[str], None] = '8b2c6d9f0a11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "device_tokens",
        sa.Column("device_key", sa.String(length=100), nullable=True),
    )

    op.create_index(
        "ix_device_tokens_device_key",
        "device_tokens",
        ["device_key"],
    )

    op.create_unique_constraint(
        "uq_device_tokens_user_device_key",
        "device_tokens",
        ["user_id", "device_key"],
    )

def downgrade() -> None:
    op.drop_constraint(
        "uq_device_tokens_user_device_key",
        "device_tokens",
        type_="unique",
    )

    op.drop_index("ix_device_tokens_device_key", table_name="device_tokens")

    op.drop_column("device_tokens", "device_key")
