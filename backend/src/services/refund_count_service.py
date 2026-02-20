from datetime import datetime
from sqlalchemy import select, update
from src.lib.database import get_db_context
from src.models.refund_count import RefundCount


async def increment_refund_count(normalized_email: str) -> int:
    """
    Increment the refund count for a normalized email.

    Uses an upsert pattern compatible with both PostgreSQL and SQLite for testability.
    """
    async with get_db_context() as db_session:
        # Check if row already exists
        stmt = select(RefundCount).where(RefundCount.normalized_email == normalized_email)
        result = await db_session.execute(stmt)
        record = result.scalar_one_or_none()

        if record is None:
            # Insert new record
            record = RefundCount(
                normalized_email=normalized_email,
                refund_count=1,
                updated_at=datetime.utcnow(),
            )
            db_session.add(record)
        else:
            # Increment existing record
            record.refund_count += 1
            record.updated_at = datetime.utcnow()

        await db_session.commit()
        return record.refund_count


async def get_refund_count(normalized_email: str) -> int:
    """
    Get the current refund count for a normalized email.
    """
    async with get_db_context() as db_session:
        stmt = select(RefundCount.refund_count).where(RefundCount.normalized_email == normalized_email)
        result = await db_session.execute(stmt)
        row = result.fetchone()
        return row[0] if row else 0


async def decrement_refund_count(normalized_email: str) -> int:
    """
    Decrement the refund count for a normalized email, with minimum 0.
    """
    async with get_db_context() as db_session:
        stmt = select(RefundCount).where(RefundCount.normalized_email == normalized_email)
        result = await db_session.execute(stmt)
        record = result.scalar_one_or_none()

        if record is None:
            # No existing row - already at 0
            return 0

        # Decrement but not below 0
        record.refund_count = max(0, record.refund_count - 1)
        record.updated_at = datetime.utcnow()
        await db_session.commit()
        return record.refund_count