"""add refund processing features with enum support

Revision ID: a593e0896e9f
Revises: 9cb3ae0d1961
Create Date: 2026-02-17 22:33:12.453384

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a593e0896e9f'
down_revision: Union[str, Sequence[str], None] = '9cb3ae0d1961'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
