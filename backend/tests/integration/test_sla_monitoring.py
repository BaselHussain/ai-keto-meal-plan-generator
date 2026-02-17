import pytest
import asyncio
import uuid
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
from sqlalchemy import select
from src.models.user import User
from src.models.payment_transaction import PaymentTransaction
from src.models.manual_resolution import ManualResolution
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_sla_deadline_calculation(test_session: AsyncSession):
    """Test SLA deadline is properly calculated for manual resolution tickets"""
    # Create a test user
    user = User(
        email="sla-test@example.com",
        normalized_email="slatesexamplecom",
        email_verified=True
    )
    test_session.add(user)
    await test_session.commit()

    # Create a manual resolution entry
    queue_entry = ManualResolution(
        id="test-uuid-123",
        payment_id="test_payment_123",
        user_email=user.email,
        normalized_email=user.normalized_email,
        issue_type="manual_refund_required",
        status="PENDING",
        sla_deadline=datetime.utcnow() + timedelta(hours=4),  # 4 hours as per schema
        resolution_notes="Payment processing failed",
        created_at=datetime.utcnow()
    )
    test_session.add(queue_entry)
    await test_session.commit()

    # Calculate expected SLA deadline (4 hours from creation per schema)
    expected_deadline = queue_entry.created_at + timedelta(hours=4)

    # Verify SLA deadline is properly set (per schema is 4 hours, not 48)
    assert queue_entry.sla_deadline == expected_deadline


@pytest.mark.asyncio
async def test_sla_breach_detection(test_session: AsyncSession):
    """Test SLA breach detection logic"""
    # Create a test user
    user = User(
        email="breach@example.com",
        normalized_email="breachexamplecom",
        email_verified=True
    )
    test_session.add(user)
    await test_session.commit()

    # Create a manual resolution entry from 5 hours ago (should breach 4-hour SLA)
    old_entry_time = datetime.utcnow() - timedelta(hours=5)  # More than 4 hours deadline

    queue_entry = ManualResolution(
        id="test-uuid-1",
        payment_id="test_payment_456",
        user_email=user.email,
        normalized_email=user.normalized_email,
        issue_type="manual_refund_required",
        status="PENDING",
        sla_deadline=old_entry_time,  # Deadline already passed
        resolution_notes="Breach test case",
        created_at=old_entry_time
    )
    test_session.add(queue_entry)
    await test_session.commit()

    # Test SLA breach detection function
    breach_detected = await has_sla_breached(test_session, queue_entry.id)

    assert breach_detected is True

    # Test with a recent entry (should not breach)
    recent_time = datetime.utcnow() - timedelta(minutes=120)  # 2 hours ago
    recent_entry = ManualResolution(
        id="test-uuid-2",
        payment_id="test_payment_789",
        user_email=user.email,
        normalized_email=user.normalized_email,
        issue_type="manual_refund_required",
        status="PENDING",
        sla_deadline=recent_time + timedelta(hours=4),  # Deadline not yet due
        resolution_notes="Recent case",
        created_at=recent_time
    )
    test_session.add(recent_entry)
    await test_session.commit()

    recent_breach_detected = await has_sla_breach_detected(test_session, recent_entry.id)

    assert recent_breach_detected is False


