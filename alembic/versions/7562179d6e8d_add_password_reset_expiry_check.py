"""add password reset expiry check

Revision ID: 7562179d6e8d
Revises: 2bf54f983173
Create Date: 2026-05-17 13:33:37.512327

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "7562179d6e8d"
down_revision: Union[str, Sequence[str], None] = "2bf54f983173"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(
        "chk_password_reset_codes_expiry",
        "password_reset_codes",
        type_="check",
        if_exists=True,
    )

    op.create_check_constraint(
        "chk_password_reset_codes_expiry",
        "password_reset_codes",
        "expires_at > created_at",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "chk_password_reset_codes_expiry",
        "password_reset_codes",
        type_="check",
        if_exists=True,
    )