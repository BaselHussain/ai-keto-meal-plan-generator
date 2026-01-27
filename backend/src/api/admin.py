"""
Admin Dashboard API Endpoints

Provides admin-only endpoints for:
- Manual resolution queue management
- Quick actions (resolve, regenerate PDF, refund)
- SLA breach monitoring

All endpoints require admin authentication via:
- X-API-Key header (must match ADMIN_API_KEY env var)
- IP whitelist check (ADMIN_IP_WHITELIST env var)

Functional Requirement: FR-M-005 (Admin dashboard)
Reference: tasks.md T127H-T127J
"""

import logging
from datetime import datetime
from typing import Annotated, Literal, Optional
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session

from src.lib.database import get_db
from src.middleware.admin_auth import require_admin_auth
from src.models.manual_resolution import ManualResolution
from src.schemas.admin import (
    ManualResolutionListResponse,
    ManualResolutionEntry,
    ResolveRequest,
    QuickActionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")


def calculate_hours_until_sla_breach(sla_deadline: datetime) -> float:
    """
    Calculate hours remaining until SLA breach.

    Args:
        sla_deadline: SLA deadline timestamp (UTC)

    Returns:
        float: Hours remaining (negative if breached)
    """
    now = datetime.utcnow()
    delta = sla_deadline - now
    return delta.total_seconds() / 3600


@router.get(
    "/manual-resolution",
    response_model=ManualResolutionListResponse,
    summary="List manual resolution queue entries",
    description=(
        "Returns paginated list of manual resolution entries with SLA countdown. "
        "Supports filtering by status and sorting by priority, created_at, or sla_deadline."
    ),
)
async def list_manual_resolution_entries(
    admin: Annotated[dict, Depends(require_admin_auth)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: Optional[Literal["pending", "in_progress", "resolved", "escalated", "sla_missed_refunded"]] = Query(
        None,
        description="Filter by status (pending, in_progress, resolved, escalated, sla_missed_refunded)"
    ),
    sort_by: Literal["priority", "created_at", "sla_deadline"] = Query(
        "sla_deadline",
        description="Sort field (priority=SLA breach urgency, created_at, sla_deadline)"
    ),
    sort_order: Literal["asc", "desc"] = Query(
        "asc",
        description="Sort order (asc or desc)"
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Entries per page (max 100)"),
) -> ManualResolutionListResponse:
    """
    List manual resolution queue entries for admin dashboard.

    Features:
    - Pagination support (default 10 per page, max 100)
    - Status filtering (pending, in_progress, resolved, escalated, sla_missed_refunded)
    - Sorting by priority (SLA urgency), created_at, or sla_deadline
    - SLA countdown calculation (hours remaining until breach)
    - Pending count badge
    - SLA breached count badge

    Args:
        admin: Admin user context from authentication middleware
        db: Database session
        status_filter: Filter by status (optional)
        sort_by: Sort field (priority, created_at, sla_deadline)
        sort_order: Sort order (asc or desc)
        page: Page number (1-indexed)
        page_size: Entries per page (max 100)

    Returns:
        ManualResolutionListResponse: Paginated entries with metadata

    Raises:
        HTTPException: 500 if database query fails
    """
    try:
        logger.info(
            f"Admin {admin['ip']} listing manual resolution entries",
            extra={
                "admin_ip": admin["ip"],
                "status_filter": status_filter,
                "sort_by": sort_by,
                "page": page,
                "page_size": page_size,
            }
        )

        # Build base query
        query = select(ManualResolution)

        # Apply status filter
        if status_filter:
            query = query.where(ManualResolution.status == status_filter)

        # Count total entries (before pagination)
        total_query = select(func.count()).select_from(query.subquery())
        total = db.execute(total_query).scalar() or 0

        # Count pending entries (for badge)
        pending_query = select(func.count()).where(ManualResolution.status == "pending")
        pending_count = db.execute(pending_query).scalar() or 0

        # Count SLA breached entries (for badge)
        sla_breached_query = select(func.count()).where(
            ManualResolution.sla_deadline < datetime.utcnow()
        )
        sla_breached_count = db.execute(sla_breached_query).scalar() or 0

        # Apply sorting
        if sort_by == "priority":
            # Priority = SLA deadline (most urgent first)
            if sort_order == "asc":
                query = query.order_by(ManualResolution.sla_deadline.asc())
            else:
                query = query.order_by(ManualResolution.sla_deadline.desc())
        elif sort_by == "created_at":
            if sort_order == "asc":
                query = query.order_by(ManualResolution.created_at.asc())
            else:
                query = query.order_by(ManualResolution.created_at.desc())
        elif sort_by == "sla_deadline":
            if sort_order == "asc":
                query = query.order_by(ManualResolution.sla_deadline.asc())
            else:
                query = query.order_by(ManualResolution.sla_deadline.desc())

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = db.execute(query)
        manual_resolution_entries = result.scalars().all()

        # Transform to response schema
        entries = []
        for entry in manual_resolution_entries:
            hours_until_breach = calculate_hours_until_sla_breach(entry.sla_deadline)
            entries.append(
                ManualResolutionEntry(
                    id=entry.id,
                    payment_id=entry.payment_id,
                    user_email=entry.user_email,
                    normalized_email=entry.normalized_email,
                    issue_type=entry.issue_type,
                    status=entry.status,
                    sla_deadline=entry.sla_deadline,
                    hours_until_sla_breach=hours_until_breach,
                    created_at=entry.created_at,
                    resolved_at=entry.resolved_at,
                    assigned_to=entry.assigned_to,
                    resolution_notes=entry.resolution_notes,
                )
            )

        # Calculate total pages
        total_pages = ceil(total / page_size) if total > 0 else 0

        logger.info(
            f"Returned {len(entries)} manual resolution entries (page {page}/{total_pages})",
            extra={
                "admin_ip": admin["ip"],
                "total": total,
                "page": page,
                "page_size": page_size,
                "pending_count": pending_count,
                "sla_breached_count": sla_breached_count,
            }
        )

        return ManualResolutionListResponse(
            entries=entries,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            pending_count=pending_count,
            sla_breached_count=sla_breached_count,
        )

    except Exception as e:
        logger.error(
            f"Failed to list manual resolution entries: {str(e)}",
            exc_info=True,
            extra={"admin_ip": admin["ip"]}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Failed to retrieve manual resolution entries",
                "code": "database_error"
            }
        )


@router.post(
    "/manual-resolution/{entry_id}/resolve",
    response_model=QuickActionResponse,
    summary="Mark manual resolution entry as resolved",
    description="Updates entry status to 'resolved' and records resolution notes",
)
async def resolve_manual_resolution_entry(
    entry_id: str,
    resolve_request: ResolveRequest,
    admin: Annotated[dict, Depends(require_admin_auth)],
    db: Annotated[Session, Depends(get_db)],
) -> QuickActionResponse:
    """
    Mark manual resolution entry as resolved.

    Updates:
    - status -> resolved
    - resolved_at -> current timestamp (UTC)
    - assigned_to -> admin user (if provided)
    - resolution_notes -> admin notes

    Args:
        entry_id: Manual resolution entry ID (UUID)
        resolve_request: Resolution details (assigned_to, resolution_notes)
        admin: Admin user context from authentication middleware
        db: Database session

    Returns:
        QuickActionResponse: Confirmation with updated status

    Raises:
        HTTPException: 404 if entry not found, 500 if update fails
    """
    try:
        logger.info(
            f"Admin {admin['ip']} resolving manual resolution entry {entry_id}",
            extra={"admin_ip": admin["ip"], "entry_id": entry_id}
        )

        # Find entry
        query = select(ManualResolution).where(ManualResolution.id == entry_id)
        result = db.execute(query)
        entry = result.scalar_one_or_none()

        if not entry:
            logger.warning(
                f"Manual resolution entry {entry_id} not found",
                extra={"admin_ip": admin["ip"], "entry_id": entry_id}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": f"Manual resolution entry {entry_id} not found",
                    "code": "entry_not_found"
                }
            )

        # Update entry
        entry.status = "resolved"
        entry.resolved_at = datetime.utcnow()
        entry.assigned_to = resolve_request.assigned_to or admin["ip"]
        entry.resolution_notes = resolve_request.resolution_notes

        db.commit()
        db.refresh(entry)

        logger.info(
            f"Manual resolution entry {entry_id} marked as resolved",
            extra={
                "admin_ip": admin["ip"],
                "entry_id": entry_id,
                "assigned_to": entry.assigned_to,
            }
        )

        return QuickActionResponse(
            success=True,
            message="Entry marked as resolved",
            entry_id=entry_id,
            updated_status="resolved",
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            f"Failed to resolve manual resolution entry {entry_id}: {str(e)}",
            exc_info=True,
            extra={"admin_ip": admin["ip"], "entry_id": entry_id}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Failed to resolve entry",
                "code": "database_error"
            }
        )


