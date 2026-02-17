from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from src.lib.database import Base


class RefundCount(Base):
    """
    Track refund counts per normalized email for abuse prevention.

    This model maintains a count of how many refunds each user has received
    to implement refund abuse prevention policies. Users with 2+ refunds
    get purchase attempts flagged for manual review, and 3+ refunds result
    in 30-day account blocks.
    """
    __tablename__ = "refund_counts"

    normalized_email = Column(String, primary_key=True, index=True, nullable=False)
    refund_count = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<RefundCount(normalized_email='{self.normalized_email}', refund_count={self.refund_count})>"