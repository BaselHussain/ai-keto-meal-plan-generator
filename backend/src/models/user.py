"""
User Model

Stores optional user accounts for dashboard access and cross-device quiz sync.

Schema Design:
- Users can create accounts via password or magic link authentication
- Email normalization prevents Gmail alias abuse (dots, plus signs)
- Password hash is nullable (NULL for magic link-only accounts)
- Timestamps track account lifecycle for retention policies

Indexes:
- idx_user_email: Unique constraint on email (fast lookups, prevents duplicates)
- idx_user_normalized_email: Non-unique index for normalized email lookups

Relationships:
- quiz_responses: One-to-many relationship with QuizResponse (to be added)
- meal_plans: One-to-many relationship with MealPlan (to be added)

Data Retention:
- Indefinite retention until user deletion request or GDPR compliance
- Related data (quiz responses, meal plans) cascade on deletion
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.lib.database import Base


class User(Base):
    """
    User account for optional authentication and cross-device sync.

    Supports two authentication methods:
    1. Password-based: email + password_hash
    2. Magic link: email only (password_hash is NULL)

    Attributes:
        id: Unique user identifier (UUID as string)
        email: Original email address (for communications)
        normalized_email: Normalized email for lookups (prevents Gmail aliases)
        password_hash: Bcrypt hash of password (NULL for magic link accounts)
        created_at: Account creation timestamp (UTC)
        updated_at: Last update timestamp (UTC, auto-updated)
    """

    __tablename__ = "users"

    # Primary key (UUID as string)
    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique user identifier (UUID)"
    )

    # Email fields
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        doc="Original email address (for communications)"
    )

    normalized_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Normalized email for lookups (prevents Gmail alias abuse)"
    )

    # Authentication
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Bcrypt hash of password (NULL for magic link accounts)"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="Account creation timestamp (UTC)"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        doc="Last update timestamp (UTC, auto-updated)"
    )

    # Relationships
    quiz_responses: Mapped[list["QuizResponse"]] = relationship(
        "QuizResponse",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
        doc="Quiz responses associated with this user"
    )

    # Table-level constraints and indexes
    __table_args__ = (
        Index("idx_user_email", "email", unique=True),
        Index("idx_user_normalized_email", "normalized_email"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<User(id={self.id}, email={self.email}, created_at={self.created_at})>"
