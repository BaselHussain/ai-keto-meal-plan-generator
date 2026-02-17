"""
Monitoring and alerting utilities for the Keto Meal Plan Generator.

Provides Sentry-based alert helpers for:
- Error rate tracking (T135)
- Payment failure alerting (T135)
- Manual queue entry alerting (T135)
- AI consecutive failure tracking (T135)
- Vercel Blob storage usage monitoring (T137)
- Webhook timestamp validation failure alerting (T138)

All functions degrade gracefully when Sentry or Redis is unavailable.
Sensitive data (emails, payment tokens) is never included in alert payloads.

Implements: T135, T137, T138
"""

import logging
from typing import Optional

import sentry_sdk
from sentry_sdk import capture_message, capture_exception, push_scope

from src.lib.redis_client import get_redis, increment_with_ttl, get_counter
from redis.exceptions import RedisError

# Configure logging
logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

# Error rate threshold: alert when >5% of requests fail
ERROR_RATE_ALERT_THRESHOLD = 0.05

# AI consecutive failure threshold: alert after >2 consecutive failures
AI_CONSECUTIVE_FAILURE_THRESHOLD = 2

# Blob storage alert threshold: alert at 80% of 5GB free tier = 4GB
BLOB_STORAGE_FREE_TIER_BYTES = 5 * 1024 * 1024 * 1024  # 5GB
BLOB_STORAGE_ALERT_THRESHOLD_BYTES = int(BLOB_STORAGE_FREE_TIER_BYTES * 0.80)  # 4GB

# Webhook failure rate threshold: alert when >3 failures per hour (replay attack signal)
WEBHOOK_FAILURE_ALERT_THRESHOLD = 3
WEBHOOK_FAILURE_WINDOW_SECONDS = 3600  # 1 hour

# Redis key prefixes
REDIS_KEY_ERROR_TOTAL = "monitoring:error_rate:total"
REDIS_KEY_ERROR_FAILURES = "monitoring:error_rate:failures"
REDIS_KEY_AI_CONSECUTIVE = "monitoring:ai:consecutive_failures"
REDIS_KEY_WEBHOOK_FAILURES = "monitoring:webhook:validation_failures"


# =============================================================================
# T135: Error Rate Tracking
# =============================================================================


async def track_error(
    error: Optional[Exception] = None,
    message: Optional[str] = None,
    context: Optional[dict] = None,
    level: str = "error",
) -> None:
    """
    Track an application error and emit to Sentry.

    Increments a Redis-backed error counter. If the error rate exceeds
    ERROR_RATE_ALERT_THRESHOLD (5%) in the current 5-minute window,
    a high-severity Sentry alert is fired.

    Args:
        error: Exception instance to capture (optional)
        message: Human-readable error description (optional)
        context: Additional key-value pairs attached to the Sentry event
        level: Sentry severity level ("fatal", "error", "warning", "info")

    Example:
        await track_error(
            error=exc,
            message="Database query failed",
            context={"endpoint": "/api/v1/quiz", "user_id": user_id},
        )
    """
    # Build context payload - never include sensitive data
    safe_context = context or {}

    try:
        with push_scope() as scope:
            scope.set_level(level)

            if safe_context:
                scope.set_context("monitoring", safe_context)

            if error is not None:
                capture_exception(error)
            elif message:
                capture_message(message, level=level)

    except Exception as sentry_exc:
        # Sentry failure must not propagate
        logger.error(f"Failed to send Sentry event: {sentry_exc}")

    # Increment counters for error rate calculation
    await _increment_error_counters(is_failure=True)

    # Check if error rate threshold is breached
    await _check_error_rate()


async def _increment_error_counters(is_failure: bool) -> None:
    """
    Increment request total and optionally failure counter.

    Uses a 5-minute rolling window (300 seconds TTL).

    Args:
        is_failure: True to increment the failure counter as well as total
    """
    window_ttl = 300  # 5-minute window
    try:
        await increment_with_ttl(REDIS_KEY_ERROR_TOTAL, ttl=window_ttl)
        if is_failure:
            await increment_with_ttl(REDIS_KEY_ERROR_FAILURES, ttl=window_ttl)
    except RedisError as exc:
        logger.warning(f"Could not update error rate counters: {exc}")


