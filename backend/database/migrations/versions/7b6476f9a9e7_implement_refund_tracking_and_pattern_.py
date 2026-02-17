"""implement refund tracking and pattern detection

Revision ID: 7b6476f9a9e7
Revises: a593e0896e9f
Create Date: 2026-02-17 22:35:30.601177

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b6476f9a9e7'
down_revision: Union[str, Sequence[str], None] = '002_add_quiz_response_updated_at'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create payment_status_enum type with the required values
    op.execute("CREATE TYPE payment_status_enum AS ENUM ('succeeded', 'refunded', 'chargeback');")

    # Create issue_type_enum type with the required values
    op.execute("CREATE TYPE issue_type_enum AS ENUM ('missing_quiz_data', 'ai_validation_failed', 'email_delivery_failed', 'manual_refund_required');")

    # Update any invalid values to 'succeeded' in payment_transactions and change type
    op.execute("""
        UPDATE payment_transactions
        SET payment_status = 'succeeded'
        WHERE payment_status NOT IN ('succeeded', 'refunded', 'chargeback')
    """)

    op.execute("""
        ALTER TABLE payment_transactions
        ALTER COLUMN payment_status TYPE payment_status_enum
        USING payment_status::payment_status_enum;
    """)

    # Update any invalid values and change issue_type column type in manual_resolution
    op.execute("""
        UPDATE manual_resolution
        SET issue_type = 'missing_quiz_data'
        WHERE issue_type NOT IN ('missing_quiz_data', 'ai_validation_failed', 'email_delivery_failed', 'manual_refund_required')
    """)

    op.execute("""
        ALTER TABLE manual_resolution
        ALTER COLUMN issue_type TYPE issue_type_enum
        USING issue_type::issue_type_enum;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Change payment_status column back to string
    op.execute("""
        ALTER TABLE payment_transactions
        ALTER COLUMN payment_status TYPE VARCHAR(50)
        USING payment_status::text;
    """)

    # Change issue_type column back to string
    op.execute("""
        ALTER TABLE manual_resolution
        ALTER COLUMN issue_type TYPE VARCHAR(50)
        USING issue_type::text;
    """)

    # Drop the enum types
    op.execute("DROP TYPE issue_type_enum;")
    op.execute("DROP TYPE payment_status_enum;")
