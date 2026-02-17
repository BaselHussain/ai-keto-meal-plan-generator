"""Add updated_at field to quiz_responses table

Revision ID: 002_add_quiz_response_updated_at
Revises: 001_initial_schema
Create Date: 2026-01-27 12:00:00.000000

This migration adds the updated_at field to quiz_responses table to support
incremental quiz progress saves (T113) for authenticated users.

Changes:
- Add updated_at TIMESTAMP column (nullable, defaults to created_at value)
- Used for tracking last progress save timestamp
- Enables cross-device sync functionality

Usage:
    # Apply migration
    alembic upgrade head

    # Rollback migration
    alembic downgrade -1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = '002_add_quiz_response_updated_at'
down_revision = '866507e290ed'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add updated_at column to quiz_responses table.

    The column defaults to created_at value for existing rows,
    and will auto-update on row modifications.
    """
    # Add updated_at column (nullable, no server default - will be set via UPDATE)
    op.add_column(
        'quiz_responses',
        sa.Column(
            'updated_at',
            sa.DateTime(),
            nullable=True,
            comment='Last progress save timestamp (for T113 incremental saves)'
        )
    )

    # Update existing rows to have updated_at = created_at
    op.execute(
        """
        UPDATE quiz_responses
        SET updated_at = created_at
        WHERE updated_at IS NULL
        """
    )


def downgrade() -> None:
    """
    Remove updated_at column from quiz_responses table.

    WARNING: This will delete all progress save timestamps.
    """
    op.drop_column('quiz_responses', 'updated_at')
