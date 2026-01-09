"""
PaymentTransaction Model

Stores payment transaction metadata for analytics, customer support, compliance, and fraud detection.

Schema Design:
- Unique payment_id constraint prevents duplicate transaction records
- Email normalization prevents Gmail alias abuse (dots, plus signs)
- meal_plan_id initially NULL, updated when meal plan generation completes
- DECIMAL(10,2) for precise financial amounts (prevents floating-point errors)
- payment_status tracks transaction lifecycle (succeeded, refunded, chargeback)
- Separate timestamps for Paddle event time vs webhook processing time

Indexes:
- idx_payment_transaction_id: Fast lookups by Paddle transaction ID (UNIQUE)
- idx_payment_normalized_email: Email-based fraud detection queries
- idx_payment_paddle_created_at: Analytics queries by payment date
- idx_payment_status: Refund and chargeback queries

Data Retention Policy:
- All payment transactions deleted 1 year after created_at
- Automatic cleanup via scheduled cleanup job (see T092-T095)

Payment Status Lifecycle:
- succeeded: Payment completed successfully (default)
- refunded: Full or partial refund issued
- chargeback: Customer disputed payment with their bank

Use Cases:
- Analytics: Revenue tracking by payment method, currency distribution, daily/monthly reports
- Customer Support: Quick payment lookup without Paddle API calls
- Fraud Detection: Multiple payment patterns, abuse prevention (FR-P-011)
- Compliance: Financial records for tax/accounting, chargeback dispute evidence

Security Notes:
- NEVER stores PCI-sensitive data (card numbers, CVV, expiration dates, billing addresses)
- Only stores safe transaction metadata provided by Paddle webhook
- Complies with PCI-DSS by not handling payment instrument data
"""

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, DateTime, Index, DECIMAL, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.lib.database import Base

if TYPE_CHECKING:
    from src.models.meal_plan import MealPlan


class PaymentTransaction(Base):
    """
    Payment transaction entity storing Paddle webhook payment metadata.

    Each payment transaction represents a successful payment event from Paddle and contains:
    - Paddle transaction metadata (payment_id, amount, currency, method)
    - Customer email (original and normalized for abuse prevention)
    - Payment status tracking (succeeded, refunded, chargeback)
    - Timestamps for both Paddle event and webhook processing
    - Optional link to generated meal plan (NULL until generation completes)

    Attributes:
        id: Unique payment transaction identifier (UUID as string)
        payment_id: Paddle payment transaction ID (unique)
        meal_plan_id: Optional FK to meal_plans.id (NULL until meal plan created)
        amount: Payment amount with 2 decimal precision (e.g., 29.99)
        currency: ISO 4217 currency code (USD, EUR, GBP)
        payment_method: Payment method used (card, apple_pay, google_pay, ideal, alipay, bank_transfer)
        payment_status: Transaction status (succeeded, refunded, chargeback)
        paddle_created_at: Payment timestamp from Paddle webhook (UTC)
        webhook_received_at: System timestamp when webhook was processed (UTC)
        customer_email: Original email address from Paddle payment
        normalized_email: Normalized email for abuse prevention (lowercase, dots/plus removed)
        created_at: Record creation timestamp (UTC)
        updated_at: Record update timestamp (UTC)

    Payment Method Values:
        - card: Credit/debit card payment
        - apple_pay: Apple Pay wallet
        - google_pay: Google Pay wallet
        - ideal: iDEAL bank transfer (Netherlands)
        - alipay: Alipay wallet (China)
        - bank_transfer: Direct bank transfer

    Payment Status Values:
        - succeeded: Payment completed successfully (default)
        - refunded: Full or partial refund issued
        - chargeback: Customer disputed payment with bank

    Retention Policy:
        - Deleted 1 year after created_at via scheduled cleanup job
        - Required for financial compliance and audit trails
    """

    __tablename__ = "payment_transactions"

    # Primary key (UUID as string)
    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique payment transaction identifier (UUID)"
    )

    # Paddle transaction tracking (unique constraint)
    payment_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        doc="Paddle payment transaction ID (unique per transaction)"
    )

    # Meal plan reference (nullable until generation completes)
    meal_plan_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("meal_plans.id"),
        nullable=True,
        doc="Foreign key to meal_plans.id (NULL until meal plan created)"
    )

    # Financial data (DECIMAL for precise amounts)
    amount: Mapped[float] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
        doc="Payment amount with 2 decimal precision (e.g., 29.99)"
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        doc="ISO 4217 currency code (USD, EUR, GBP)"
    )

    # Payment method and status
    payment_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Payment method type (card, apple_pay, google_pay, ideal, alipay, bank_transfer)"
    )

    payment_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="succeeded",
        doc="Transaction status (succeeded, refunded, chargeback)"
    )

    # Timestamps (Paddle event time vs webhook processing time)
    paddle_created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        doc="Payment timestamp from Paddle webhook (UTC)"
    )

    webhook_received_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="System timestamp when webhook was processed (UTC)"
    )

    # Email fields
    customer_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Original email address from Paddle payment"
    )

    normalized_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Normalized email for abuse prevention (lowercase, dots/plus removed)"
    )

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="Record creation timestamp (UTC)"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        doc="Record update timestamp (UTC)"
    )

    # Relationship to MealPlan (one-to-one)
    meal_plan: Mapped[Optional["MealPlan"]] = relationship(
        "MealPlan",
        back_populates="payment_transaction",
        lazy="selectin",
        doc="Related meal plan (NULL until generation completes)"
    )

    # Table-level constraints and indexes
    __table_args__ = (
        Index("idx_payment_transaction_id", "payment_id", unique=True),
        Index("idx_payment_normalized_email", "normalized_email"),
        Index("idx_payment_paddle_created_at", "paddle_created_at"),
        Index("idx_payment_status", "payment_status"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<PaymentTransaction(id={self.id}, payment_id={self.payment_id}, "
            f"amount={self.amount} {self.currency}, payment_method={self.payment_method}, "
            f"payment_status={self.payment_status}, customer_email={self.customer_email}, "
            f"paddle_created_at={self.paddle_created_at})>"
        )