async def _check_error_rate() -> None:
    """
    Check the current error rate and fire a Sentry alert if threshold exceeded.

    Reads rolling window counters from Redis and computes failure ratio.
    Fires a Sentry 'fatal' message when rate > ERROR_RATE_ALERT_THRESHOLD.
    """
    try:
        total = await get_counter(REDIS_KEY_ERROR_TOTAL) or 0
        failures = await get_counter(REDIS_KEY_ERROR_FAILURES) or 0

        if total < 10:
            # Not enough data points to make a reliable assessment
            return

        error_rate = failures / total
        if error_rate > ERROR_RATE_ALERT_THRESHOLD:
            alert_msg = (
                f"High error rate detected: {error_rate:.1%} "
                f"({failures}/{total} requests failed in the last 5 minutes). "
                f"Threshold: {ERROR_RATE_ALERT_THRESHOLD:.0%}"
            )
            logger.error(alert_msg)

            try:
                with push_scope() as scope:
                    scope.set_tag("alert_type", "error_rate")
                    scope.set_context("error_rate", {
                        "rate": round(error_rate, 4),
                        "failures": failures,
                        "total": total,
                        "threshold": ERROR_RATE_ALERT_THRESHOLD,
                        "window_seconds": 300,
                    })
                    capture_message(alert_msg, level="fatal")
            except Exception as exc:
                logger.error(f"Failed to send error rate alert to Sentry: {exc}")

    except RedisError as exc:
        logger.warning(f"Could not compute error rate: {exc}")


# =============================================================================
# T135: Payment Failure Alerting
# =============================================================================


async def alert_payment_failure(
    transaction_id: Optional[str] = None,
    failure_reason: Optional[str] = None,
    context: Optional[dict] = None,
) -> None:
    """
    Alert Sentry on payment processing failure.

    Fires a 'error' level Sentry message. Payment-sensitive data (card
    details, full transaction data) is never included in the alert.

    Args:
        transaction_id: Paddle transaction ID for correlation (safe to log)
        failure_reason: Human-readable reason for the failure
        context: Additional non-sensitive context fields

    Example:
        await alert_payment_failure(
            transaction_id="txn_01abc",
            failure_reason="Webhook processing failed: DB write error",
        )
    """
    safe_context = context or {}
    alert_msg = (
        f"Payment processing failure"
        + (f" — transaction: {transaction_id}" if transaction_id else "")
        + (f" — reason: {failure_reason}" if failure_reason else "")
    )

    logger.error(alert_msg)

    try:
        with push_scope() as scope:
            scope.set_tag("alert_type", "payment_failure")
            scope.set_context("payment_failure", {
                "transaction_id": transaction_id or "unknown",
                "failure_reason": failure_reason or "unspecified",
                **{k: v for k, v in safe_context.items()},
            })
            capture_message(alert_msg, level="error")
    except Exception as exc:
        logger.error(f"Failed to send payment failure alert to Sentry: {exc}")


# =============================================================================
# T135: Manual Queue Entry Alerting
# =============================================================================


async def alert_manual_queue_entry(
    entry_id: Optional[str] = None,
    reason: Optional[str] = None,
    context: Optional[dict] = None,
) -> None:
    """
    Alert Sentry when a delivery is added to the manual resolution queue.

    Manual queue entries indicate deliveries that could not complete
    automatically and require human intervention. Alerts are 'warning' level
    since they require attention but are not application errors.

    Args:
        entry_id: Manual queue entry or quiz response ID for correlation
        reason: Reason the delivery was escalated to manual queue
        context: Additional non-sensitive context fields

    Example:
        await alert_manual_queue_entry(
            entry_id="quiz_response_uuid",
            reason="AI generation failed after 3 retries",
        )
    """
    safe_context = context or {}
    alert_msg = (
        "Manual queue entry added"
        + (f" — entry: {entry_id}" if entry_id else "")
        + (f" — reason: {reason}" if reason else "")
    )

    logger.warning(alert_msg)

    try:
        with push_scope() as scope:
            scope.set_tag("alert_type", "manual_queue")
            scope.set_context("manual_queue", {
                "entry_id": entry_id or "unknown",
                "reason": reason or "unspecified",
                **{k: v for k, v in safe_context.items()},
            })
            capture_message(alert_msg, level="warning")
    except Exception as exc:
        logger.error(f"Failed to send manual queue alert to Sentry: {exc}")


