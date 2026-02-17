from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from src.core.database import get_db_session
from src.models.refund_count import RefundCount


async def increment_refund_count(normalized_email: str) -> int:
    """
    Increment the refund count for a normalized email, with proper locking to prevent race conditions.
    """
    async with get_db_session() as db_session:
        # Use PostgreSQL's ON CONFLICT to handle potential race conditions
        stmt = """
        INSERT INTO refund_counts (normalized_email, refund_count, updated_at)
        VALUES (:email, 1, :updated_at)
        ON CONFLICT (normalized_email)
        DO UPDATE SET
            refund_count = refund_counts.refund_count + 1,
            updated_at = :updated_at
        RETURNING refund_count
        """

        result = await db_session.execute(
            stmt,
            {
                "email": normalized_email,
                "updated_at": func.now()
            }
        )

        new_count = result.first()[0]
        await db_session.commit()
        return new_count


async def get_refund_count(normalized_email: str) -> int:
    """
    Get the current refund count for a normalized email.
    """
    async with get_db_session() as db_session:
        stmt = select(RefundCount.refund_count).where(RefundCount.normalized_email == normalized_email)
        result = await db_session.execute(stmt)
        row = result.fetchone()
        return row[0] if row else 0


async def decrement_refund_count(normalized_email: str) -> int:
    """
    Decrement the refund count for a normalized email, with minimum 0.
    """
    async with get_db_session() as db_session:
        stmt = """
        UPDATE refund_counts
        SET
            refund_count = GREATEST(0, refund_count - 1),
            updated_at = :updated_at
        WHERE normalized_email = :email
        RETURNING refund_count
        """

        result = await db_session.execute(
            stmt,
            {
                "email": normalized_email,
                "updated_at": func.now()
            }
        )

        if not result.rowcount:
            # If no existing row, return 0 (already at minimum)
            return 0

        updated_count = result.first()[0]
        await db_session.commit()
        return updated_count