@router.post(
    "/manual-resolution/{entry_id}/regenerate",
    response_model=QuickActionResponse,
    summary="Trigger PDF regeneration for manual resolution entry",
    description="Marks entry as in_progress and triggers manual PDF regeneration (stub for now)",
)
async def regenerate_pdf_for_entry(
    entry_id: str,
    admin: Annotated[dict, Depends(require_admin_auth)],
    db: Annotated[Session, Depends(get_db)],
) -> QuickActionResponse:
    """
    Trigger PDF regeneration for manual resolution entry.

    Updates:
    - status -> in_progress
    - assigned_to -> admin IP

    Note: Actual PDF regeneration logic is a stub for now (Phase 9.6).
    Full implementation in Phase 10.x will trigger actual AI + PDF generation.

    Args:
        entry_id: Manual resolution entry ID (UUID)
        admin: Admin user context from authentication middleware
        db: Database session

    Returns:
        QuickActionResponse: Confirmation with updated status

    Raises:
        HTTPException: 404 if entry not found, 500 if update fails
    """
    try:
        logger.info(
            f"Admin {admin['ip']} triggering PDF regeneration for entry {entry_id}",
            extra={"admin_ip": admin["ip"], "entry_id": entry_id}
        )

        # Find entry
        query = select(ManualResolution).where(ManualResolution.id == entry_id)
        result = db.execute(query)
        entry = result.scalar_one_or_none()

        if not entry:
            logger.warning(
                f"Manual resolution entry {entry_id} not found",
                extra={"admin_ip": admin["ip"], "entry_id": entry_id}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": f"Manual resolution entry {entry_id} not found",
                    "code": "entry_not_found"
                }
            )

        # Update entry status
        entry.status = "in_progress"
        entry.assigned_to = admin["ip"]

        db.commit()
        db.refresh(entry)

        # TODO: Trigger actual PDF regeneration
        # This is a stub for now - full implementation in Phase 10.x will:
        # 1. Fetch quiz data from quiz_responses table
        # 2. Call AI meal plan generation service
        # 3. Generate PDF
        # 4. Upload to Vercel Blob
        # 5. Send delivery email
        # 6. Mark entry as resolved

        logger.info(
            f"PDF regeneration triggered for entry {entry_id} (stub implementation)",
            extra={"admin_ip": admin["ip"], "entry_id": entry_id}
        )

        return QuickActionResponse(
            success=True,
            message="PDF regeneration triggered (stub - full implementation in Phase 10.x)",
            entry_id=entry_id,
            updated_status="in_progress",
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            f"Failed to regenerate PDF for entry {entry_id}: {str(e)}",
            exc_info=True,
            extra={"admin_ip": admin["ip"], "entry_id": entry_id}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Failed to trigger PDF regeneration",
                "code": "database_error"
            }
        )