# =============================================================================
# T135: AI Consecutive Failure Tracking
# =============================================================================


async def track_ai_failure(
    error: Optional[Exception] = None,
    context: Optional[dict] = None,
) -> None:
    """
    Track an AI generation failure and alert after consecutive failures.

    Uses Redis to maintain a consecutive failure counter. When the count
    exceeds AI_CONSECUTIVE_FAILURE_THRESHOLD (2), a 'fatal' Sentry alert fires.
    The counter resets on successful generation via reset_ai_failure_count().

    Args:
        error: Exception from AI generation pipeline (optional)
        context: Additional context (model name, attempt number, etc.)

    Example:
        try:
            meal_plan = await generate_meal_plan(quiz_response)
            await reset_ai_failure_count()
        except AIGenerationError as exc:
            await track_ai_failure(error=exc, context={"attempt": attempt_number})
    """
    safe_context = context or {}

    try:
        consecutive_failures = await _increment_ai_failure_counter()
    except RedisError as exc:
        logger.warning(f"Could not increment AI failure counter: {exc}")
        consecutive_failures = None

    alert_msg = (
        f"AI meal plan generation failed "
        + (f"(consecutive failures: {consecutive_failures})" if consecutive_failures is not None else "(counter unavailable)")
    )
    logger.error(alert_msg)

    should_alert_critical = (
        consecutive_failures is not None
        and consecutive_failures > AI_CONSECUTIVE_FAILURE_THRESHOLD
    )
    sentry_level = "fatal" if should_alert_critical else "error"

    try:
        with push_scope() as scope:
            scope.set_tag("alert_type", "ai_failure")
            scope.set_tag("consecutive_failures", str(consecutive_failures or "unknown"))
            scope.set_context("ai_failure", {
                "consecutive_failures": consecutive_failures,
                "threshold": AI_CONSECUTIVE_FAILURE_THRESHOLD,
                "alert_escalated": should_alert_critical,
                **{k: v for k, v in safe_context.items()},
            })

            if error is not None:
                capture_exception(error)
            else:
                capture_message(alert_msg, level=sentry_level)

    except Exception as exc:
        logger.error(f"Failed to send AI failure alert to Sentry: {exc}")

    if should_alert_critical:
        logger.error(
            f"CRITICAL: AI generation has failed {consecutive_failures} consecutive times. "
            f"Threshold of {AI_CONSECUTIVE_FAILURE_THRESHOLD} exceeded."
        )


async def _increment_ai_failure_counter() -> int:
    """
    Increment the AI consecutive failure counter in Redis.

    Uses a 24-hour TTL so the counter resets once per day if not
    explicitly cleared by reset_ai_failure_count().

    Returns:
        int: Updated consecutive failure count
    """
    count = await increment_with_ttl(
        REDIS_KEY_AI_CONSECUTIVE,
        ttl=86400,  # 24-hour TTL as safety net
    )
    return count or 1


async def reset_ai_failure_count() -> None:
    """
    Reset the AI consecutive failure counter after a successful generation.

    Must be called whenever AI meal plan generation succeeds to clear
    the consecutive failure state.

    Example:
        meal_plan = await generate_meal_plan(quiz_response)
        await reset_ai_failure_count()
    """
    try:
        client = await get_redis()
        await client.delete(REDIS_KEY_AI_CONSECUTIVE)
        logger.debug("AI consecutive failure counter reset")
    except RedisError as exc:
        logger.warning(f"Could not reset AI failure counter: {exc}")


