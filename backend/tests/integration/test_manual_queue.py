"""
Integration tests for ManualResolution queue (T127E).

Tests:
1. Create entry with issue_type="missing_quiz_data"
2. Create entry with issue_type="ai_validation_failed"
3. Create entry with issue_type="email_delivery_failed"
4. Status transitions: pending -> in_progress -> resolved
5. SLA deadline = created_at + 4 hours
6. Query pending entries ordered by sla_deadline (most urgent first)
"""

import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.manual_resolution import ManualResolution
from src.lib.email_utils import normalize_email


# --- Helpers ---

def create_resolution_entry(
    issue_type: str,
    payment_id: str = None,
    email: str = "test@example.com",
    sla_offset_hours: float = 0,
) -> ManualResolution:
    """Helper to create a ManualResolution entry."""
    now = datetime.utcnow()
    return ManualResolution(
        id=str(uuid.uuid4()),
        payment_id=payment_id or f"pay_{uuid.uuid4().hex[:12]}",
        user_email=email,
        normalized_email=normalize_email(email),
        issue_type=issue_type,
        status="pending",
        sla_deadline=now + timedelta(hours=4) + timedelta(hours=sla_offset_hours),
        created_at=now + timedelta(hours=sla_offset_hours),
    )


# --- Tests ---

@pytest.mark.asyncio
async def test_create_missing_quiz_data_entry(test_session: AsyncSession):
    """T127E-1: Create manual resolution entry with issue_type='missing_quiz_data'."""
    entry = create_resolution_entry(issue_type="missing_quiz_data")
    test_session.add(entry)
    await test_session.commit()
    await test_session.refresh(entry)

    assert entry.id is not None
    assert entry.issue_type == "missing_quiz_data"
    assert entry.status == "pending"
    assert entry.resolved_at is None
    assert entry.assigned_to is None


@pytest.mark.asyncio
async def test_create_ai_validation_failed_entry(test_session: AsyncSession):
    """T127E-2: Create manual resolution entry with issue_type='ai_validation_failed'."""
    entry = create_resolution_entry(issue_type="ai_validation_failed")
    test_session.add(entry)
    await test_session.commit()
    await test_session.refresh(entry)

    assert entry.issue_type == "ai_validation_failed"
    assert entry.status == "pending"
    assert entry.payment_id is not None


@pytest.mark.asyncio
async def test_create_email_delivery_failed_entry(test_session: AsyncSession):
    """T127E-3: Create manual resolution entry with issue_type='email_delivery_failed'."""
    entry = create_resolution_entry(
        issue_type="email_delivery_failed",
        email="delivery.fail@gmail.com",
    )
    test_session.add(entry)
    await test_session.commit()
    await test_session.refresh(entry)

    assert entry.issue_type == "email_delivery_failed"
    assert entry.user_email == "delivery.fail@gmail.com"
    assert entry.normalized_email == normalize_email("delivery.fail@gmail.com")


@pytest.mark.asyncio
async def test_status_transitions(test_session: AsyncSession):
    """T127E-4: Status transitions: pending -> in_progress -> resolved."""
    entry = create_resolution_entry(issue_type="missing_quiz_data")
    test_session.add(entry)
    await test_session.commit()

    # pending -> in_progress
    entry.status = "in_progress"
    entry.assigned_to = "admin@example.com"
    await test_session.commit()
    await test_session.refresh(entry)
    assert entry.status == "in_progress"
    assert entry.assigned_to == "admin@example.com"

    # in_progress -> resolved
    entry.status = "resolved"
    entry.resolved_at = datetime.utcnow()
    entry.resolution_notes = "Manually regenerated meal plan"
    await test_session.commit()
    await test_session.refresh(entry)
    assert entry.status == "resolved"
    assert entry.resolved_at is not None
    assert entry.resolution_notes == "Manually regenerated meal plan"


@pytest.mark.asyncio
async def test_sla_deadline_four_hours(test_session: AsyncSession):
    """T127E-5: SLA deadline = created_at + 4 hours."""
    entry = create_resolution_entry(issue_type="ai_validation_failed")
    test_session.add(entry)
    await test_session.commit()
    await test_session.refresh(entry)

    # sla_deadline should be ~4 hours after created_at
    delta = entry.sla_deadline - entry.created_at
    # Allow 2 second tolerance for test execution time
    assert abs(delta.total_seconds() - 4 * 3600) < 2, (
        f"SLA deadline should be 4 hours after created_at, got {delta.total_seconds()}s"
    )


@pytest.mark.asyncio
async def test_pending_entries_ordered_by_sla_deadline(test_session: AsyncSession):
    """T127E-6: Query pending entries ordered by sla_deadline (most urgent first)."""
    # Create entries with different SLA deadlines
    # Entry 1: SLA in 4 hours (latest)
    entry_late = create_resolution_entry(
        issue_type="email_delivery_failed",
        email="late@example.com",
        sla_offset_hours=2,
    )
    # Entry 2: SLA in 2 hours (earliest/most urgent)
    entry_urgent = create_resolution_entry(
        issue_type="missing_quiz_data",
        email="urgent@example.com",
        sla_offset_hours=-2,
    )
    # Entry 3: SLA in 3 hours (middle)
    entry_mid = create_resolution_entry(
        issue_type="ai_validation_failed",
        email="mid@example.com",
        sla_offset_hours=0,
    )

    test_session.add_all([entry_late, entry_urgent, entry_mid])
    await test_session.commit()

    # Query pending entries ordered by SLA deadline (most urgent first)
    result = await test_session.execute(
        select(ManualResolution)
        .where(ManualResolution.status == "pending")
        .order_by(ManualResolution.sla_deadline.asc())
    )
    entries = result.scalars().all()

    # Filter to our test entries only
    test_emails = {"late@example.com", "urgent@example.com", "mid@example.com"}
    test_entries = [e for e in entries if e.user_email in test_emails]

    assert len(test_entries) >= 3
    # Most urgent (earliest SLA) should be first
    assert test_entries[0].user_email == "urgent@example.com"
    assert test_entries[1].user_email == "mid@example.com"
    assert test_entries[2].user_email == "late@example.com"
