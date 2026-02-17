"""
Refund Processing Service
Handles refund-related operations including payment status updates,
refund count tracking, and refund pattern detection for fraud prevention.

Process Refund Request (T120-T123):
- Updates payment_transactions.payment_status to 'refunded' on refund webhook
- Adds refund counts to meal_plans table when refund webhooks are received
- Implements refund pattern detection (≥2 refunds in 90d triggers manual review)
- Creates manual review flag in manual_resolution queue for 3rd purchase
- Blocks users from making purchases for 30 days if ≥3 refunds in 90 days

File: backend/src/services/refund_service.py
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import sentry_sdk

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.models.manual_resolution import IssueType, ManualResolution
from src.models.meal_plan import MealPlan
from src.models.payment_transaction import PaymentTransaction, PaymentStatus
from src.models.quiz_response import QuizResponse
from src.lib.database import get_db

logger = logging.getLogger(__name__)


async def process_refund(event_data: Dict[str, Any]) -> None:
    """
    Process refund webhook event by updating payment status and refund counts.

    This function handles the payment.refunded webhook event by:
    1. Finding the payment transaction by payment_id
    2. Updating payment_transaction.payment_status to 'refunded'
    3. Updating the associated meal plan's refund_count
    4. Running refund pattern detection to identify suspicious users
    5. Creating manual review flags when needed
    6. Blocking users based on refund count thresholds

    Args:
        event_data: Paddle webhook event data containing refund information

    Reference:
        T120A: Update payment_transactions.payment_status to 'refunded' on refund webhook
        T120B: Update meal_plans refund_count
        T121: Implement refund pattern detection (flag 2nd+ refund)
        T122: Create manual review flag in manual_resolution queue
        T123: Implement 30-day purchase block for high-refund customers
    """
    payment_id = event_data.get("id")
    if not payment_id:
        logger.error("Refund event missing payment_id")
        sentry_sdk.capture_message("Refund event missing payment_id")
        return

    # Extract customer email from event data
    customer_email = None
    if "customer_email" in event_data:
        customer_email = event_data["customer_email"]
    elif "data" in event_data and "customer_email" in event_data["data"]:
        customer_email = event_data["data"]["customer_email"]

    if not customer_email:
        logger.error(f"Refund event missing customer_email for payment {payment_id}")
        sentry_sdk.capture_message(f"Refund event missing customer_email for payment {payment_id}")
        return

    from src.lib.email_utils import normalize_email
    normalized_email = normalize_email(customer_email)

    async with get_db() as session:
        try:
            # Find the payment transaction
            result = await session.execute(
                select(PaymentTransaction).where(
                    PaymentTransaction.payment_id == payment_id
                )
            )
            payment_transaction = result.scalar_one_or_none()

            if not payment_transaction:
                logger.error(f"Payment transaction not found for refund: {payment_id}")
                return

            # Update payment transaction status to "refunded" (T120A)
            payment_transaction.payment_status = PaymentStatus.REFUNDED
            payment_transaction.updated_at = datetime.utcnow()

            # Find the related meal plan to update refund count (T120B)
            meal_plan = payment_transaction.meal_plan
            if meal_plan:
                # Increment the refund count on the meal plan
                meal_plan.refund_count += 1
                meal_plan.status = "refunded"  # Update status to refunded as well - keeping as string to match model enum
                meal_plan.updated_at = datetime.utcnow()

                logger.info(f"Updated refund count for meal plan {meal_plan.id} to {meal_plan.refund_count}")

                # Check for refund pattern (T121 - flag if 2 or more refunds in 90 days)
                total_refunds = await get_refund_count_in_period(
                    session, normalized_email, days=90
                )

                # Check if this is the 3rd or more refund (≥2 refunds already + current one = 3+ total)
                if total_refunds >= 3:
                    # This triggers the 30-day purchase block (T123)
                    logger.info(f"User {normalized_email} has {total_refunds} refunds in 90 days, implementing purchase block")
                    await implement_purchase_block(session, normalized_email, total_refunds)

                # Check if this is the 2nd or more refund to decide on manual review (T121, T122)
                elif total_refunds >= 2:
                    # Create manual review flag for pattern detection (T122)
                    if total_refunds == 2:  # Only create flag for 2nd refund (first suspicious pattern)
                        await create_manual_refund_review(session, payment_transaction, meal_plan)

            else:
                # Find meal plan by normalized_email if payment_transaction doesn't have the relationship
                logger.warning(f"No meal plan found via payment transaction for {payment_id}, searching by email")

                result = await session.execute(
                    select(MealPlan).where(
                        MealPlan.normalized_email == normalized_email
                    ).order_by(MealPlan.created_at.desc())  # Get most recent meal plan
                )
                meal_plan = result.scalar_one_or_none()

                if meal_plan:
                    meal_plan.refund_count += 1
                    meal_plan.status = "refunded"
                    meal_plan.updated_at = datetime.utcnow()

                    logger.info(f"Updated refund count for meal plan {meal_plan.id} to {meal_plan.refund_count}")

                    # Check for refund patterns as before
                    total_refunds = await get_refund_count_in_period(
                        session, normalized_email, days=90
                    )

                    if total_refunds >= 3:
                        await implement_purchase_block(session, normalized_email, total_refunds)
                    elif total_refunds >= 2:
                        if total_refunds == 2:
                            await create_manual_refund_review(session, payment_transaction, meal_plan)

            await session.commit()
            logger.info(f"Successfully processed refund for payment {payment_id}")

        except Exception as e:
            logger.error(f"Error processing refund for payment {payment_id}: {e}")
            sentry_sdk.capture_exception(e)
            await session.rollback()


async def get_refund_count_in_period(session, normalized_email: str, days: int = 90) -> int:
    """
    Get count of refunded payments for an email in the specified time period.

    Args:
        session: Async database session
        normalized_email: Normalized customer email
        days: Number of days to look back

    Returns:
        int: Number of refunded payments in the specified period
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Count meal plans that have been refunded in the time period
    result = await session.execute(
        select(MealPlan)
        .where(
            (MealPlan.normalized_email == normalized_email) &
            (MealPlan.refund_count > 0) &
            (MealPlan.created_at >= cutoff_date)
        )
    )
    meal_plans = result.scalars().all()

    total_refunds = sum([mp.refund_count for mp in meal_plans])
    return total_refunds


