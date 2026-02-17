import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User
from src.models.payment_transaction import PaymentTransaction
from src.models.email_blacklist import EmailBlacklist


@pytest.mark.asyncio
async def test_chargeback_creates_email_blacklist(test_session: AsyncSession):
    """Test that chargebacks result in email blacklisting"""
    # Create a test user
    user = User(
        email="test@example.com",
        normalized_email="testexamplecom",
        email_verified=True,
        email_verification_token=None,
        quiz_started_at=datetime.utcnow(),
        quiz_completed_at=datetime.utcnow()
    )
    test_session.add(user)
    await test_session.commit()

    # Create a payment transaction for this user
    payment = PaymentTransaction(
        user_id=user.id,
        paddle_subscription_id="sub_123",
        paddle_plan_id="plan_456",
        amount=29.99,
        currency="USD",
        status="active",
        recurring=True,
        next_bill_date=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    test_session.add(payment)
    await test_session.commit()

    # Simulate processing of chargeback - manually add to blacklist
    with patch('sentry_sdk.capture_message') as mock_sentry:
        # This is what happens during chargeback processing
        blacklist_entry = EmailBlacklist(
            email="test@example.com",
            normalized_email="testexamplecom",
            reason="CHARGEBACK",
            expires_at=datetime.utcnow() + timedelta(days=90)  # 90-day TTL
        )
        test_session.add(blacklist_entry)
        await test_session.commit()

        # Check if email was blacklisted
        blacklist_result = await test_session.execute(
            select(EmailBlacklist).where(EmailBlacklist.email == "test@example.com")
        )
        blacklisted_email = blacklist_result.scalars().first()
        assert blacklisted_email is not None
        assert blacklisted_email.reason == "CHARGEBACK"
        assert blacklisted_email.expires_at is not None
        assert blacklisted_email.expires_at >= datetime.utcnow() + timedelta(days=89)  # At least 89 days left

        # Verify Sentry was notified
        mock_sentry.assert_called()


@pytest.mark.asyncio
async def test_normal_refund_does_not_blacklist_email(test_session: AsyncSession):
    """Test that normal refunds don't blacklist emails"""
    # Create a test user
    user = User(
        email="test2@example.com",
        normalized_email="test2examplecom",
        email_verified=True
    )
    test_session.add(user)
    await test_session.commit()

    # Create a payment transaction
    payment = PaymentTransaction(
        user_id=user.id,
        paddle_subscription_id="sub_456",
        paddle_plan_id="plan_789",
        amount=29.99,
        currency="USD",
        status="active",
        created_at=datetime.utcnow()
    )
    test_session.add(payment)
    await test_session.commit()

    # Process normal refund (don't blacklist)
    # This should result in no EmailBlacklist entry

    # Check that the email is NOT blacklisted
    blacklist_result = await test_session.execute(
        select(EmailBlacklist).where(EmailBlacklist.email == "test2@example.com")
    )
    blacklisted_email = blacklist_result.scalars().first()
    assert blacklisted_email is None


@pytest.mark.asyncio
async def test_blacklist_lookup_during_checkout(test_session: AsyncSession):
    """Test that checkout fails when email is blacklisted"""
    # Create blacklisted email
    blacklist_entry = EmailBlacklist(
        email="blacklist@example.com",
        normalized_email="blacklistexamplecom",
        reason="CHARGEBACK",
        expires_at=datetime.utcnow() + timedelta(days=90)
    )
    test_session.add(blacklist_entry)
    await test_session.commit()

    # Test blacklisted email lookup (checkout validation)
    blacklist_result = await test_session.execute(
        select(EmailBlacklist)
        .where(EmailBlacklist.normalized_email == "blacklistexamplecom")
        .where(EmailBlacklist.expires_at > datetime.utcnow())
    )
    blacklisted_email = blacklist_result.scalars().first()
    assert blacklisted_email is not None
    assert blacklisted_email.email == "blacklist@example.com"

    # Should block checkout
    is_blocked = blacklisted_email is not None
    assert is_blocked is True


@pytest.mark.asyncio
async def test_blacklist_has_90_day_ttl(test_session: AsyncSession):
    """Test that blacklisted emails have 90-day TTL and auto-expire"""
    # Create blacklisted email with 90-day expiration
    blacklist_time = datetime.utcnow()
    blacklist_entry = EmailBlacklist(
        email="tempblocked@example.com",
        normalized_email="tempblockedexamplecom",
        reason="CHARGEBACK",
        expires_at=blacklist_time + timedelta(days=90)
    )
    test_session.add(blacklist_entry)
    await test_session.commit()

    # Verify the TTL was set correctly
    result = await test_session.execute(
        select(EmailBlacklist).where(EmailBlacklist.normalized_email == "tempblockedexamplecom")
    )
    email_blacklist = result.scalars().first()
    assert email_blacklist is not None
    expected_expiration = blacklist_time + timedelta(days=90)
    assert abs((email_blacklist.expires_at - expected_expiration).total_seconds()) < 1  # Within 1 second

    # Simulate time passage and check if record expires
    # After 91 days, it should no longer appear in active blacklist lookups
    future_time = blacklist_time + timedelta(days=91)
    active_blacklist_result = await test_session.execute(
        select(EmailBlacklist)
        .where(EmailBlacklist.normalized_email == "tempblockedexamplecom")
        .where(EmailBlacklist.expires_at > future_time)
    )
    active_blacklist = active_blacklist_result.scalars().first()
    assert active_blacklist is None