# =============================================================================
# T137: Vercel Blob Storage Monitoring
# =============================================================================


async def check_blob_storage_usage(estimated_bytes: int) -> None:
    """
    Check Vercel Blob storage usage and alert when approaching the 5GB free tier.

    Fires a Sentry 'warning' when usage exceeds BLOB_STORAGE_ALERT_THRESHOLD_BYTES
    (4GB, 80% of the 5GB free tier). Vercel Blob does not provide a direct usage
    API, so callers must supply the estimated byte count (e.g., sum of all PDF
    sizes from the database).

    Args:
        estimated_bytes: Current estimated storage usage in bytes.
                         Typically computed as: SELECT SUM(pdf_size_bytes) FROM meal_plans

    Example:
        total_bytes = await db.scalar(select(func.sum(MealPlan.pdf_size_bytes)))
        await check_blob_storage_usage(total_bytes or 0)
    """
    usage_gb = estimated_bytes / (1024 ** 3)
    threshold_gb = BLOB_STORAGE_ALERT_THRESHOLD_BYTES / (1024 ** 3)
    free_tier_gb = BLOB_STORAGE_FREE_TIER_BYTES / (1024 ** 3)
    usage_pct = (estimated_bytes / BLOB_STORAGE_FREE_TIER_BYTES) * 100

    logger.info(
        f"Blob storage check: {usage_gb:.2f}GB / {free_tier_gb:.0f}GB "
        f"({usage_pct:.1f}%)"
    )

    if estimated_bytes >= BLOB_STORAGE_ALERT_THRESHOLD_BYTES:
        alert_msg = (
            f"Vercel Blob storage approaching free tier limit: "
            f"{usage_gb:.2f}GB used of {free_tier_gb:.0f}GB "
            f"({usage_pct:.1f}%). Threshold: {threshold_gb:.0f}GB (80%)."
        )
        logger.warning(alert_msg)

        try:
            with push_scope() as scope:
                scope.set_tag("alert_type", "blob_storage_threshold")
                scope.set_context("blob_storage", {
                    "used_bytes": estimated_bytes,
                    "used_gb": round(usage_gb, 3),
                    "free_tier_gb": free_tier_gb,
                    "threshold_gb": threshold_gb,
                    "usage_pct": round(usage_pct, 1),
                })
                capture_message(alert_msg, level="warning")
        except Exception as exc:
            logger.error(f"Failed to send blob storage alert to Sentry: {exc}")


async def get_blob_storage_stats(estimated_bytes: int) -> dict:
    """
    Return current Vercel Blob storage usage metrics.

    Callers supply the estimated byte count (e.g., from a database aggregate).
    No external API calls are made; this function only computes derived metrics.

    Args:
        estimated_bytes: Current estimated storage usage in bytes

    Returns:
        dict: Storage usage metrics with keys:
            - used_bytes (int): Bytes consumed
            - used_gb (float): Gigabytes consumed
            - free_tier_gb (float): Free tier limit in GB
            - threshold_gb (float): Alert threshold in GB
            - usage_pct (float): Percentage of free tier consumed
            - threshold_exceeded (bool): True if usage >= 80% threshold
            - critical (bool): True if usage >= 95% of free tier

    Example:
        stats = await get_blob_storage_stats(total_pdf_bytes)
        if stats["threshold_exceeded"]:
            # Trigger cleanup job early
            pass
    """
    usage_gb = estimated_bytes / (1024 ** 3)
    threshold_gb = BLOB_STORAGE_ALERT_THRESHOLD_BYTES / (1024 ** 3)
    free_tier_gb = BLOB_STORAGE_FREE_TIER_BYTES / (1024 ** 3)
    usage_pct = (estimated_bytes / BLOB_STORAGE_FREE_TIER_BYTES) * 100
    critical_threshold = int(BLOB_STORAGE_FREE_TIER_BYTES * 0.95)

    return {
        "used_bytes": estimated_bytes,
        "used_gb": round(usage_gb, 3),
        "free_tier_gb": free_tier_gb,
        "threshold_gb": threshold_gb,
        "usage_pct": round(usage_pct, 1),
        "threshold_exceeded": estimated_bytes >= BLOB_STORAGE_ALERT_THRESHOLD_BYTES,
        "critical": estimated_bytes >= critical_threshold,
    }