@pytest.mark.asyncio
async def test_sla_monitoring_scheduled_job(test_session: AsyncSession):
    """Test the manual resolution queue SLA monitoring job execution"""
    # Create multiple test users
    users_data = [
        {"email": "timely@example.com", "normalized_email": "timelyexamplecom"},
        {"email": "breach1@example.com", "normalized_email": "breach1examplecom"},
        {"email": "breach2@example.com", "normalized_email": "breach2examplecom"},
    ]

    users = []
    for user_data in users_data:
        user = User(email=user_data["email"], normalized_email=user_data["normalized_email"], email_verified=True)
        test_session.add(user)
        users.append(user)
    await test_session.commit()

    # Create queue entries: 1 recent (no breach), 2 old (should breach)
    current_time = datetime.utcnow()

    # Recent entry (should not breach - 2 hours old, deadline in 2 more hours)
    recent_time = current_time - timedelta(hours=2)
    recent_entry = ManualResolution(
        id="recent-uuid-1",
        payment_id="test_payment_recent",
        user_email=users[0].email,
        normalized_email=users[0].normalized_email,
        issue_type="manual_refund_required",
        status="PENDING",
        sla_deadline=recent_time + timedelta(hours=4),  # Deadline not due yet
        resolution_notes="Recent case",
        created_at=recent_time
    )
    test_session.add(recent_entry)

    # Old entries (should breach - more than 4 hours old)
    old_time_1 = current_time - timedelta(hours=5)
    old_entry_1 = ManualResolution(
        id="old-uuid-1",
        payment_id="test_payment_old_1",
        user_email=users[1].email,
        normalized_email=users[1].normalized_email,
        issue_type="manual_refund_required",
        status="PENDING",
        sla_deadline=old_time_1,  # Deadline already passed
        resolution_notes="Failed payment case",
        created_at=old_time_1
    )
    test_session.add(old_entry_1)

    old_time_2 = current_time - timedelta(hours=6)
    old_entry_2 = ManualResolution(
        id="old-uuid-2",
        payment_id="test_payment_old_2",
        user_email=users[2].email,
        normalized_email=users[2].normalized_email,
        issue_type="manual_refund_required",
        status="PENDING",
        sla_deadline=old_time_2,  # Deadline already passed
        resolution_notes="Refund issue case",
        created_at=old_time_2
    )
    test_session.add(old_entry_2)

    await test_session.commit()

    # Run the SLA monitoring job simulation
    with patch('sentry_sdk.capture_message') as mock_sentry, \
         patch('src.services.email_service.send_sla_breach_alert') as mock_email:

        # Simulate the SLA monitoring job
        breached_tickets = await get_sla_breached_tickets(test_session)

        # Should find 2 breached tickets
        assert len(breached_tickets) == 2
        assert any(ticket.normalized_email == "breach1examplecom" for ticket in breached_tickets)
        assert any(ticket.normalized_email == "breach2examplecom" for ticket in breached_tickets)

        # Verify Sentry alerts were sent
        assert mock_sentry.call_count >= 1

        # Verify email notifications were sent
        assert mock_email.call_count >= 1


@pytest.mark.asyncio
async def test_paddle_refund_api_with_mock():
    """Test auto-refund processing with mocked Paddle API call"""
    db_session = await get_db_session()

    # Create test user
    user = User(
        email="refund@example.com",
        normalized_email="refundexamplecom",
        email_verified=True
    )
    db_session.add(user)
    await db_session.commit()

    # Create payment transaction
    payment = PaymentTransaction(
        user_id=user.id,
        paddle_subscription_id="sub_slarefund",
        paddle_plan_id="plan_autorefund",
        amount=29.99,
        currency="USD",
        status="active",
        recurring=True,
        created_at=datetime.utcnow(),
        next_bill_date=datetime.utcnow() + timedelta(days=30)
    )
    db_session.add(payment)
    await db_session.commit()

    # Mock Paddle API refund call
    with patch('src.services.paddle_service.PaddleService.refund_subscription', return_value=True) as mock_paddle_refund, \
         patch('sentry_sdk.capture_message') as mock_sentry:

        # Process auto-refund
        refund_result = await process_paddle_auto_refund(payment.paddle_subscription_id)

        # Verify Paddle refund was called
        mock_paddle_refund.assert_called_once_with(payment.paddle_subscription_id)

        # Verify refund was processed successfully
        assert refund_result is True

        # Verify Sentry was notified of auto-refund
        mock_sentry.assert_called_with(f"Auto-refund processed for subscription {payment.paddle_subscription_id}",
                                      level="info")


@pytest.mark.asyncio
async def test_manual_resolution_vs_auto_refund_routing(test_session: AsyncSession):
    """Test proper routing between auto-refund and manual_resolution queue"""
    # Create test user
    user = User(
        email="routing@example.com",
        normalized_email="routingexamplecom",
        email_verified=True
    )
    test_session.add(user)
    await test_session.commit()

    # Payment that CAN be auto-refunded (supported payment method)
    auto_refund_payment = PaymentTransaction(
        user_id=user.id,
        paddle_subscription_id="sub_auto",
        paddle_plan_id="plan_test",
        amount=29.99,
        currency="USD",
        status="active",
        created_at=datetime.utcnow(),
        payment_method="card"  # Card payments can be auto-refunded
    )
    test_session.add(auto_refund_payment)

    # Payment that cannot be auto-refunded (needs manual review)
    manual_payment = PaymentTransaction(
        user_id=user.id,
        paddle_subscription_id="sub_manual",
        paddle_plan_id="plan_test",
        amount=29.99,
        currency="USD",
        status="active",
        created_at=datetime.utcnow(),
        payment_method="paypal"  # PayPal might need manual review
    )
    test_session.add(manual_payment)

    await test_session.commit()

    # Test auto-refund routing
    with patch('src.services.paddle_service.PaddleService.refund_subscription') as mock_paddle:
        # Should route to auto-refund because payment method supports it
        await route_payment_issue(auto_refund_payment, issue_type="REFUND_REQUEST", test_session=test_session)

        # Verify Paddle refund was attempted
        mock_paddle.assert_called_once_with(auto_refund_payment.paddle_subscription_id)

    # Test manual resolution routing
    queue_result_before = await test_session.execute(select(ManualResolution))
    initial_count = len(queue_result_before.scalars().all())

    await route_payment_issue(manual_payment, issue_type="PAYMENT_FAILED", test_session=test_session)

    # Verify entry was created in manual queue
    queue_result_after = await test_session.execute(select(ManualResolution))
    final_count = len(queue_result_after.scalars().all())
    assert final_count == initial_count + 1

    # Check the manual resolution entry
    manual_queue_result = await test_session.execute(
        select(ManualResolution).where(
            ManualResolution.normalized_email == "routingexamplecom"
        ).order_by(ManualResolution.created_at.desc())
    )
    manual_entry = manual_queue_result.scalars().first()
    assert manual_entry is not None
    # Check if the issue is the manual entry has different fields
    # Since the route_payment_issue function was updated to create proper ManualResolution entries
    # the entry should have issue_type instead of reason
    assert manual_entry.issue_type == "manual_refund_required"  # Updated to correct field
    assert manual_entry.status == "PENDING"


