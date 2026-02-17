"""
Delivery Orchestration Service

Coordinates the full meal plan delivery flow after successful payment:
1. AI meal plan generation (meal_plan_generator.py)
2. PDF generation (pdf_generator.py)
3. Blob storage upload (blob_storage.py)
4. Email delivery (email_service.py)

Key Features:
- Transaction boundaries for atomic operations (T087)
- Rollback handling for failed operations (T088)
- Comprehensive error logging with Sentry integration (T089)
- Idempotency checks for each step
- Performance tracking (<90s p95 requirement)
- Manual resolution queue routing on unrecoverable failures

Implements: T086, T087, T088, T089
Functional Requirements: FR-Q-018, FR-D-001 to FR-D-008, FR-E-001 to FR-E-005
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

from src.lib.database import get_db
from src.models.meal_plan import MealPlan
from src.models.manual_resolution import ManualResolution
from src.schemas.meal_plan import PreferencesSummary
from src.services.meal_plan_generator import (
    generate_meal_plan,
    MealPlanGenerationError,
)
from src.services.pdf_generator import (
    generate_pdf,
    PDFGenerationError,
)
from src.services.blob_storage import (
    upload_pdf_to_vercel_blob,
    delete_blob,
    BlobStorageError,
)
from src.services.email_service import send_delivery_email

# Configure logging
logger = logging.getLogger(__name__)

# SLA deadline for manual resolution (4 hours per spec)
SLA_DEADLINE_HOURS = 4

# Performance budget (5 min for dev - 30-day meal plan generation is large)
ORCHESTRATION_TIMEOUT = 360


class DeliveryOrchestrationError(Exception):
    """
    Custom exception for delivery orchestration failures.

    Attributes:
        message: Human-readable error description
        error_type: Category of error (ai_generation, pdf_generation, blob_upload, email_delivery, database)
        step: Which step in the orchestration failed
        original_error: Original exception if wrapping another error
        requires_manual_resolution: Whether failure should be routed to manual queue
    """

    def __init__(
        self,
        message: str,
        error_type: str = "unknown",
        step: str = "unknown",
        original_error: Optional[Exception] = None,
        requires_manual_resolution: bool = False,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.step = step
        self.original_error = original_error
        self.requires_manual_resolution = requires_manual_resolution

    def __str__(self) -> str:
        """String representation with error type and step."""
        return f"[{self.error_type}:{self.step}] {super().__str__()}"


def _capture_sentry_error(
    error: Exception,
    payment_id: str,
    email: str,
    step: str,
    extra_context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Capture error in Sentry with context (T089).

    Args:
        error: Exception to capture
        payment_id: Paddle payment ID for context
        email: User email for context
        step: Current orchestration step
        extra_context: Additional context data
    """
    if not SENTRY_AVAILABLE:
        logger.warning("Sentry not available for error capture")
        return

    try:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("payment_id", payment_id)
            scope.set_tag("step", step)
            scope.set_user({"email": email})

            if extra_context:
                for key, value in extra_context.items():
                    scope.set_extra(key, value)

            sentry_sdk.capture_exception(error)

        logger.debug(f"Error captured in Sentry: {step} - {error}")

    except Exception as sentry_error:
        logger.error(f"Failed to capture error in Sentry: {sentry_error}")


