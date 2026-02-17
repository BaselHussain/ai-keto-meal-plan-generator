"""add payment status enum support and optimize refund processing

Revision ID: 9cb3ae0d1961
Revises: 002_add_quiz_response_updated_at
Create Date: 2026-02-17 22:29:30.485340

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9cb3ae0d1961'
down_revision: Union[str, Sequence[str], None] = '002_add_quiz_response_updated_at'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the payment_status_enum type if it doesn't exist
    op.execute("CREATE TYPE payment_status_enum AS ENUM ('succeeded', 'refunded', 'chargeback');")

    # Create the issue_type_enum type if it doesn't exist
    op.execute("CREATE TYPE issue_type_enum AS ENUM ('missing_quiz_data', 'ai_validation_failed', 'email_delivery_failed', 'manual_refund_required');")

    # Update payment_status column in payment_transactions table
    with op.batch_alter_table('payment_transactions', recreate='always') as batch_op:
        batch_op.alter_column(
            'payment_status',
            existing_type=sa.String(50),
            type_=sa.Enum('succeeded', 'refunded', 'chargeback', name='payment_status_enum'),
            existing_nullable=False
        )

    # Update issue_type column in manual_resolution table
    with op.batch_alter_table('manual_resolution', recreate='always') as batch_op:
        batch_op.alter_column(
            'issue_type',
            existing_type=sa.String(50),
            type_=sa.Enum('missing_quiz_data', 'ai_validation_failed', 'email_delivery_failed', 'manual_refund_required', name='issue_type_enum'),
            existing_nullable=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Roll back the issue_type column to string in manual_resolution table
    with op.batch_alter_table('manual_resolution', recreate='always') as batch_op:
        batch_op.alter_column(
            'issue_type',
            existing_type=sa.Enum('missing_quiz_data', 'ai_validation_failed', 'email_delivery_failed', 'manual_refund_required', name='issue_type_enum'),
            type_=sa.String(50),
            existing_nullable=False
        )

    # Roll back the payment_status column to string in payment_transactions table
    with op.batch_alter_table('payment_transactions', recreate='always') as batch_op:
        batch_op.alter_column(
            'payment_status',
            existing_type=sa.Enum('succeeded', 'refunded', 'chargeback', name='payment_status_enum'),
            type_=sa.String(50),
            existing_nullable=False
        )

    # Drop the enum types
    op.execute("DROP TYPE issue_type_enum;")
    op.execute("DROP TYPE payment_status_enum;")
