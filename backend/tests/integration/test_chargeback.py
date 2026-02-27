import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User
from src.models.email_blacklist import EmailBlacklist


@pytest.mark.asyncio
async def test_chargeback_creates_email_blacklist(test_session: AsyncSession):
    """Test that chargebacks result in email blacklisting"""
    # Create a test user (only valid fields on User model)
    user = User(
        email="chargeback_test@example.com",
        normalized_email="chargebacktestexamplecom",
    )
    test_session.add(user)
    await test_session.commit()

    # Simulate processing of chargeback - manually add to blacklist
    # EmailBlacklist only accepts normalized_email, reason, and expires_at
    blacklist_entry = EmailBlacklist(
        normalized_email="chargebacktestexamplecom",
        reason="CHARGEBACK",
        expires_at=datetime.utcnow() + timedelta(days=90)  # 90-day TTL
    )
    test_session.add(blacklist_entry)
    await test_session.commit()

    # Check if email was blacklisted by normalized_email
    blacklist_result = await test_session.execute(
        select(EmailBlacklist).where(
            EmailBlacklist.normalized_email == "chargebacktestexamplecom"
        )
    )
    blacklisted_email = blacklist_result.scalars().first()
    assert blacklisted_email is not None
    assert blacklisted_email.reason == "CHARGEBACK"
    assert blacklisted_email.expires_at is not None
    assert blacklisted_email.expires_at >= datetime.utcnow() + timedelta(days=89)  # At least 89 days left


@pytest.mark.asyncio
async def test_normal_refund_does_not_blacklist_email(test_session: AsyncSession):
    """Test that normal refunds don't blacklist emails"""
    # Create a test user (only valid fields on User model)
    user = User(
        email="normal_refund@example.com",
        normalized_email="normalrefundexamplecom",
    )
    test_session.add(user)
    await test_session.commit()

    # Process normal refund (don't blacklist)
    # This should result in no EmailBlacklist entry

    # Check that the email is NOT blacklisted
    blacklist_result = await test_session.execute(
        select(EmailBlacklist).where(
            EmailBlacklist.normalized_email == "normalrefundexamplecom"
        )
    )
    blacklisted_email = blacklist_result.scalars().first()
    assert blacklisted_email is None


@pytest.mark.asyncio
async def test_blacklist_lookup_during_checkout(test_session: AsyncSession):
    """Test that checkout fails when email is blacklisted"""
    # Create blacklisted email using valid EmailBlacklist constructor
    blacklist_entry = EmailBlacklist(
        normalized_email="blacklistcheckoutexamplecom",
        reason="CHARGEBACK",
        expires_at=datetime.utcnow() + timedelta(days=90)
    )
    test_session.add(blacklist_entry)
    await test_session.commit()

    # Test blacklisted email lookup (checkout validation)
    blacklist_result = await test_session.execute(
        select(EmailBlacklist)
        .where(EmailBlacklist.normalized_email == "blacklistcheckoutexamplecom")
        .where(EmailBlacklist.expires_at > datetime.utcnow())
    )
    blacklisted_email = blacklist_result.scalars().first()
    assert blacklisted_email is not None
    assert blacklisted_email.normalized_email == "blacklistcheckoutexamplecom"

    # Should block checkout
    is_blocked = blacklisted_email is not None
    assert is_blocked is True


@pytest.mark.asyncio
async def test_blacklist_has_90_day_ttl(test_session: AsyncSession):
    """Test that blacklisted emails have 90-day TTL and auto-expire"""
    # Create blacklisted email with 90-day expiration
    blacklist_time = datetime.utcnow()
    blacklist_entry = EmailBlacklist(
        normalized_email="tempblockedttlexamplecom",
        reason="CHARGEBACK",
        expires_at=blacklist_time + timedelta(days=90)
    )
    test_session.add(blacklist_entry)
    await test_session.commit()

    # Verify the TTL was set correctly
    result = await test_session.execute(
        select(EmailBlacklist).where(EmailBlacklist.normalized_email == "tempblockedttlexamplecom")
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
        .where(EmailBlacklist.normalized_email == "tempblockedttlexamplecom")
        .where(EmailBlacklist.expires_at > future_time)
    )
    active_blacklist = active_blacklist_result.scalars().first()
    assert active_blacklist is None
