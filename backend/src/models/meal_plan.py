"""
MealPlan Model

Stores meal plan metadata, payment reference, PDF storage path, and food preference summary.

Schema Design:
- Unique payment_id constraint prevents duplicate meal plans per payment
- Email normalization prevents Gmail alias abuse (dots, plus signs)
- pdf_blob_path stores permanent blob path (signed URLs generated on-demand)
- JSONB preferences_summary for efficient food preference querying
- Status enum tracks meal plan lifecycle (processing, completed, failed, refunded)
- Refund tracking prevents abuse (max 3 refunds per normalized email)

Indexes:
- idx_mealplan_payment_id: Fast lookups for payment verification (UNIQUE)
- idx_mealplan_normalized_email: Email-based queries for refund abuse prevention
- idx_mealplan_created_at: Efficient cleanup job queries (90-day retention)

Data Retention Policy:
- All meal plans deleted 90 days after created_at
- Automatic cleanup via scheduled cleanup job (see T092-T095)

Status Lifecycle:
- processing: Initial state when payment webhook triggers generation
- completed: PDF generated successfully and blob URL stored
- failed: Generation failed (AI error, blob storage error, etc.)
- refunded: Payment refunded (triggers PDF access revocation)
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING

from sqlalchemy import String, Integer, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.lib.database import Base

if TYPE_CHECKING:
    from src.models.payment_transaction import PaymentTransaction


class MealPlan(Base):
    """
    Meal plan entity storing generated 30-day keto meal plans.

    Each meal plan is tied to a unique Paddle payment and contains:
    - PDF storage reference for the generated meal plan
    - Food preference summary derived from quiz responses
    - AI model metadata for traceability
    - Delivery and refund tracking

    Attributes:
        id: Unique meal plan identifier (UUID as string)
        payment_id: Paddle payment transaction ID (unique)
        email: Original email address from payment/quiz
        normalized_email: Normalized email for abuse prevention
        pdf_blob_path: Permanent Vercel Blob storage path (not time-limited URL)
        calorie_target: Daily calorie target from quiz calculation
        preferences_summary: Derived food preferences (JSONB structure below)
        ai_model: AI model used for generation (gpt-4o, gemini-1.5-pro)
        status: Lifecycle state (processing, completed, failed, refunded)
        refund_count: Number of refunds for this email (abuse prevention)
        created_at: Meal plan creation timestamp (UTC)
        email_sent_at: Email delivery timestamp (NULL if not yet sent)

    Preferences Summary JSONB Structure:
        {
            "excluded_foods": ["beef", "pork", "lamb", "chickpeas", "lentils"],
            "preferred_proteins": ["chicken", "turkey", "salmon", "tuna", "shrimp"],
            "dietary_restrictions": "No dairy from cows, goat dairy OK. Prefer coconut-based alternatives."
        }

    Status Enum Values:
        - processing: PDF generation in progress
        - completed: PDF successfully generated and stored
        - failed: Generation failed (retryable error)
        - refunded: Payment refunded (PDF access revoked)

    Retention Policy:
        - Deleted 90 days after created_at via scheduled cleanup job
        - References in QuizResponse.payment_id remain for audit trail
    """

    __tablename__ = "meal_plans"

    # Primary key (UUID as string)
    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique meal plan identifier (UUID)"
    )

    # Payment tracking (unique constraint)
    payment_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        doc="Paddle payment transaction ID (unique per meal plan)"
    )

    # Email fields
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Original email address from payment/quiz"
    )

    normalized_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Normalized email for refund abuse prevention"
    )

    # PDF storage reference (permanent path, not time-limited URL)
    pdf_blob_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Permanent Vercel Blob storage path (signed URLs generated on-demand)"
    )

    # Calorie and preferences
    calorie_target: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Daily calorie target from quiz calculation (Mifflin-St Jeor)"
    )

    preferences_summary: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        doc="Derived food preferences (excluded_foods, preferred_proteins, dietary_restrictions)"
    )

    # AI metadata
    ai_model: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="AI model used for generation (gpt-4o, gemini-1.5-pro)"
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="processing",
        doc="Lifecycle state (processing, completed, failed, refunded)"
    )

    # Refund abuse prevention
    refund_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of refunds for this normalized email (abuse prevention)"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="Meal plan creation timestamp (UTC)"
    )

    email_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="Email delivery timestamp (NULL if not yet sent)"
    )

    # Relationship to PaymentTransaction (one-to-one)
    payment_transaction: Mapped[Optional["PaymentTransaction"]] = relationship(
        "PaymentTransaction",
        back_populates="meal_plan",
        lazy="selectin",
        doc="Related payment transaction (NULL if meal plan created before payment tracking)"
    )

    # Table-level constraints and indexes
    __table_args__ = (
        Index("idx_mealplan_payment_id", "payment_id", unique=True),
        Index("idx_mealplan_normalized_email", "normalized_email"),
        Index("idx_mealplan_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<MealPlan(id={self.id}, payment_id={self.payment_id}, "
            f"email={self.email}, status={self.status}, "
            f"ai_model={self.ai_model}, created_at={self.created_at})>"
        )
