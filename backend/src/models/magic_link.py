"""
MagicLinkToken Model

Stores one-time authentication tokens for passwordless login via email.

Schema Design:
- Tokens are hashed using SHA256 before storage (never store plaintext tokens)
- Email normalization prevents Gmail alias abuse (dots, plus signs)
- Single-use enforcement via used_at timestamp
- 24-hour expiration window (expires_at = created_at + 24h)
- IP tracking for security audit trail (generation_ip, usage_ip)

Indexes:
- idx_magic_token_hash: Unique constraint on token_hash (fast lookups, single-use)
- idx_magic_expires_at: Index on expires_at (cleanup job queries)
- idx_magic_normalized_email: Index on normalized_email (user lookup queries)

Data Retention:
- 24 hours after creation (cleanup job removes expired tokens)
- Used tokens can be cleaned up immediately after use (optional optimization)
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.lib.database import Base


class MagicLinkToken(Base):
    """
    One-time authentication token for passwordless email login.

    Tokens are hashed using SHA256 before storage to prevent database compromise
    from revealing valid authentication tokens. Single-use enforcement prevents
    replay attacks. IP tracking provides security audit trail.

    Attributes:
        id: Unique token identifier (UUID as string)
        token_hash: SHA256 hash of the plaintext token (UNIQUE, NOT NULL)
        email: Original email address (for communications)
        normalized_email: Normalized email for lookups (prevents Gmail aliases)
        created_at: Token creation timestamp (UTC)
        expires_at: Token expiration timestamp (created_at + 24h, indexed for cleanup)
        used_at: Token usage timestamp (NULL = unused, NOT NULL = used/invalidated)
        generation_ip: IP address that requested the token (IPv4/IPv6)
        usage_ip: IP address that consumed the token (IPv4/IPv6)
    """

    __tablename__ = "magic_link_tokens"

    # Primary key (UUID as string)
    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique token identifier (UUID)"
    )

    # Token hash (SHA256, unique constraint)
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        doc="SHA256 hash of plaintext token (32 bytes = 64 hex chars)"
    )

    # Email fields
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Original email address (for communications)"
    )

    normalized_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Normalized email for lookups (prevents Gmail alias abuse)"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="Token creation timestamp (UTC)"
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        doc="Token expiration timestamp (created_at + 24h, indexed for cleanup)"
    )

    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="Token usage timestamp (NULL = unused, NOT NULL = used/invalidated)"
    )

    # IP tracking for security audit
    generation_ip: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        doc="IP address that requested the token (IPv4=15 chars, IPv6=45 chars)"
    )

    usage_ip: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        doc="IP address that consumed the token (IPv4=15 chars, IPv6=45 chars)"
    )

    # Table-level constraints and indexes
    __table_args__ = (
        Index("idx_magic_token_hash", "token_hash", unique=True),
        Index("idx_magic_expires_at", "expires_at"),
        Index("idx_magic_normalized_email", "normalized_email"),
    )

    def __init__(self, **kwargs):
        """
        Initialize MagicLinkToken with automatic expires_at calculation.

        If expires_at is not provided, it will be automatically set to
        created_at + 24 hours.

        Args:
            **kwargs: Keyword arguments for model fields
        """
        # Set created_at if not provided
        if 'created_at' not in kwargs:
            kwargs['created_at'] = datetime.utcnow()

        # Auto-calculate expires_at if not provided
        if 'expires_at' not in kwargs:
            kwargs['expires_at'] = kwargs['created_at'] + timedelta(hours=24)

        super().__init__(**kwargs)

    def __repr__(self) -> str:
        """String representation for debugging."""
        status = "used" if self.used_at else "unused"
        return (
            f"<MagicLinkToken(id={self.id}, email={self.email}, "
            f"status={status}, expires_at={self.expires_at})>"
        )
