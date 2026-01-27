"""
Pydantic schemas for admin dashboard and manual resolution operations.

Admin endpoints return these schemas for:
- Manual resolution queue listing
- Quick action responses (resolve, regenerate PDF, refund)
- SLA breach monitoring

Functional Requirement: FR-M-005 (Admin dashboard)
Reference: tasks.md T127H-T127J
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ManualResolutionEntry(BaseModel):
    """
    Single manual resolution queue entry for admin dashboard.

    Attributes:
        id: Queue entry ID (UUID)
        payment_id: Paddle payment ID
        user_email: Original email from payment
        normalized_email: Normalized email for pattern detection
        issue_type: Failure category (missing_quiz_data, ai_validation_failed, etc.)
        status: Current status (pending, in_progress, resolved, escalated, sla_missed_refunded)
        sla_deadline: Timestamp when SLA breach occurs (UTC)
        hours_until_sla_breach: Calculated hours remaining until SLA breach (negative if breached)
        created_at: Entry creation timestamp (UTC)
        resolved_at: Resolution timestamp (NULL if not resolved, UTC)
        assigned_to: Admin user assigned to this issue
        resolution_notes: Admin notes documenting resolution

    Example:
        {
            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "payment_id": "txn_01h2x3y4z5",
            "user_email": "user@example.com",
            "normalized_email": "user@example.com",
            "issue_type": "ai_validation_failed",
            "status": "pending",
            "sla_deadline": "2024-01-15T12:00:00Z",
            "hours_until_sla_breach": 2.5,
            "created_at": "2024-01-15T08:00:00Z",
            "resolved_at": null,
            "assigned_to": null,
            "resolution_notes": null
        }
    """

    id: str = Field(
        description="Queue entry ID (UUID)",
        examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
    )

    payment_id: str = Field(
        description="Paddle payment ID",
        examples=["txn_01h2x3y4z5"]
    )

    user_email: str = Field(
        description="Original email from payment/quiz",
        examples=["user@example.com"]
    )

    normalized_email: str = Field(
        description="Normalized email for pattern detection",
        examples=["user@example.com"]
    )

    issue_type: str = Field(
        description="Failure category",
        examples=["ai_validation_failed", "missing_quiz_data", "email_delivery_failed"]
    )

    status: str = Field(
        description="Current queue status",
        examples=["pending", "in_progress", "resolved", "escalated", "sla_missed_refunded"]
    )

    sla_deadline: datetime = Field(
        description="Timestamp when SLA breach occurs (UTC)",
        examples=["2024-01-15T12:00:00Z"]
    )

    hours_until_sla_breach: float = Field(
        description="Hours remaining until SLA breach (negative if breached)",
        examples=[2.5, -0.5]
    )

    created_at: datetime = Field(
        description="Entry creation timestamp (UTC)",
        examples=["2024-01-15T08:00:00Z"]
    )

    resolved_at: Optional[datetime] = Field(
        default=None,
        description="Resolution timestamp (NULL if not resolved, UTC)",
        examples=["2024-01-15T10:30:00Z", None]
    )

    assigned_to: Optional[str] = Field(
        default=None,
        description="Admin user assigned to this issue",
        examples=["admin@ketomealplan.com", None]
    )

    resolution_notes: Optional[str] = Field(
        default=None,
        description="Admin notes documenting resolution",
        examples=["Manually regenerated PDF and sent email", None]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "payment_id": "txn_01h2x3y4z5",
                "user_email": "user@example.com",
                "normalized_email": "user@example.com",
                "issue_type": "ai_validation_failed",
                "status": "pending",
                "sla_deadline": "2024-01-15T12:00:00Z",
                "hours_until_sla_breach": 2.5,
                "created_at": "2024-01-15T08:00:00Z",
                "resolved_at": None,
                "assigned_to": None,
                "resolution_notes": None
            }
        }
    )


class ManualResolutionListResponse(BaseModel):
    """
    Paginated list of manual resolution entries for admin dashboard.

    Attributes:
        entries: List of manual resolution entries
        total: Total number of entries matching filters
        page: Current page number (1-indexed)
        page_size: Number of entries per page
        total_pages: Total number of pages
        pending_count: Count of entries with status=pending
        sla_breached_count: Count of entries with hours_until_sla_breach < 0

    Example:
        {
            "entries": [...],
            "total": 15,
            "page": 1,
            "page_size": 10,
            "total_pages": 2,
            "pending_count": 8,
            "sla_breached_count": 2
        }
    """

    entries: List[ManualResolutionEntry] = Field(
        description="List of manual resolution entries"
    )

    total: int = Field(
        description="Total number of entries matching filters",
        examples=[15]
    )

    page: int = Field(
        ge=1,
        description="Current page number (1-indexed)",
        examples=[1]
    )

    page_size: int = Field(
        ge=1,
        le=100,
        description="Number of entries per page",
        examples=[10]
    )

    total_pages: int = Field(
        ge=0,
        description="Total number of pages",
        examples=[2]
    )

    pending_count: int = Field(
        description="Count of entries with status=pending",
        examples=[8]
    )

    sla_breached_count: int = Field(
        description="Count of entries with hours_until_sla_breach < 0",
        examples=[2]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entries": [
                    {
                        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "payment_id": "txn_01h2x3y4z5",
                        "user_email": "user@example.com",
                        "normalized_email": "user@example.com",
                        "issue_type": "ai_validation_failed",
                        "status": "pending",
                        "sla_deadline": "2024-01-15T12:00:00Z",
                        "hours_until_sla_breach": 2.5,
                        "created_at": "2024-01-15T08:00:00Z",
                        "resolved_at": None,
                        "assigned_to": None,
                        "resolution_notes": None
                    }
                ],
                "total": 15,
                "page": 1,
                "page_size": 10,
                "total_pages": 2,
                "pending_count": 8,
                "sla_breached_count": 2
            }
        }
    )


class ResolveRequest(BaseModel):
    """
    Request to mark manual resolution entry as resolved.

    Attributes:
        assigned_to: Admin user marking as resolved (optional)
        resolution_notes: Notes documenting resolution (required)

    Example:
        {
            "assigned_to": "admin@ketomealplan.com",
            "resolution_notes": "Manually regenerated PDF and sent email to customer"
        }
    """

    assigned_to: Optional[str] = Field(
        default=None,
        description="Admin user marking as resolved",
        examples=["admin@ketomealplan.com"]
    )

    resolution_notes: str = Field(
        min_length=1,
        description="Notes documenting resolution (required)",
        examples=["Manually regenerated PDF and sent email to customer"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "assigned_to": "admin@ketomealplan.com",
                "resolution_notes": "Manually regenerated PDF and sent email to customer"
            }
        }
    )


class QuickActionResponse(BaseModel):
    """
    Response for quick admin actions (resolve, regenerate, refund).

    Attributes:
        success: Whether action was successful
        message: Human-readable confirmation message
        entry_id: Manual resolution entry ID
        updated_status: New status after action

    Example:
        {
            "success": true,
            "message": "Entry marked as resolved",
            "entry_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "updated_status": "resolved"
        }
    """

    success: bool = Field(
        description="Whether action was successful",
        examples=[True]
    )

    message: str = Field(
        description="Human-readable confirmation message",
        examples=["Entry marked as resolved", "PDF regeneration triggered"]
    )

    entry_id: str = Field(
        description="Manual resolution entry ID",
        examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
    )

    updated_status: str = Field(
        description="New status after action",
        examples=["resolved", "in_progress", "sla_missed_refunded"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Entry marked as resolved",
                "entry_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "updated_status": "resolved"
            }
        }
    )