def _log_step(
    step: str,
    status: str,
    payment_id: str,
    email: str,
    duration_ms: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log orchestration step with structured context (T089).

    Args:
        step: Step name (ai_generation, pdf_generation, blob_upload, email_delivery)
        status: Step status (started, completed, failed, skipped)
        payment_id: Paddle payment ID
        email: User email
        duration_ms: Step duration in milliseconds (if completed)
        extra: Additional context data
    """
    log_data = {
        "step": step,
        "status": status,
        "payment_id": payment_id,
        "email": email,
    }

    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms

    if extra:
        log_data.update(extra)

    if status == "failed":
        logger.error(f"ORCHESTRATION_STEP: {log_data}")
    elif status == "completed":
        logger.info(f"ORCHESTRATION_STEP: {log_data}")
    else:
        logger.debug(f"ORCHESTRATION_STEP: {log_data}")


async def _create_manual_resolution_entry(
    db: AsyncSession,
    payment_id: str,
    user_email: str,
    normalized_email: str,
    issue_type: str,
    error_details: Optional[str] = None,
) -> ManualResolution:
    """
    Create manual resolution queue entry for failed operations (T088).

    Args:
        db: Database session
        payment_id: Paddle payment ID
        user_email: Original user email
        normalized_email: Normalized email for pattern detection
        issue_type: Category of failure
        error_details: Optional error details for resolution notes

    Returns:
        ManualResolution: Created queue entry
    """
    now = datetime.utcnow()
    sla_deadline = now + timedelta(hours=SLA_DEADLINE_HOURS)

    resolution = ManualResolution(
        id=str(uuid.uuid4()),
        payment_id=payment_id,
        user_email=user_email,
        normalized_email=normalized_email,
        issue_type=issue_type,
        status="pending",
        sla_deadline=sla_deadline,
        created_at=now,
        resolution_notes=f"Automated entry: {error_details}" if error_details else None,
    )

    db.add(resolution)

    logger.info(
        f"Created manual resolution entry: payment_id={payment_id}, "
        f"issue_type={issue_type}, sla_deadline={sla_deadline.isoformat()}"
    )

    return resolution


async def _check_existing_meal_plan(
    db: AsyncSession,
    payment_id: str,
) -> Optional[MealPlan]:
    """
    Check if meal plan already exists for payment (idempotency check).

    Args:
        db: Database session
        payment_id: Paddle payment ID

    Returns:
        MealPlan if exists, None otherwise
    """
    result = await db.execute(
        select(MealPlan).where(MealPlan.payment_id == payment_id)
    )
    return result.scalar_one_or_none()


async def _create_meal_plan_record(
    db: AsyncSession,
    payment_id: str,
    email: str,
    normalized_email: str,
    calorie_target: int,
    preferences_summary: Dict[str, Any],
) -> MealPlan:
    """
    Create initial meal plan record with 'processing' status (T087).

    This is the first atomic operation - creates the record before
    starting the expensive AI generation.

    Args:
        db: Database session
        payment_id: Paddle payment ID
        email: User email
        normalized_email: Normalized email
        calorie_target: Daily calorie target
        preferences_summary: Food preferences dict

    Returns:
        MealPlan: Created record with 'processing' status
    """
    meal_plan = MealPlan(
        id=str(uuid.uuid4()),
        payment_id=payment_id,
        email=email,
        normalized_email=normalized_email,
        pdf_blob_path="",  # Will be updated after upload
        calorie_target=calorie_target,
        preferences_summary=preferences_summary,
        ai_model="pending",  # Will be updated after generation
        status="processing",
        refund_count=0,
        created_at=datetime.utcnow(),
    )

    db.add(meal_plan)
    await db.flush()  # Flush to get ID without committing

    logger.info(
        f"Created meal plan record: id={meal_plan.id}, payment_id={payment_id}, status=processing"
    )

    return meal_plan


async def _update_meal_plan_status(
    db: AsyncSession,
    meal_plan: MealPlan,
    status: str,
    pdf_blob_path: Optional[str] = None,
    ai_model: Optional[str] = None,
    email_sent_at: Optional[datetime] = None,
) -> None:
    """
    Update meal plan record status and fields (T087).

    Args:
        db: Database session
        meal_plan: MealPlan record to update
        status: New status (processing, completed, failed)
        pdf_blob_path: Blob URL after upload
        ai_model: AI model used for generation
        email_sent_at: Email delivery timestamp
    """
    meal_plan.status = status

    if pdf_blob_path is not None:
        meal_plan.pdf_blob_path = pdf_blob_path

    if ai_model is not None:
        meal_plan.ai_model = ai_model

    if email_sent_at is not None:
        meal_plan.email_sent_at = email_sent_at

    await db.flush()

    logger.debug(
        f"Updated meal plan status: id={meal_plan.id}, status={status}"
    )


async def orchestrate_meal_plan_delivery(
    payment_id: str,
    email: str,
    normalized_email: str,
    quiz_data: Dict[str, Any],
    calorie_target: int,
    preferences_summary: Dict[str, Any],
    db: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """
    Orchestrate the full meal plan delivery flow.

    This function coordinates all steps of meal plan delivery after successful payment:
    1. Create/retrieve meal plan record (idempotent)
    2. Generate AI meal plan
    3. Generate PDF from meal plan
    4. Upload PDF to Vercel Blob storage
    5. Send delivery email with PDF attachment

    Each step has:
    - Idempotency checks (skip if already completed)
    - Transaction boundaries (atomic commits)
    - Rollback handling (cleanup on failure)
    - Error logging (Sentry integration)
    - Manual resolution routing (on unrecoverable failures)

    Args:
        payment_id: Paddle payment transaction ID
        email: User's original email address
        normalized_email: Normalized email for abuse prevention
        quiz_data: Full quiz response data (for AI context)
        calorie_target: Daily calorie target from quiz
        preferences_summary: Food preferences dict

    Returns:
        dict: {
            "success": bool,
            "meal_plan_id": str | None,
            "steps_completed": list[str],
            "error": str | None,
            "requires_manual_resolution": bool,
            "total_duration_ms": int,
        }

    Implements:
        - T086: Full orchestration flow
        - T087: Transaction boundaries
        - T088: Rollback handling
        - T089: Comprehensive error logging

    Performance Budget:
        - Full flow < 90s (p95) per FR-Q-018
    """
    start_time = datetime.utcnow()
    steps_completed: List[str] = []
    meal_plan: Optional[MealPlan] = None
    meal_plan_data = None
    pdf_bytes: Optional[bytes] = None
    blob_url: Optional[str] = None

    logger.info(
        f"Starting meal plan delivery orchestration: payment_id={payment_id}, "
        f"email={email}, calorie_target={calorie_target}"
    )

    # Use provided db session or create new one
    if db is None:
        # Get a new database session
        async for session in get_db():
            db = session
            break

    try:
        # ============================================================
        # STEP 0: Idempotency Check - Check for existing meal plan
        # ============================================================
        _log_step("idempotency_check", "started", payment_id, email)

        existing_meal_plan = await _check_existing_meal_plan(db, payment_id)

        if existing_meal_plan:
            # Check if already completed
            if existing_meal_plan.status == "completed":
                logger.info(
                    f"Meal plan already completed for payment_id={payment_id}, "
                    f"skipping orchestration"
                )
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

                return {
                    "success": True,
                    "meal_plan_id": existing_meal_plan.id,
                    "steps_completed": ["already_completed"],
                    "error": None,
                    "requires_manual_resolution": False,
                    "total_duration_ms": duration_ms,
                }

            # Resume from existing 'processing' meal plan
            meal_plan = existing_meal_plan
            logger.info(
                f"Resuming orchestration for existing meal plan: id={meal_plan.id}, "
                f"status={meal_plan.status}"
            )

        steps_completed.append("idempotency_check")

        # ============================================================
        # STEP 1: Create Meal Plan Record (Atomic Transaction)
        # ============================================================
        if meal_plan is None:
            step_start = datetime.utcnow()
            _log_step("create_record", "started", payment_id, email)

            try:
                meal_plan = await _create_meal_plan_record(
                    db=db,
                    payment_id=payment_id,
                    email=email,
                    normalized_email=normalized_email,
                    calorie_target=calorie_target,
                    preferences_summary=preferences_summary,
                )

                # Commit the record creation (atomic boundary T087)
                await db.commit()

                step_duration = int((datetime.utcnow() - step_start).total_seconds() * 1000)
                _log_step("create_record", "completed", payment_id, email, step_duration)
                steps_completed.append("create_record")

            except Exception as e:
                _log_step("create_record", "failed", payment_id, email, extra={"error": str(e)})
                _capture_sentry_error(e, payment_id, email, "create_record")
                await db.rollback()
                raise DeliveryOrchestrationError(
                    f"Failed to create meal plan record: {e}",
                    error_type="database",
                    step="create_record",
                    original_error=e,
                    requires_manual_resolution=True,
                )

        # ============================================================
        # STEP 2: AI Meal Plan Generation
        # ============================================================
        step_start = datetime.utcnow()
        _log_step("ai_generation", "started", payment_id, email)

        try:
            # Build preferences from summary
            preferences = PreferencesSummary(
                excluded_foods=preferences_summary.get("excluded_foods", []),
                preferred_proteins=preferences_summary.get("preferred_proteins", []),
                dietary_restrictions=preferences_summary.get("dietary_restrictions", ""),
            )

            # Generate meal plan with AI
            generation_result = await asyncio.wait_for(
                generate_meal_plan(calorie_target, preferences),
                timeout=ORCHESTRATION_TIMEOUT - 10,  # Reserve 10s for remaining steps
            )

            if not generation_result.get("success"):
                raise MealPlanGenerationError(
                    generation_result.get("validation_errors", ["Unknown AI generation error"])[0],
                    error_type=generation_result.get("error_type", "ai_generation_failed"),
                )

            meal_plan_data = generation_result["meal_plan"]
            ai_model = generation_result.get("model_used", "unknown")

            # Update meal plan with AI model info
            await _update_meal_plan_status(db, meal_plan, "processing", ai_model=ai_model)
            await db.commit()

            step_duration = int((datetime.utcnow() - step_start).total_seconds() * 1000)
            _log_step(
                "ai_generation", "completed", payment_id, email, step_duration,
                extra={"ai_model": ai_model, "generation_time_ms": generation_result.get("generation_time_ms")}
            )
            steps_completed.append("ai_generation")

        except asyncio.TimeoutError as e:
            _log_step("ai_generation", "failed", payment_id, email, extra={"error": "timeout"})
            _capture_sentry_error(e, payment_id, email, "ai_generation", {"timeout_seconds": ORCHESTRATION_TIMEOUT - 10})
            await _update_meal_plan_status(db, meal_plan, "failed")
            await db.commit()

            # Create manual resolution entry
            await _create_manual_resolution_entry(
                db, payment_id, email, normalized_email,
                "ai_validation_failed", "AI generation timed out"
            )
            await db.commit()

            raise DeliveryOrchestrationError(
                "AI meal plan generation timed out",
                error_type="timeout",
                step="ai_generation",
                original_error=e,
                requires_manual_resolution=True,
            )

        except MealPlanGenerationError as e:
            _log_step("ai_generation", "failed", payment_id, email, extra={"error": str(e)})
            _capture_sentry_error(e, payment_id, email, "ai_generation", {"error_type": e.error_type})
            await _update_meal_plan_status(db, meal_plan, "failed")
            await db.commit()

            # Create manual resolution entry
            await _create_manual_resolution_entry(
                db, payment_id, email, normalized_email,
                "ai_validation_failed", str(e)
            )
            await db.commit()

            raise DeliveryOrchestrationError(
                f"AI meal plan generation failed: {e}",
                error_type="ai_generation",
                step="ai_generation",
                original_error=e,
                requires_manual_resolution=True,
            )

        except Exception as e:
            _log_step("ai_generation", "failed", payment_id, email, extra={"error": str(e)})
            _capture_sentry_error(e, payment_id, email, "ai_generation")
            await _update_meal_plan_status(db, meal_plan, "failed")
            await db.commit()

            await _create_manual_resolution_entry(
                db, payment_id, email, normalized_email,
                "ai_validation_failed", str(e)
            )
            await db.commit()

            raise DeliveryOrchestrationError(
                f"Unexpected error during AI generation: {e}",
                error_type="ai_generation",
                step="ai_generation",
                original_error=e,
                requires_manual_resolution=True,
            )

        # ============================================================
        # STEP 3: PDF Generation
        # ============================================================
        step_start = datetime.utcnow()
        _log_step("pdf_generation", "started", payment_id, email)

        try:
            pdf_bytes = await generate_pdf(
                meal_plan=meal_plan_data,
                calorie_target=calorie_target,
                user_email=email,
                preferences=preferences,
            )

            step_duration = int((datetime.utcnow() - step_start).total_seconds() * 1000)
            _log_step(
                "pdf_generation", "completed", payment_id, email, step_duration,
                extra={"pdf_size_bytes": len(pdf_bytes)}
            )
            steps_completed.append("pdf_generation")

        except PDFGenerationError as e:
            _log_step("pdf_generation", "failed", payment_id, email, extra={"error": str(e)})
            _capture_sentry_error(e, payment_id, email, "pdf_generation", {"error_type": e.error_type})
            await _update_meal_plan_status(db, meal_plan, "failed")
            await db.commit()

            await _create_manual_resolution_entry(
                db, payment_id, email, normalized_email,
                "ai_validation_failed", f"PDF generation failed: {e}"
            )
            await db.commit()

            raise DeliveryOrchestrationError(
                f"PDF generation failed: {e}",
                error_type="pdf_generation",
                step="pdf_generation",
                original_error=e,
                requires_manual_resolution=True,
            )

        except Exception as e:
            _log_step("pdf_generation", "failed", payment_id, email, extra={"error": str(e)})
            _capture_sentry_error(e, payment_id, email, "pdf_generation")
            await _update_meal_plan_status(db, meal_plan, "failed")
            await db.commit()

            await _create_manual_resolution_entry(
                db, payment_id, email, normalized_email,
                "ai_validation_failed", f"PDF generation error: {e}"
            )
            await db.commit()

            raise DeliveryOrchestrationError(
                f"Unexpected error during PDF generation: {e}",
                error_type="pdf_generation",
                step="pdf_generation",
                original_error=e,
                requires_manual_resolution=True,
            )

        # ============================================================
        # STEP 4: Blob Storage Upload (Atomic with PDF Generation - T087)
        # ============================================================
        step_start = datetime.utcnow()
        _log_step("blob_upload", "started", payment_id, email)

        try:
            # Generate filename with payment ID for traceability
            pdf_filename = f"keto-meal-plan-{payment_id[:12]}.pdf"

            blob_url = await upload_pdf_to_vercel_blob(pdf_bytes, pdf_filename)

            # Update meal plan with blob URL (atomic commit with email send status)
            await _update_meal_plan_status(db, meal_plan, "processing", pdf_blob_path=blob_url)
            await db.commit()

            step_duration = int((datetime.utcnow() - step_start).total_seconds() * 1000)
            _log_step(
                "blob_upload", "completed", payment_id, email, step_duration,
                extra={"blob_url": blob_url}
            )
            steps_completed.append("blob_upload")

        except BlobStorageError as e:
            _log_step("blob_upload", "failed", payment_id, email, extra={"error": str(e)})
            _capture_sentry_error(e, payment_id, email, "blob_upload", {"error_type": e.error_type})
            await _update_meal_plan_status(db, meal_plan, "failed")
            await db.commit()

            await _create_manual_resolution_entry(
                db, payment_id, email, normalized_email,
                "ai_validation_failed", f"Blob upload failed: {e}"
            )
            await db.commit()

            raise DeliveryOrchestrationError(
                f"Blob storage upload failed: {e}",
                error_type="blob_upload",
                step="blob_upload",
                original_error=e,
                requires_manual_resolution=True,
            )

        except Exception as e:
            _log_step("blob_upload", "failed", payment_id, email, extra={"error": str(e)})
            _capture_sentry_error(e, payment_id, email, "blob_upload")
            await _update_meal_plan_status(db, meal_plan, "failed")
            await db.commit()

            await _create_manual_resolution_entry(
                db, payment_id, email, normalized_email,
                "ai_validation_failed", f"Blob upload error: {e}"
            )
            await db.commit()

            raise DeliveryOrchestrationError(
                f"Unexpected error during blob upload: {e}",
                error_type="blob_upload",
                step="blob_upload",
                original_error=e,
                requires_manual_resolution=True,
            )

        # ============================================================
        # STEP 5: Email Delivery (Atomic with Blob Upload - T087)
        # ============================================================
        step_start = datetime.utcnow()
        _log_step("email_delivery", "started", payment_id, email)

        try:
            # Check if email already sent (idempotency)
            email_already_sent = meal_plan.email_sent_at is not None

            email_result = await send_delivery_email(
                to_email=email,
                calorie_target=calorie_target,
                pdf_bytes=pdf_bytes,
                pdf_filename=pdf_filename,
                payment_id=payment_id,
                email_already_sent=email_already_sent,
            )

            if email_result["success"]:
                # Update meal plan to completed with email timestamp
                sent_at = email_result.get("sent_at")
                await _update_meal_plan_status(
                    db, meal_plan, "completed",
                    email_sent_at=sent_at,
                )
                await db.commit()

                step_duration = int((datetime.utcnow() - step_start).total_seconds() * 1000)
                _log_step(
                    "email_delivery", "completed", payment_id, email, step_duration,
                    extra={"message_id": email_result.get("message_id")}
                )
                steps_completed.append("email_delivery")

            else:
                # Email delivery failed
                error_msg = email_result.get("error", "Unknown email error")
                _log_step("email_delivery", "failed", payment_id, email, extra={"error": error_msg})
                _capture_sentry_error(
                    Exception(error_msg), payment_id, email, "email_delivery",
                    {"attempts": email_result.get("attempts")}
                )

                # Check if manual resolution needed
                if email_result.get("requires_manual_resolution"):
                    # PDF is already uploaded, so mark as completed but with email issue
                    await _update_meal_plan_status(db, meal_plan, "completed")
                    await db.commit()

                    # Create manual resolution for email issue
                    await _create_manual_resolution_entry(
                        db, payment_id, email, normalized_email,
                        "email_delivery_failed", error_msg
                    )
                    await db.commit()

                    raise DeliveryOrchestrationError(
                        f"Email delivery failed: {error_msg}",
                        error_type="email_delivery",
                        step="email_delivery",
                        requires_manual_resolution=True,
                    )

                raise DeliveryOrchestrationError(
                    f"Email delivery failed: {error_msg}",
                    error_type="email_delivery",
                    step="email_delivery",
                    requires_manual_resolution=False,
                )

        except DeliveryOrchestrationError:
            # Re-raise our custom errors
            raise

        except Exception as e:
            _log_step("email_delivery", "failed", payment_id, email, extra={"error": str(e)})
            _capture_sentry_error(e, payment_id, email, "email_delivery")

            # PDF is uploaded, mark completed but note email failure
            await _update_meal_plan_status(db, meal_plan, "completed")
            await db.commit()

            await _create_manual_resolution_entry(
                db, payment_id, email, normalized_email,
                "email_delivery_failed", str(e)
            )
            await db.commit()

            raise DeliveryOrchestrationError(
                f"Unexpected error during email delivery: {e}",
                error_type="email_delivery",
                step="email_delivery",
                original_error=e,
                requires_manual_resolution=True,
            )

        # ============================================================
        # SUCCESS: All steps completed
        # ============================================================
        total_duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        logger.info(
            f"Meal plan delivery completed successfully: payment_id={payment_id}, "
            f"meal_plan_id={meal_plan.id}, total_duration_ms={total_duration_ms}"
        )

        return {
            "success": True,
            "meal_plan_id": meal_plan.id,
            "steps_completed": steps_completed,
            "error": None,
            "requires_manual_resolution": False,
            "total_duration_ms": total_duration_ms,
        }

    except DeliveryOrchestrationError as e:
        # Handle our custom orchestration errors
        total_duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        logger.error(
            f"Meal plan delivery failed: payment_id={payment_id}, "
            f"step={e.step}, error={e}, total_duration_ms={total_duration_ms}"
        )

        return {
            "success": False,
            "meal_plan_id": meal_plan.id if meal_plan else None,
            "steps_completed": steps_completed,
            "error": str(e),
            "requires_manual_resolution": e.requires_manual_resolution,
            "total_duration_ms": total_duration_ms,
        }

    except Exception as e:
        # Handle unexpected errors
        total_duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        logger.error(
            f"Unexpected error during orchestration: payment_id={payment_id}, "
            f"error={e}, total_duration_ms={total_duration_ms}",
            exc_info=True
        )

        _capture_sentry_error(e, payment_id, email, "orchestration", {"steps_completed": steps_completed})

        # Rollback any pending transaction (T088)
        try:
            await db.rollback()
        except Exception:
            pass

        # Create manual resolution entry for unexpected failure
        try:
            await _create_manual_resolution_entry(
                db, payment_id, email, normalized_email,
                "ai_validation_failed", f"Orchestration error: {e}"
            )
            await db.commit()
        except Exception as resolution_error:
            logger.error(f"Failed to create manual resolution entry: {resolution_error}")

        return {
            "success": False,
            "meal_plan_id": meal_plan.id if meal_plan else None,
            "steps_completed": steps_completed,
            "error": str(e),
            "requires_manual_resolution": True,
            "total_duration_ms": total_duration_ms,
        }


async def retry_failed_delivery(
    payment_id: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Retry a failed meal plan delivery from the last successful step.

    This function is called by admin tools or scheduled jobs to retry
    failed deliveries. It resumes from where the previous attempt failed.

    Args:
        payment_id: Paddle payment transaction ID
        db: Database session

    Returns:
        dict: Same format as orchestrate_meal_plan_delivery()

    Note:
        This function requires the meal plan record to exist in the database.
        It will NOT create a new record if one doesn't exist.
    """
    logger.info(f"Retrying failed delivery for payment_id={payment_id}")

    # Find existing meal plan
    meal_plan = await _check_existing_meal_plan(db, payment_id)

    if not meal_plan:
        return {
            "success": False,
            "meal_plan_id": None,
            "steps_completed": [],
            "error": f"No meal plan found for payment_id={payment_id}",
            "requires_manual_resolution": True,
            "total_duration_ms": 0,
        }

    if meal_plan.status == "completed":
        return {
            "success": True,
            "meal_plan_id": meal_plan.id,
            "steps_completed": ["already_completed"],
            "error": None,
            "requires_manual_resolution": False,
            "total_duration_ms": 0,
        }

    # Retry the orchestration
    return await orchestrate_meal_plan_delivery(
        payment_id=payment_id,
        email=meal_plan.email,
        normalized_email=meal_plan.normalized_email,
        quiz_data={},  # Quiz data not needed for retry
        calorie_target=meal_plan.calorie_target,
        preferences_summary=meal_plan.preferences_summary,
        db=db,
    )


async def rollback_failed_delivery(
    payment_id: str,
    db: AsyncSession,
    cleanup_blob: bool = True,
) -> Dict[str, Any]:
    """
    Rollback a failed delivery by cleaning up partial artifacts (T088).

    This function is called when a delivery fails and cleanup is needed:
    - Delete uploaded blob (if cleanup_blob=True)
    - Update meal plan status to 'failed'
    - Create manual resolution entry

    Args:
        payment_id: Paddle payment transaction ID
        db: Database session
        cleanup_blob: Whether to delete uploaded blob (default True)

    Returns:
        dict: Rollback result
    """
    logger.info(f"Rolling back failed delivery for payment_id={payment_id}")

    meal_plan = await _check_existing_meal_plan(db, payment_id)

    if not meal_plan:
        return {
            "success": False,
            "error": f"No meal plan found for payment_id={payment_id}",
        }

    # Clean up blob if exists and requested
    if cleanup_blob and meal_plan.pdf_blob_path:
        try:
            await delete_blob(meal_plan.pdf_blob_path)
            logger.info(f"Deleted blob for payment_id={payment_id}: {meal_plan.pdf_blob_path}")
        except BlobStorageError as e:
            logger.warning(f"Failed to delete blob during rollback: {e}")

    # Update status to failed
    await _update_meal_plan_status(db, meal_plan, "failed")
    await db.commit()

    return {
        "success": True,
        "meal_plan_id": meal_plan.id,
        "rolled_back": True,
    }
