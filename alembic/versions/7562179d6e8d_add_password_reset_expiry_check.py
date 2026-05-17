"""add password reset expiry check

Revision ID: 7562179d6e8d
Revises: 2bf54f983173
Create Date: 2026-05-17 13:33:37.512327

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7562179d6e8d'
down_revision: Union[str, Sequence[str], None] = '2bf54f983173'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
