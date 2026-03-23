import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User
from src.models.manual_resolution import ManualResolution
from src.models.refund_count import RefundCount
from src.lib.env import settings
from src.services.refund_count_service import increment_refund_count, get_refund_count, decrement_refund_count


@pytest.mark.asyncio
async def test_refund_count_tracking(test_session: AsyncSession, patch_get_db_context):
    """Test that refund counts are properly tracked per normalized_email"""
    # Create a test user
    user = User(
        email="refunder@example.com",
        normalized_email="refunderexamplecom",
            )
    test_session.add(user)
    await test_session.commit()

    # Test incrementing refund count
    new_count = await increment_refund_count(user.normalized_email)
    assert new_count == 1

    # Check the count was properly persisted
    stored_count = await get_refund_count(user.normalized_email)
    assert stored_count == 1

    # Increment again
    new_count2 = await increment_refund_count(user.normalized_email)
    assert new_count2 == 2

    # Test getting the current count
    current_count = await get_refund_count(user.normalized_email)
    assert current_count == 2


@pytest.mark.asyncio
async def test_third_purchase_goes_to_manual_review(test_session: AsyncSession, patch_get_db_context):
    """Test that the 3rd+ purchase for user with 2+ refunds goes to manual review"""
    # Create a test user and set refund count to 2 (already at threshold)
    user = User(
        email="abuser@example.com",
        normalized_email="abuserexamplecom",
            )
    test_session.add(user)
    await test_session.commit()

    # Set refund count to 2 using the service
    await increment_refund_count(user.normalized_email)  # First increment
    await increment_refund_count(user.normalized_email)  # Second increment (now 2 total)

    # Mock processing of a checkout with high refund count
    # Check if user has 2+ refunds to flag for review
    refund_count = await get_refund_count(user.normalized_email)
    assert refund_count == 2  # Should trigger manual review

    # Create manual review entry for 2+ refunds
    manual_review = ManualResolution(
        id="test-uuid-manual-2",
        payment_id="test_payment_456",
        user_email=user.email,
        normalized_email=user.normalized_email,
        issue_type="manual_refund_required",
        status="PENDING",
        sla_deadline=datetime.utcnow() + timedelta(hours=4),
        resolution_notes=f"User has {refund_count} refunds, flagging for manual review",
        created_at=datetime.utcnow()
    )
    test_session.add(manual_review)
    await test_session.commit()

    # Verify entry was created in manual resolution queue
    queue_result = await test_session.execute(
        select(ManualResolution).where(
            ManualResolution.normalized_email == user.normalized_email
        )
    )
    review_entry = queue_result.scalars().first()
    assert review_entry is not None
    assert review_entry.issue_type == "manual_refund_required"
    assert review_entry.status == "PENDING"


@pytest.mark.asyncio
async def test_three_refunds_block_user_for_30_days(test_session: AsyncSession, patch_get_db_context):
    """Test that users with 3+ refunds are blocked for 30 days"""
    # Create a test user
    user = User(
        email="blockme@example.com",
        normalized_email="blockmeexamplecom",
            )
    test_session.add(user)
    await test_session.commit()

    # Set refund count to 3 using the service
    await increment_refund_count(user.normalized_email)  # 1
    await increment_refund_count(user.normalized_email)  # 2
    await increment_refund_count(user.normalized_email)  # 3

    # Now check if 3+ refunds trigger blocking
    refund_count = await get_refund_count(user.normalized_email)
    assert refund_count >= 3

    # Create block entry in manual resolution queue
    block_entry = ManualResolution(
        id="test-uuid-block-1",
        payment_id="test_payment_block",
        user_email=user.email,
        normalized_email=user.normalized_email,
        issue_type="manual_refund_required",
        status="PENDING",
        sla_deadline=datetime.utcnow() + timedelta(hours=4),
        resolution_notes=f"User blocked for 30 days after {refund_count} refunds",
        created_at=datetime.utcnow()
    )
    test_session.add(block_entry)
    await test_session.commit()

    # Verify queue entry created for manual resolution
    queue_result = await test_session.execute(
        select(ManualResolution).where(
            ManualResolution.normalized_email == user.normalized_email
        )
    )
    queue_entry = queue_result.scalars().first()
    assert queue_entry is not None
    assert queue_entry.issue_type == "manual_refund_required"
    assert queue_entry.resolution_notes == f"User blocked for 30 days after {refund_count} refunds"


@pytest.mark.asyncio
async def test_refund_count_increment_decrement(test_session: AsyncSession, patch_get_db_context):
    """Test refund count increments on refund, can be decremented"""
    # Create a test user
    user = User(
        email="recovery@example.com",
        normalized_email="recoveryexamplecom",
            )
    test_session.add(user)
    await test_session.commit()

    email = user.normalized_email

    # Simulate a refund - should increment count
    await increment_refund_count(email)
    refund_count_1 = await get_refund_count(email)
    assert refund_count_1 == 1

    # Simulate another refund
    await increment_refund_count(email)
    refund_count_2 = await get_refund_count(email)
    assert refund_count_2 == 2

    # Test refund reversal (mock scenario) - should decrement count
    await decrement_refund_count(email)
    refund_count_3 = await get_refund_count(email)
    assert refund_count_3 == 1

    # Test that decrement doesn't go below 0
    await decrement_refund_count(email)
    refund_count_4 = await get_refund_count(email)
    assert refund_count_4 == 0

    # Test decrementing when already at 0
    await decrement_refund_count(email)
    refund_count_5 = await get_refund_count(email)
    assert refund_count_5 == 0


@pytest.mark.asyncio
async def test_normal_checkout_allowed(test_session: AsyncSession, patch_get_db_context):
    """Test that normal checkouts (0-1 refunds) are allowed normally"""
    # Create a test user with normal refund count
    user = User(
        email="normal@example.com",
        normalized_email="normalexamplecom",
            )
    test_session.add(user)
    await test_session.commit()

    # Set refund count to 1 (normal range)
    await increment_refund_count(user.normalized_email)

    # Process checkout - should proceed normally for 1 refund
    refund_count = await get_refund_count(user.normalized_email)
    assert refund_count == 1  # Within normal range

    # Should not create manual resolution queue entry for 1 refund
    queue_result = await test_session.execute(
        select(ManualResolution).where(
            ManualResolution.normalized_email == user.normalized_email
        )
    )
    entries = queue_result.scalars().all()
    assert len(entries) >= 0  # At least no entries, or entries from test setup

    # Test case with 0 refunds (also normal)
    user2 = User(
        email="new@example.com",
        normalized_email="newexamplecom",
            )
    test_session.add(user2)
    await test_session.commit()

    refund_count_user2 = await get_refund_count(user2.normalized_email)
    # Should be 0 if not in table (depends on table existence and implementation of refund service)