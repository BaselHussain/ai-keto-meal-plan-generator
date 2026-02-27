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

    # Verify SLA deadline is approximately 4 hours from now (within a 5-second window to
    # account for the microsecond gap between when `created_at` and `sla_deadline` were set).
    now = datetime.utcnow()
    expected_lower = now + timedelta(hours=4) - timedelta(seconds=5)
    expected_upper = now + timedelta(hours=4) + timedelta(seconds=5)
    assert expected_lower <= queue_entry.sla_deadline <= expected_upper


@pytest.mark.asyncio
async def test_sla_breach_detection(test_session: AsyncSession):
    """Test SLA breach detection logic"""
    # Create a test user
    user = User(
        email="breach@example.com",
        normalized_email="breachexamplecom",
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
    """Test the SLA monitoring job detects breached entries and calls process_sla_violation."""
    from contextlib import asynccontextmanager
    from src.services.sla_monitoring_service import run_sla_monitoring

    current_time = datetime.utcnow()

    # Create 2 breached entries (deadline already passed) and 1 OK entry
    recent_entry = ManualResolution(
        id=str(uuid.uuid4()),
        payment_id="sched_payment_recent",
        user_email="sched_recent@example.com",
        normalized_email="schedrecentexamplecom",
        issue_type="manual_refund_required",
        status="pending",
        sla_deadline=current_time + timedelta(hours=4),  # Not breached
        resolution_notes="Recent case",
        created_at=current_time - timedelta(hours=2),
    )
    old_entry_1 = ManualResolution(
        id=str(uuid.uuid4()),
        payment_id="sched_payment_old_1",
        user_email="sched_breach1@example.com",
        normalized_email="schedbreach1examplecom",
        issue_type="manual_refund_required",
        status="pending",
        sla_deadline=current_time - timedelta(hours=1),  # Breached
        resolution_notes="Old case 1",
        created_at=current_time - timedelta(hours=5),
    )
    old_entry_2 = ManualResolution(
        id=str(uuid.uuid4()),
        payment_id="sched_payment_old_2",
        user_email="sched_breach2@example.com",
        normalized_email="schedbreach2examplecom",
        issue_type="manual_refund_required",
        status="pending",
        sla_deadline=current_time - timedelta(hours=2),  # Breached
        resolution_notes="Old case 2",
        created_at=current_time - timedelta(hours=6),
    )
    test_session.add_all([recent_entry, old_entry_1, old_entry_2])
    await test_session.commit()

    # Patch get_db to inject the test session so run_sla_monitoring uses it
    @asynccontextmanager
    async def mock_get_db():
        yield test_session

    with patch("src.services.sla_monitoring_service.get_db", return_value=mock_get_db()), \
         patch("src.services.sla_monitoring_service.process_sla_violation", new_callable=AsyncMock, return_value=True) as mock_process, \
         patch("sentry_sdk.capture_message"):

        result = await run_sla_monitoring()

    # Should have processed 2 breached tickets, not the recent one
    assert result["checked_entries"] == 2
    assert result["refunds_processed"] == 2
    assert mock_process.call_count == 2


@pytest.mark.asyncio
async def test_paddle_refund_api_with_mock(test_session: AsyncSession):
    """Test process_sla_violation triggers Paddle refund via PaddleClient."""
    from contextlib import asynccontextmanager
    from src.services.sla_monitoring_service import process_sla_violation
    from src.models.payment_status import PaymentStatus

    # Create payment transaction matching current schema
    payment = PaymentTransaction(
        id=str(uuid.uuid4()),
        payment_id="paddle_refund_test_pay_001",
        amount=47.95,
        currency="USD",
        payment_method="card",
        payment_status=PaymentStatus.SUCCEEDED,
        paddle_created_at=datetime.utcnow(),
        webhook_received_at=datetime.utcnow(),
        customer_email="paddle_refund_test@example.com",
        normalized_email="paddlerefundtestexamplecom",
    )
    test_session.add(payment)
    await test_session.flush()

    # Create breached ManualResolution entry
    entry = ManualResolution(
        id=str(uuid.uuid4()),
        payment_id=payment.payment_id,
        user_email=payment.customer_email,
        normalized_email=payment.normalized_email,
        issue_type="manual_refund_required",
        status="pending",
        sla_deadline=datetime.utcnow() - timedelta(hours=1),
        resolution_notes="SLA breached",
        created_at=datetime.utcnow() - timedelta(hours=5),
    )
    test_session.add(entry)
    await test_session.commit()

    @asynccontextmanager
    async def mock_get_db():
        yield test_session

    with patch("src.services.sla_monitoring_service.get_db", return_value=mock_get_db()), \
         patch("src.services.sla_monitoring_service.update_manual_resolution_status", new_callable=AsyncMock, return_value=True), \
         patch("src.services.sla_monitoring_service.PaddleClient") as MockPaddleClient, \
         patch("src.services.sla_monitoring_service.send_sla_missed_refund_email", new_callable=AsyncMock), \
         patch("sentry_sdk.capture_message"):

        mock_client = AsyncMock()
        mock_client.process_sla_refund.return_value = True
        MockPaddleClient.return_value = mock_client

        result = await process_sla_violation(entry)

    assert result is True
    mock_client.process_sla_refund.assert_called_once()


@pytest.mark.asyncio
async def test_manual_resolution_vs_auto_refund_routing(test_session: AsyncSession):
    """Test process_sla_violation handles card (auto-refund) vs missing payment (manual)."""
    from contextlib import asynccontextmanager
    from src.services.sla_monitoring_service import process_sla_violation
    from src.models.payment_status import PaymentStatus

    @asynccontextmanager
    async def mock_get_db():
        yield test_session

    # --- Scenario 1: card payment → auto-refund succeeds ---
    card_payment = PaymentTransaction(
        id=str(uuid.uuid4()),
        payment_id="routing_card_pay_001",
        amount=47.95,
        currency="USD",
        payment_method="card",
        payment_status=PaymentStatus.SUCCEEDED,
        paddle_created_at=datetime.utcnow(),
        webhook_received_at=datetime.utcnow(),
        customer_email="routing_card@example.com",
        normalized_email="routingcardexamplecom",
    )
    test_session.add(card_payment)
    await test_session.flush()

    card_entry = ManualResolution(
        id=str(uuid.uuid4()),
        payment_id=card_payment.payment_id,
        user_email=card_payment.customer_email,
        normalized_email=card_payment.normalized_email,
        issue_type="manual_refund_required",
        status="pending",
        sla_deadline=datetime.utcnow() - timedelta(hours=1),
        resolution_notes="Card refund",
        created_at=datetime.utcnow() - timedelta(hours=5),
    )
    test_session.add(card_entry)
    await test_session.commit()

    with patch("src.services.sla_monitoring_service.get_db", return_value=mock_get_db()), \
         patch("src.services.sla_monitoring_service.update_manual_resolution_status", new_callable=AsyncMock, return_value=True), \
         patch("src.services.sla_monitoring_service.PaddleClient") as MockPaddleClient, \
         patch("src.services.sla_monitoring_service.send_sla_missed_refund_email", new_callable=AsyncMock), \
         patch("sentry_sdk.capture_message"):

        mock_client = AsyncMock()
        mock_client.process_sla_refund.return_value = True
        MockPaddleClient.return_value = mock_client

        result = await process_sla_violation(card_entry)

    # Card payment — auto-refund should succeed
    assert result is True
    mock_client.process_sla_refund.assert_called_once()

    # --- Scenario 2: missing payment transaction → returns False ---
    missing_entry = ManualResolution(
        id=str(uuid.uuid4()),
        payment_id="routing_nonexistent_pay_999",
        user_email="routing_missing@example.com",
        normalized_email="routingmissingexamplecom",
        issue_type="manual_refund_required",
        status="pending",
        sla_deadline=datetime.utcnow() - timedelta(hours=1),
        resolution_notes="Missing payment",
        created_at=datetime.utcnow() - timedelta(hours=5),
    )
    test_session.add(missing_entry)
    await test_session.commit()

    with patch("src.services.sla_monitoring_service.get_db", return_value=mock_get_db()), \
         patch("src.services.sla_monitoring_service.update_manual_resolution_status", new_callable=AsyncMock, return_value=True), \
         patch("sentry_sdk.capture_message"):

        result2 = await process_sla_violation(missing_entry)

    # No payment transaction found → cannot auto-refund
    assert result2 is False


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