@router.post(
    "/manual-resolution/{entry_id}/refund",
    response_model=QuickActionResponse,
    summary="Issue refund for manual resolution entry",
    description="Marks entry as sla_missed_refunded and triggers refund (stub for now - Paddle not available)",
)
async def refund_for_entry(
    entry_id: str,
    admin: Annotated[dict, Depends(require_admin_auth)],
    db: Annotated[Session, Depends(get_db)],
) -> QuickActionResponse:
    """
    Issue refund for manual resolution entry.

    Updates:
    - status -> sla_missed_refunded
    - resolved_at -> current timestamp (UTC)
    - assigned_to -> admin IP
    - resolution_notes -> "Manual refund issued by admin"

    Note: Actual Paddle refund API call is a stub for now (Phase 9.6).
    Full implementation in Phase 10.x will call Paddle Refund API.

    Args:
        entry_id: Manual resolution entry ID (UUID)
        admin: Admin user context from authentication middleware
        db: Database session

    Returns:
        QuickActionResponse: Confirmation with updated status

    Raises:
        HTTPException: 404 if entry not found, 500 if update fails
    """
    try:
        logger.info(
            f"Admin {admin['ip']} issuing refund for entry {entry_id}",
            extra={"admin_ip": admin["ip"], "entry_id": entry_id}
        )

        # Find entry
        query = select(ManualResolution).where(ManualResolution.id == entry_id)
        result = db.execute(query)
        entry = result.scalar_one_or_none()

        if not entry:
            logger.warning(
                f"Manual resolution entry {entry_id} not found",
                extra={"admin_ip": admin["ip"], "entry_id": entry_id}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": f"Manual resolution entry {entry_id} not found",
                    "code": "entry_not_found"
                }
            )

        # Update entry
        entry.status = "sla_missed_refunded"
        entry.resolved_at = datetime.utcnow()
        entry.assigned_to = admin["ip"]
        entry.resolution_notes = f"Manual refund issued by admin {admin['ip']}"

        db.commit()
        db.refresh(entry)

        # TODO: Call Paddle Refund API
        # This is a stub for now - full implementation in Phase 10.x will:
        # 1. Call Paddle API to issue refund for payment_id
        # 2. Verify refund success
        # 3. Log refund transaction
        # 4. Send refund confirmation email to user

        logger.info(
            f"Refund issued for entry {entry_id} (stub implementation)",
            extra={
                "admin_ip": admin["ip"],
                "entry_id": entry_id,
                "payment_id": entry.payment_id,
            }
        )

        return QuickActionResponse(
            success=True,
            message="Refund issued (stub - full Paddle integration in Phase 10.x)",
            entry_id=entry_id,
            updated_status="sla_missed_refunded",
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            f"Failed to issue refund for entry {entry_id}: {str(e)}",
            exc_info=True,
            extra={"admin_ip": admin["ip"], "entry_id": entry_id}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Failed to issue refund",
                "code": "database_error"
            }
        )
