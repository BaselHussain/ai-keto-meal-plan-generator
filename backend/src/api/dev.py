"""
Development-only API endpoints for testing the full delivery flow
without payment integration.

WARNING: These endpoints MUST NOT be enabled in production.
They bypass payment verification and trigger the full delivery pipeline directly.

Endpoints:
    POST /api/v1/dev/trigger-delivery - Trigger meal plan delivery for a quiz submission
"""

import logging
import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.lib.database import get_db
from src.lib.email_utils import normalize_email
from src.models.quiz_response import QuizResponse
from src.services.delivery_orchestrator import orchestrate_meal_plan_delivery

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dev", tags=["Development"])


class TriggerDeliveryRequest(BaseModel):
    """Request body for triggering meal plan delivery."""

    quiz_id: str = Field(..., description="Quiz response ID from submission")
    email: str = Field(..., description="Email address for delivery")


class TriggerDeliveryResponse(BaseModel):
    """Response from delivery trigger."""

    success: bool
    message: str
    payment_id: str = Field(default="", description="Fake payment ID used for this delivery")
    delivery_status: str = Field(default="queued", description="Current delivery status")


def _build_preferences_summary(quiz_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build preferences_summary from quiz_data for the orchestrator."""
    preferred_proteins = []
    for step_key in ["step_3", "step_4", "step_9", "step_10"]:
        items = quiz_data.get(step_key, [])
        if isinstance(items, list):
            preferred_proteins.extend(items)

    excluded_foods: list = []
    dietary_restrictions = quiz_data.get("step_17", "")

    return {
        "preferred_proteins": preferred_proteins,
        "excluded_foods": excluded_foods,
        "dietary_restrictions": dietary_restrictions,
    }


async def _run_delivery(
    payment_id: str,
    email: str,
    normalized_email_addr: str,
    quiz_data: Dict[str, Any],
    calorie_target: int,
    preferences_summary: Dict[str, Any],
) -> None:
    """Run the delivery orchestration as a background task."""
    try:
        result = await orchestrate_meal_plan_delivery(
            payment_id=payment_id,
            email=email,
            normalized_email=normalized_email_addr,
            quiz_data=quiz_data,
            calorie_target=calorie_target,
            preferences_summary=preferences_summary,
        )

        if result["success"]:
            logger.info(
                f"[DEV] Delivery completed successfully: payment_id={payment_id}, "
                f"meal_plan_id={result.get('meal_plan_id')}, "
                f"duration_ms={result.get('total_duration_ms')}"
            )
        else:
            logger.error(
                f"[DEV] Delivery failed: payment_id={payment_id}, "
                f"error={result.get('error')}"
            )
    except Exception as e:
        logger.error(f"[DEV] Delivery error: payment_id={payment_id}, error={e}", exc_info=True)


@router.post("/trigger-delivery", response_model=TriggerDeliveryResponse)
async def trigger_delivery(
    request: TriggerDeliveryRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> TriggerDeliveryResponse:
    """
    [DEV ONLY] Trigger meal plan delivery without payment.

    This endpoint bypasses Paddle payment verification and directly
    triggers the full delivery pipeline: AI generation -> PDF -> Blob -> Email.

    Args:
        request: Quiz ID and email for delivery
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        TriggerDeliveryResponse with status

    Raises:
        HTTPException 404: Quiz response not found
        HTTPException 500: Delivery trigger failed
    """
    try:
        # Look up quiz response
        result = await db.execute(
            select(QuizResponse).where(QuizResponse.id == request.quiz_id)
        )
        quiz_response = result.scalar_one_or_none()

        if not quiz_response:
            raise HTTPException(
                status_code=404,
                detail=f"Quiz response not found: {request.quiz_id}",
            )

        # Generate a fake payment ID for the dev flow
        fake_payment_id = f"dev-test-{uuid.uuid4().hex[:12]}"

        # Build preferences summary from quiz data
        quiz_data = quiz_response.quiz_data
        calorie_target = quiz_response.calorie_target
        normalized_email_addr = normalize_email(request.email)
        preferences_summary = _build_preferences_summary(quiz_data)

        logger.info(
            f"[DEV] Triggering delivery: quiz_id={request.quiz_id}, "
            f"email={request.email}, fake_payment_id={fake_payment_id}, "
            f"calorie_target={calorie_target}"
        )

        # Run delivery in background so the endpoint returns immediately
        background_tasks.add_task(
            _run_delivery,
            payment_id=fake_payment_id,
            email=request.email,
            normalized_email_addr=normalized_email_addr,
            quiz_data=quiz_data,
            calorie_target=calorie_target,
            preferences_summary=preferences_summary,
        )

        return TriggerDeliveryResponse(
            success=True,
            message="Delivery triggered. Your personalized keto meal plan is being generated and will be sent to your email.",
            payment_id=fake_payment_id,
            delivery_status="processing",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DEV] Failed to trigger delivery: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger delivery: {str(e)}",
        )