# =============================================================================
# T138: Webhook Timestamp Validation Failure Alerting
# =============================================================================


async def track_webhook_validation_failure(
    source: Optional[str] = None,
    failure_reason: Optional[str] = None,
) -> None:
    """
    Track a webhook signature/timestamp validation failure.

    Increments a Redis counter with a 1-hour TTL. When the count exceeds
    WEBHOOK_FAILURE_ALERT_THRESHOLD (3 per hour), a potential replay attack
    is reported to Sentry at 'error' level.

    Args:
        source: Webhook source identifier (e.g., "paddle", IP address)
        failure_reason: Type of validation failure ("invalid_signature",
                        "timestamp_expired", "missing_header", etc.)

    Example:
        # In Paddle webhook handler, after signature verification fails:
        await track_webhook_validation_failure(
            source="paddle",
            failure_reason="invalid_signature",
        )
    """
    safe_source = source or "unknown"
    safe_reason = failure_reason or "unspecified"

    logger.warning(
        f"Webhook validation failure: source={safe_source}, reason={safe_reason}"
    )

    # Increment per-hour failure counter
    try:
        failure_count = await increment_with_ttl(
            REDIS_KEY_WEBHOOK_FAILURES,
            ttl=WEBHOOK_FAILURE_WINDOW_SECONDS,
        )
    except RedisError as exc:
        logger.warning(f"Could not increment webhook failure counter: {exc}")
        failure_count = None

    # Alert if threshold exceeded
    if failure_count is not None and failure_count > WEBHOOK_FAILURE_ALERT_THRESHOLD:
        alert_msg = (
            f"Potential webhook replay attack detected: "
            f"{failure_count} validation failures in the past hour "
            f"(threshold: {WEBHOOK_FAILURE_ALERT_THRESHOLD}). "
            f"Last source: {safe_source}, reason: {safe_reason}"
        )
        logger.error(alert_msg)

        try:
            with push_scope() as scope:
                scope.set_tag("alert_type", "webhook_replay_attack")
                scope.set_tag("webhook_source", safe_source)
                scope.set_context("webhook_failures", {
                    "failure_count": failure_count,
                    "threshold": WEBHOOK_FAILURE_ALERT_THRESHOLD,
                    "window_seconds": WEBHOOK_FAILURE_WINDOW_SECONDS,
                    "last_source": safe_source,
                    "last_reason": safe_reason,
                })
                capture_message(alert_msg, level="error")
        except Exception as exc:
            logger.error(f"Failed to send webhook failure alert to Sentry: {exc}")


async def check_webhook_failure_rate() -> dict:
    """
    Return current webhook validation failure rate metrics.

    Reads the Redis counter for the current 1-hour window.

    Returns:
        dict: Failure rate metrics with keys:
            - failure_count (int): Number of failures in the current window
            - threshold (int): Alert threshold count
            - window_seconds (int): Tracking window duration in seconds
            - threshold_exceeded (bool): True if failure_count > threshold
            - alert_active (bool): Alias for threshold_exceeded

    Example:
        metrics = await check_webhook_failure_rate()
        if metrics["alert_active"]:
            # Block further webhook processing from untrusted sources
            pass
    """
    try:
        failure_count = await get_counter(REDIS_KEY_WEBHOOK_FAILURES) or 0
    except RedisError as exc:
        logger.warning(f"Could not read webhook failure counter: {exc}")
        failure_count = 0

    threshold_exceeded = failure_count > WEBHOOK_FAILURE_ALERT_THRESHOLD

    return {
        "failure_count": failure_count,
        "threshold": WEBHOOK_FAILURE_ALERT_THRESHOLD,
        "window_seconds": WEBHOOK_FAILURE_WINDOW_SECONDS,
        "threshold_exceeded": threshold_exceeded,
        "alert_active": threshold_exceeded,
    }
