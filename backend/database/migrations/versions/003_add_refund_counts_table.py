"""Add refund_counts table for tracking refund abuse

Revision ID: 003_add_refund_counts_table
Revises: 002_add_quiz_response_updated_at
Create Date: 2026-02-17 10:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '003_add_refund_counts_table'
down_revision = '002_add_quiz_response_updated_at'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('refund_counts',
        sa.Column('normalized_email', sa.String(), nullable=False),
        sa.Column('refund_count', sa.Integer(), nullable=False, default=0),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                 server_default=sa.text('now()'), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('normalized_email'),
        sa.Index('ix_refund_counts_normalized_email', 'normalized_email')
    )


def downgrade():
    op.drop_table('refund_counts')