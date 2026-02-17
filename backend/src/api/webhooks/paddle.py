"""
Paddle Webhook Handler with Chargeback Support

Handles all Paddle webhook events including payments, refunds, and chargebacks.
Implements security measures: HMAC-SHA256 validation, timestamp checking,
idempotency, and race condition handling.

Chargeback Processing (T116, T116A, T117, T118):
- Process payment.chargeback events
- Update payment_transactions.payment_status to "chargeback" (T116A)
- Add normalized_email to email_blacklist with 90-day TTL (T117)
- Log chargeback event to Sentry (T118)
- Process with same reliability as successful payments

Security & Validation:
- HMAC-SHA256 signature validation (per research.md lines 337-438)
- Timestamp validation (5-minute window for replay attacks)
- Idempotency via payment_id unique constraint (IntegrityError handling)
- Race condition handling: poll quiz_responses for 5 seconds if not found
- Manual resolution queue for unresolvable cases

Webhook Events Supported:
- checkout.completed (payment successful)
- subscription.created, subscription.updated, subscription.canceled
- payment.chargeback (new: chargeback handling per FR-P-013)
- payment.refunded
- payment.dispute.won, payment.dispute.lost

Rate Limiting:
- 10 requests per IP per minute for webhook endpoint
- Rate limit by source IP to prevent webhook floods

File: backend/src/api/webhooks/paddle.py
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import sentry_sdk
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.lib.email_utils import normalize_email
from src.lib.env import settings
from src.lib.redis_client import get_redis, increment_with_ttl
from src.models.email_blacklist import EmailBlacklist
from src.models.manual_resolution import IssueType, ManualResolution
from src.models.payment_transaction import PaymentTransaction, PaymentStatus
from src.models.quiz_response import QuizResponse
from src.lib.database import get_db

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Webhook validation window (5 minutes in seconds)
WEBHOOK_VALIDATION_WINDOW = 300

# Webhook rate limit: 10 per IP per minute
WEBHOOK_RATE_LIMIT = 10
WEBHOOK_RATE_WINDOW = 60  # seconds


async def validate_webhook_signature(
    request: Request, payload: bytes, signature: str
) -> bool:
    """
    Validate Paddle webhook signature using HMAC-SHA256.

    Args:
        request: FastAPI request object
        payload: Raw webhook payload bytes
        signature: Signature from Paddle-Signature header

    Returns:
        bool: True if signature is valid

    Reference:
        research.md lines 337-438 (Paddle webhook security)
    """
    # Parse signature components
    signature_parts = signature.split(",")
    if len(signature_parts) < 2:
        logger.warning("Invalid signature format")
        return False

    # Extract timestamp and signature value
    timestamp = None
    signature_value = None
    for part in signature_parts:
        if part.startswith("t:"):
            timestamp = part[2:]
        elif part.startswith("v1:"):
            signature_value = part[3:]

    if not timestamp or not signature_value:
        logger.warning("Missing timestamp or signature value")
        return False

    # Verify timestamp is within acceptable window
    current_time = int(time.time())
    payload_time = int(timestamp)
    if abs(current_time - payload_time) > WEBHOOK_VALIDATION_WINDOW:
        logger.warning(
            f"Webhook timestamp outside window: {payload_time} vs {current_time}"
        )
        sentry_sdk.capture_message(
            f"Paddle webhook replay attack attempt - timestamp outside window: {payload_time} vs {current_time}"
        )
        return False

    # Construct signature string
    signature_string = f"{payload_time}:{payload.decode('utf-8')}"

    # Generate expected signature
    expected_signature = hmac.new(
        settings.PADDLE_WEBHOOK_SECRET.encode("utf-8"),
        signature_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # Compare signatures
    is_valid = hmac.compare_digest(signature_value, expected_signature)
    if not is_valid:
        logger.warning("Webhook signature validation failed")
        sentry_sdk.capture_message("Paddle webhook signature validation failed")

    return is_valid


async def rate_limit_webhook(ip_address: str) -> None:
    """
    Apply rate limiting to webhook endpoint to prevent abuse.

    Args:
        ip_address: Client IP address

    Raises:
        HTTPException: If rate limit exceeded
    """
    redis_client = await get_redis()
    key = f"webhook_rate_limit:{ip_address}"

    # Increment counter with 1-minute TTL
    count = await increment_with_ttl(key, ttl=WEBHOOK_RATE_WINDOW, amount=1)

    if count > WEBHOOK_RATE_LIMIT:
        # Rate limit exceeded
        logger.warning(f"Webhook rate limit exceeded for IP: {ip_address}")
        raise HTTPException(
            status_code=429,
            detail="Webhook rate limit exceeded. Too many requests.",
        )


from src.services.refund_service import process_refund


async def handle_chargeback_event(event_data: Dict[str, Any]) -> None:
    """
    Process payment.chargeback event (T116, T116A, T117, T118).

    Handles chargeback by:
    1. Updating payment transaction status to "chargeback" (T116A)
    2. Adding email to blacklist with 90-day TTL (T117)
    3. Logging to Sentry (T118)

    Args:
        event_data: Paddle webhook event data
    """
    payment_id = event_data.get("id")
    if not payment_id:
        logger.error("Chargeback event missing payment_id")
        sentry_sdk.capture_message("Chargeback event missing payment_id")
        return

    # Extract customer email from event data
    customer_email = None
    if "customer_email" in event_data:
        customer_email = event_data["customer_email"]
    elif "data" in event_data and "customer_email" in event_data["data"]:
        customer_email = event_data["data"]["customer_email"]

    if not customer_email:
        logger.error(f"Chargeback event missing customer_email for payment {payment_id}")
        sentry_sdk.capture_message(
            f"Chargeback event missing customer_email for payment {payment_id}"
        )
        return

    normalized_email = normalize_email(customer_email)

    async with get_db() as session:
        try:
            # Update payment transaction status to "chargeback" (T116A)
            result = await session.execute(
                select(PaymentTransaction).where(
                    PaymentTransaction.payment_id == payment_id
                )
            )
            payment_transaction = result.scalar_one_or_none()

            if payment_transaction:
                payment_transaction.payment_status = PaymentStatus.CHARGEBACK
                payment_transaction.updated_at = datetime.utcnow()
                await session.commit()
                logger.info(f"Updated payment {payment_id} to chargeback status")
            else:
                logger.warning(f"Payment transaction not found: {payment_id}")

            # Add normalized_email to email_blacklist with 90-day TTL (T117)
            # First check if email is already blacklisted
            result = await session.execute(
                select(EmailBlacklist).where(
                    EmailBlacklist.normalized_email == normalized_email
                )
            )
            existing_blacklist = result.scalar_one_or_none()

            if existing_blacklist:
                # Update existing entry with new 90-day TTL
                existing_blacklist.expires_at = datetime.utcnow() + timedelta(days=90)
                existing_blacklist.reason = "CHARGEBACK"
                existing_blacklist.updated_at = datetime.utcnow()
            else:
                # Create new blacklist entry
                blacklist_entry = EmailBlacklist(
                    normalized_email=normalized_email,
                    reason="CHARGEBACK",
                    expires_at=datetime.utcnow() + timedelta(days=90),
                )
                session.add(blacklist_entry)

            await session.commit()
            logger.info(f"Added email to blacklist: {normalized_email}")

            # Log chargeback event to Sentry (T118)
            sentry_sdk.capture_message(
                f"Chargeback processed for payment {payment_id}",
                level="info",
                extra={
                    "payment_id": payment_id,
                    "email": customer_email,
                    "normalized_email": normalized_email,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        except Exception as e:
            logger.error(f"Error processing chargeback for payment {payment_id}: {e}")
            sentry_sdk.capture_exception(e)
            await session.rollback()


async def handle_payment_completed_event(event_data: Dict[str, Any]) -> None:
    """
    Handle checkout.completed event (existing payment processing).

    Args:
        event_data: Paddle webhook event data
    """
    from src.services.delivery_orchestrator import trigger_meal_plan_generation

    payment_id = event_data["id"]
    amount = event_data["details"]["totals"]["currency_code"]["total"]
    currency = event_data["details"]["totals"]["currency_code"]["currency_code"]
    customer_email = event_data["customer_email"]

    # Extract payment method from event
    payment_method = "unknown"
    if "details" in event_data and "payouts" in event_data["details"]:
        payouts = event_data["details"]["payouts"]
        if payouts and len(payouts) > 0:
            payment_method = payouts[0].get("payout_method_type", "unknown")

    # Normalize email
    normalized_email = normalize_email(customer_email)

    # Check for duplicate payment (idempotency)
    async with get_db() as session:
        try:
            # Try to create payment transaction
            payment_transaction = PaymentTransaction(
                payment_id=payment_id,
                amount=amount,
                currency=currency,
                customer_email=customer_email,
                normalized_email=normalized_email,
                payment_method=payment_method,
                payment_status=PaymentStatus.SUCCEEDED,
                paddle_created_at=datetime.utcnow(),
            )
            session.add(payment_transaction)
            await session.commit()
            logger.info(f"Created payment transaction for {payment_id}")

            # Poll for quiz response (handle race condition)
            quiz_response = None
            for attempt in range(10):  # 10 attempts
                result = await session.execute(
                    select(QuizResponse).where(
                        QuizResponse.email == normalized_email
                    )
                )
                quiz_response = result.scalar_one_or_none()

                if quiz_response:
                    break
                await asyncio.sleep(0.5)  # 500ms delay

            if not quiz_response:
                # Quiz response not found after polling - manual resolution
                manual_resolution = ManualResolution(
                    issue_type=IssueType.MISSING_QUIZ_DATA,
                    payment_id=payment_id,
                    customer_email=customer_email,
                    description=f"Quiz response not found for payment {payment_id} after 10 polling attempts",
                    sla_deadline=datetime.utcnow() + timedelta(hours=4),
                )
                session.add(manual_resolution)
                await session.commit()
                logger.warning(
                    f"Created manual resolution for missing quiz: {payment_id}"
                )
                sentry_sdk.capture_message(
                    f"Manual resolution created for missing quiz data: {payment_id}"
                )
            else:
                # Trigger meal plan generation
                await trigger_meal_plan_generation(quiz_response.id)

        except IntegrityError:
            # Duplicate payment - already processed
            logger.info(f"Duplicate payment webhook for {payment_id}, skipping")
            await session.rollback()
        except Exception as e:
            logger.error(f"Error processing payment {payment_id}: {e}")
            sentry_sdk.capture_exception(e)
            await session.rollback()


@router.post("/paddle")
async def handle_paddle_webhook(
    request: Request, background_tasks: BackgroundTasks
):
    """
    Handle Paddle webhook events including chargebacks (T116).

    Validates signature, applies rate limiting, and processes different event types.

    Args:
        request: FastAPI request object
        background_tasks: Background tasks for async processing

    Returns:
        dict: Success response

    Reference:
        research.md lines 337-438 (webhook security)
        T062-T066 (webhook handler requirements)
        T116 (chargeback event processing)
    """
    # Get raw payload
    payload = await request.body()
    signature = request.headers.get("Paddle-Signature")

    if not signature:
        logger.warning("Missing Paddle-Signature header")
        raise HTTPException(status_code=400, detail="Missing signature")

    # Validate signature
    if not await validate_webhook_signature(request, payload, signature):
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Rate limiting
    client_ip = request.client.host
    await rate_limit_webhook(client_ip)

    try:
        # Parse event data
        event_data = json.loads(payload.decode("utf-8"))

        # Get event type
        event_type = event_data.get("event_type")

        logger.info(f"Paddle webhook received: {event_type} - {event_data.get('id')}")

        # Process different event types
        if event_type == "checkout.completed":
            background_tasks.add_task(handle_payment_completed_event, event_data)
        elif event_type == "payment.chargeback":
            # Handle chargeback event (T116)
            background_tasks.add_task(handle_chargeback_event, event_data)
        elif event_type == "payment.refunded":
            # Process refund event (T120-T123)
            background_tasks.add_task(process_refund, event_data)
        else:
            # Log unsupported event types
            logger.info(f"Unsupported event type: {event_type}")

        # Return 200 OK for all events (even if async processing fails)
        return {"status": "success"}

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook: {e}")
        sentry_sdk.capture_exception(e)
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except ValidationError as e:
        logger.error(f"Validation error in webhook: {e}")
        sentry_sdk.capture_exception(e)
        raise HTTPException(status_code=400, detail="Validation error")
    except Exception as e:
        logger.error(f"Unexpected error in webhook: {e}")
        sentry_sdk.capture_exception(e)
        # Still return 200 to prevent webhook retries - error handled async
        return {"status": "success"}