async def create_manual_refund_review(
    session,
    payment_transaction: PaymentTransaction,
    meal_plan: MealPlan
) -> None:
    """
    Create a manual review flag in the manual_resolution queue for suspicious refund patterns.

    Args:
        session: Async database session
        payment_transaction: The refunded payment transaction
        meal_plan: The related meal plan
    """
    # First check if there's already a refund pattern manual resolution for this customer
    # to avoid creating duplicate entries
    result = await session.execute(
        select(ManualResolution).where(
            (ManualResolution.normalized_email == meal_plan.normalized_email) &
            (ManualResolution.issue_type == IssueType.MANUAL_REFUND_REQUIRED) &
            (ManualResolution.status == "pending")
        )
    )
    existing_review = result.scalar_one_or_none()

    if existing_review:
        logger.info(f"Manual review already exists for {meal_plan.normalized_email}, skipping duplicate")
        return

    # Create manual resolution entry for refund pattern (T122)
    manual_resolution = ManualResolution(
        payment_id=payment_transaction.payment_id,
        user_email=payment_transaction.customer_email,
        normalized_email=meal_plan.normalized_email,
        issue_type=IssueType.MANUAL_REFUND_REQUIRED,  # Use existing enum
        status="pending",
        sla_deadline=datetime.utcnow() + timedelta(hours=4),
        description=f"Refund pattern detected: 2+ refunds in 90 days for {meal_plan.normalized_email}. "
                   f"Payment {payment_transaction.payment_id} refunded. "
                   f"Current refund count across period: needs investigation.",
        created_at=datetime.utcnow()
    )

    session.add(manual_resolution)
    await session.commit()

    logger.info(f"Created manual review entry for refund pattern: {meal_plan.normalized_email}")
    sentry_sdk.capture_message(
        f"Manual review created for refund pattern: {meal_plan.normalized_email}",
        level="info",
        extra={
            "email": meal_plan.normalized_email,
            "payment_id": payment_transaction.payment_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


async def implement_purchase_block(session, normalized_email: str, refund_count: int) -> None:
    """
    Implement 30-day purchase block for users with ≥3 refunds in 90 days (T123).

    Args:
        session: Async database session
        normalized_email: User's normalized email
        refund_count: Total refund count
    """
    from src.models.email_blacklist import EmailBlacklist

    # Add to blacklist with 30-day TTL as a purchase block (T123)
    result = await session.execute(
        select(EmailBlacklist).where(
            EmailBlacklist.normalized_email == normalized_email
        )
    )
    existing_block = result.scalar_one_or_none()

    if existing_block:
        # Update existing block (might already be blacklisted for chargeback)
        existing_block.expires_at = datetime.utcnow() + timedelta(days=30)
        existing_block.reason = f"PURCHASE_BLOCK_REFUND_{refund_count}"
        existing_block.updated_at = datetime.utcnow()
    else:
        # Create new purchase block entry
        purchase_block = EmailBlacklist(
            normalized_email=normalized_email,
            reason=f"PURCHASE_BLOCK_REFUND_{refund_count}",
            expires_at=datetime.utcnow() + timedelta(days=30),
            created_at=datetime.utcnow(),
        )
        session.add(purchase_block)

    await session.commit()
    logger.info(f"Applied 30-day purchase block for {normalized_email} with {refund_count} refunds")

    # Log to Sentry for monitoring
    sentry_sdk.capture_message(
        f"30-day purchase block applied for high-refund customer",
        level="info",
        extra={
            "email": normalized_email,
            "refund_count": refund_count,
            "block_duration_days": 30,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )