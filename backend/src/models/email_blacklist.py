"""
EmailBlacklist Model

Prevents re-purchase by users with chargebacks (FR-P-009).

Schema Design:
- Normalized email prevents Gmail alias abuse (dots, plus signs)
- Auto-calculated expires_at (created_at + 90 days) for retention policy
- Reason field currently supports "chargeback" only
- Scheduled cleanup job removes expired entries

Indexes:
- idx_blacklist_normalized_email: Unique constraint on normalized_email (fast lookups)
- idx_blacklist_expires_at: Index on expires_at (for cleanup job efficiency)

Data Retention:
- 90 days from creation_at
- Auto-deleted via scheduled cleanup job checking expires_at
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.lib.database import Base


class EmailBlacklist(Base):
    """
    Email blacklist for preventing re-purchase after chargebacks.

    Stores normalized emails that are temporarily blocked from making purchases.
    Entries auto-expire after 90 days to comply with retention policies.

    Attributes:
        id: Unique blacklist entry identifier (UUID as string)
        normalized_email: Normalized email address (prevents Gmail aliases)
        reason: Reason for blacklisting (currently "chargeback" only)
        created_at: Blacklist creation timestamp (UTC)
        expires_at: Expiration timestamp (UTC, created_at + 90 days)
    """

    __tablename__ = "email_blacklist"

    # Primary key (UUID as string)
    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique blacklist entry identifier (UUID)"
    )

    # Normalized email (unique constraint)
    normalized_email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        doc="Normalized email address (prevents Gmail alias abuse)"
    )

    # Blacklist reason
    reason: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Reason for blacklisting (e.g., 'chargeback')"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="Blacklist creation timestamp (UTC)"
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
        doc="Expiration timestamp (UTC, created_at + 90 days)"
    )

    # Table-level constraints and indexes
    __table_args__ = (
        Index("idx_blacklist_normalized_email", "normalized_email", unique=True),
        Index("idx_blacklist_expires_at", "expires_at"),
    )

    def __init__(
        self,
        normalized_email: str,
        reason: str = "chargeback",
        id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
    ) -> None:
        """
        Initialize EmailBlacklist entry with auto-calculated expiration.

        Args:
            normalized_email: Normalized email address to blacklist
            reason: Reason for blacklisting (default: "chargeback")
            id: Optional UUID (auto-generated if not provided)
            created_at: Optional creation timestamp (default: UTC now)
            expires_at: Optional expiration timestamp (default: created_at + 90 days)
        """
        self.id = id or str(uuid.uuid4())
        self.normalized_email = normalized_email
        self.reason = reason
        self.created_at = created_at or datetime.utcnow()
        # Auto-calculate expires_at if not provided: created_at + 90 days
        self.expires_at = expires_at or (self.created_at + timedelta(days=90))

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<EmailBlacklist(id={self.id}, normalized_email={self.normalized_email}, "
            f"reason={self.reason}, expires_at={self.expires_at})>"
        )
