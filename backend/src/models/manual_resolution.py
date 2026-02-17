"""
ManualResolution Model

Queue for failed operations requiring manual intervention (FR-M-001 to FR-M-006).

Schema Design:
- Each entry represents a failed operation that requires manual admin intervention
- payment_id links to the Paddle payment that triggered the failed operation
- normalized_email enables cross-queue pattern detection for fraud/abuse
- sla_deadline set to created_at + 4 hours for auto-refund trigger
- Status lifecycle: pending -> in_progress -> resolved/escalated/sla_missed_refunded
- Issue types track different failure categories for routing and metrics

Indexes:
- idx_manual_sla_deadline: Fast SLA breach detection queries (every 30 seconds)
- idx_manual_status: Queue filtering by status for admin dashboard
- idx_manual_created_at: 1-year retention cleanup queries

Data Retention Policy:
- All manual resolution entries deleted 1 year after created_at
- Automatic cleanup via scheduled cleanup job (see T092-T095)
- Retention required for compliance audit and pattern analysis

Issue Types:
- missing_quiz_data: Quiz response not found or expired during meal plan generation
- ai_validation_failed: Meal plan validation failed after 3 retries
- email_delivery_failed: Email delivery failed after all retry attempts
- manual_refund_required: Admin-triggered refund (e.g., customer service request)

Status Lifecycle:
- pending: New entry awaiting admin assignment (default)
- in_progress: Admin actively working on the issue
- resolved: Issue successfully resolved
- escalated: Escalated to higher-tier support or engineering
- sla_missed_refunded: SLA deadline missed, auto-refund triggered

Use Cases:
- Admin Dashboard: Queue view filtered by status, sorted by SLA deadline
- SLA Monitoring: Automated checks every 30 seconds for SLA breach
- Auto-Refund Trigger: Issues with status=pending AND sla_deadline < now()
- Pattern Analysis: Detect systemic issues via issue_type clustering
- Audit Trail: Track resolution history with assigned_to and resolution_notes

Security Notes:
- Only stores normalized_email (no PII like full name, phone, address)
- Resolution notes may contain sensitive customer information - access control required
- Payment ID allows admin to look up full transaction details in Paddle dashboard
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Index, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum as SQLEnum

from src.lib.database import Base
from .issue_type import IssueType


class ManualResolution(Base):
    """
    Manual resolution queue entity for failed operations requiring admin intervention.

    Each manual resolution entry represents a failed operation (meal plan generation,
    email delivery, etc.) that could not be automatically resolved and requires manual
    admin action. Entries are tracked through a status lifecycle and have SLA deadlines
    for auto-refund triggers.

    Attributes:
        id: Unique queue entry identifier (UUID as string)
        payment_id: Paddle payment ID that triggered the failed operation
        user_email: Original email address from payment/quiz
        normalized_email: Normalized email for cross-queue pattern detection
        issue_type: Category of failure (missing_quiz_data, ai_validation_failed, etc.)
        status: Current queue status (pending, in_progress, resolved, escalated, sla_missed_refunded)
        sla_deadline: Auto-refund trigger timestamp (created_at + 4 hours, UTC)
        created_at: Queue entry creation timestamp (UTC, indexed for cleanup)
        resolved_at: Resolution timestamp (NULL until resolved, UTC)
        assigned_to: Admin user assigned to this issue (email or username)
        resolution_notes: Free-form admin notes documenting resolution steps

    Issue Type Values:
        - missing_quiz_data: Quiz response not found or expired
        - ai_validation_failed: Meal plan validation failed after retries
        - email_delivery_failed: Email delivery failed after retries
        - manual_refund_required: Admin-triggered refund request

    Status Values:
        - pending: New entry awaiting assignment (default)
        - in_progress: Admin actively working on issue
        - resolved: Issue successfully resolved
        - escalated: Escalated to higher-tier support
        - sla_missed_refunded: SLA deadline missed, auto-refund triggered

    Retention Policy:
        - Deleted 1 year after created_at via scheduled cleanup job
        - Required for compliance audit and pattern analysis
    """

    __tablename__ = "manual_resolution"

    # Primary key (UUID as string)
    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique queue entry identifier (UUID)"
    )

    # Payment tracking
    payment_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Paddle payment ID that triggered the failed operation"
    )

    # Email fields (original and normalized)
    user_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Original email address from payment/quiz"
    )

    normalized_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Normalized email for cross-queue pattern detection (lowercase, dots/plus removed)"
    )

    # Issue classification
    issue_type: Mapped[IssueType] = mapped_column(
        SQLEnum(IssueType, name="issue_type_enum"),
        nullable=False,
        doc="Failure category (missing_quiz_data, ai_validation_failed, email_delivery_failed, manual_refund_required)"
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        doc="Queue status (pending, in_progress, resolved, escalated, sla_missed_refunded)"
    )

    # SLA management
    sla_deadline: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
        doc="Auto-refund trigger timestamp (created_at + 4 hours, UTC)"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
        doc="Queue entry creation timestamp (UTC, indexed for 1-year cleanup)"
    )

    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="Resolution timestamp (NULL until resolved, UTC)"
    )

    # Admin assignment and notes
    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Admin user assigned to this issue (email or username)"
    )

    resolution_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Free-form admin notes documenting resolution steps"
    )

    # Table-level constraints and indexes
    __table_args__ = (
        Index("idx_manual_sla_deadline", "sla_deadline"),
        Index("idx_manual_status", "status"),
        Index("idx_manual_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<ManualResolution(id={self.id}, payment_id={self.payment_id}, "
            f"issue_type={self.issue_type}, status={self.status}, "
            f"user_email={self.user_email}, sla_deadline={self.sla_deadline}, "
            f"created_at={self.created_at})>"
        )