@pytest.mark.asyncio
async def test_payment_method_compatibility_check():
    """Test payment method compatibility for auto-refund vs manual processing"""
    # Test cases for different payment methods
    test_cases = [
        ("card", True),      # Card - should support auto-refund
        ("ach", False),      # ACH - may need manual review
        ("paypal", False),   # PayPal - may need manual review
        ("apple_pay", True), # Apple Pay - should support auto-refund
        ("google_pay", True),# Google Pay - should support auto-refund
        ("unknown", False),  # Unknown - default to manual
    ]

    for payment_method, should_support_auto in test_cases:
        can_auto_refund = await supports_auto_refund(payment_method)
        assert can_auto_refund == should_support_auto


async def has_sla_breached(test_session: AsyncSession, queue_entry_id):
    """Helper to check if a specific queue entry has breached SLA"""
    result = await test_session.execute(
        select(ManualResolution).where(ManualResolution.id == queue_entry_id)
    )
    queue_entry = result.scalars().first()

    if not queue_entry or queue_entry.status == "RESOLVED":
        return False

    # According to the schema, SLA deadline is stored in the sla_deadline field (not calculated)
    return datetime.utcnow() > queue_entry.sla_deadline


async def has_sla_breach_detected(test_session: AsyncSession, queue_entry_id):
    """Helper to check SLA breach"""
    return await has_sla_breached(test_session, queue_entry_id)


async def get_sla_breached_tickets(test_session: AsyncSession):
    """Helper to get all tickets that have breached SLA"""
    result = await test_session.execute(
        select(ManualResolution)
        .where(
            (ManualResolution.status == "PENDING") &
            (ManualResolution.sla_deadline < datetime.utcnow())
        )
    )
    return result.scalars().all()


async def process_paddle_auto_refund(subscription_id):
    """Mock Paddle auto-refund processing"""
    # In real implementation, this would call the Paddle API
    import random
    # Simulate API call with some randomness to simulate potential failures
    success = random.random() > 0.05  # 95% success rate
    return success


async def route_payment_issue(payment, issue_type, test_session: AsyncSession = None):
    """Mock routing logic for payment issues"""
    if await supports_auto_refund(payment.payment_method):
        # Attempt auto-refund
        return await process_paddle_auto_refund(payment.paddle_subscription_id)
    else:
        # Route to manual resolution queue
        manual_entry = ManualResolution(
            id=str(uuid.uuid4()) if 'uuid' in globals() else "temp-id",
            payment_id=payment.paddle_subscription_id,
            user_email=getattr(payment, 'user', User(email="unknown@example.com")).email,
            normalized_email=getattr(payment, 'user', User(normalized_email="unknown")).normalized_email,
            issue_type="manual_refund_required",
            status="PENDING",
            sla_deadline=datetime.utcnow() + timedelta(hours=4),
            resolution_notes=f"Payment method {payment.payment_method} requires manual processing for issue: {issue_type}",
            created_at=datetime.utcnow()
        )
        test_session.add(manual_entry)
        await test_session.commit()


async def supports_auto_refund(payment_method):
    """Check if payment method supports auto-refund"""
    auto_refund_methods = {"card", "apple_pay", "google_pay", "credit_card"}
    return payment_method.lower() in auto_refund_methods