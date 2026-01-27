"""
Quiz submission API endpoints.

This module handles quiz submission from the frontend, including validation,
calorie calculation, email normalization, and database persistence.

Endpoints:
    POST /api/quiz/submit - Submit completed 20-step quiz
    POST /api/quiz/save-progress - Save incremental quiz progress (T113 - authenticated users)
    GET /api/quiz/load-progress - Load saved quiz progress (T114 - authenticated users)
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from src.lib.database import get_db
from src.lib.email_utils import normalize_email
from src.services.auth_service import verify_access_token
from src.services.calorie_calculator import (
    calculate_calorie_target,
    Gender,
    ActivityLevel,
    Goal,
    ACTIVITY_MULTIPLIERS,
    GOAL_ADJUSTMENTS,
)
from src.models.quiz_response import QuizResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quiz", tags=["quiz"])


# Pydantic schemas for request/response validation
class BiometricsData(BaseModel):
    """Biometric data from Step 20."""

    age: int = Field(..., ge=18, le=100, description="User age in years")
    weight_kg: float = Field(..., ge=30, le=300, description="Weight in kilograms")
    height_cm: float = Field(..., ge=122, le=229, description="Height in centimeters")
    goal: str = Field(..., description="Fitness goal: weight_loss, maintenance, muscle_gain")

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, v: str) -> str:
        """Validate goal is one of the accepted values."""
        valid_goals = ["weight_loss", "maintenance", "muscle_gain"]
        if v not in valid_goals:
            raise ValueError(f"Goal must be one of: {', '.join(valid_goals)}")
        return v


class QuizData(BaseModel):
    """Complete quiz data structure matching frontend."""

    step_1: str = Field(..., description="Gender: male or female")
    step_2: str = Field(..., description="Activity level")
    step_3: List[str] = Field(default_factory=list, description="Poultry selections")
    step_4: List[str] = Field(default_factory=list, description="Fish & Seafood")
    step_5: List[str] = Field(default_factory=list, description="Low-Carb Vegetables")
    step_6: List[str] = Field(default_factory=list, description="Cruciferous Vegetables")
    step_7: List[str] = Field(default_factory=list, description="Leafy Greens")
    step_8: List[str] = Field(default_factory=list, description="Additional Vegetables")
    step_9: List[str] = Field(default_factory=list, description="Additional Proteins")
    step_10: List[str] = Field(default_factory=list, description="Organ Meats")
    step_11: List[str] = Field(default_factory=list, description="Berries")
    step_12: List[str] = Field(default_factory=list, description="Nuts & Seeds")
    step_13: List[str] = Field(default_factory=list, description="Herbs & Spices")
    step_14: List[str] = Field(default_factory=list, description="Fats & Oils")
    step_15: List[str] = Field(default_factory=list, description="Beverages")
    step_16: List[str] = Field(default_factory=list, description="Dairy & Alternatives")
    step_17: str = Field(default="", max_length=500, description="Dietary restrictions")
    step_18: str = Field(..., description="Meals per day")
    step_19: List[str] = Field(default_factory=list, description="Behavioral patterns")
    step_20: BiometricsData = Field(..., description="Biometric data")

    @field_validator("step_1")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        """Validate gender."""
        if v not in ["male", "female"]:
            raise ValueError("Gender must be 'male' or 'female'")
        return v

    @field_validator("step_2")
    @classmethod
    def validate_activity(cls, v: str) -> str:
        """Validate activity level."""
        valid_levels = [
            "sedentary",
            "lightly_active",
            "moderately_active",
            "very_active",
            "super_active",
        ]
        if v not in valid_levels:
            raise ValueError(f"Activity level must be one of: {', '.join(valid_levels)}")
        return v

    def get_total_food_items(self) -> int:
        """Calculate total number of food items selected (FR-Q-017)."""
        food_steps = [
            self.step_3,
            self.step_4,
            self.step_5,
            self.step_6,
            self.step_7,
            self.step_8,
            self.step_9,
            self.step_10,
            self.step_11,
            self.step_12,
            self.step_13,
            self.step_14,
            self.step_15,
            self.step_16,
        ]
        return sum(len(step) for step in food_steps)


class QuizSubmissionRequest(BaseModel):
    """Request body for quiz submission."""

    email: str = Field(..., description="User email for PDF delivery")
    quiz_data: QuizData = Field(..., description="Complete 20-step quiz data")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Basic email validation."""
        v = v.strip().lower()
        if "@" not in v or len(v) < 3:
            raise ValueError("Invalid email address")
        return v


class CalorieBreakdown(BaseModel):
    """Detailed calorie calculation breakdown for display."""

    bmr: float = Field(..., description="Basal Metabolic Rate (kcal/day)")
    tdee: float = Field(..., description="Total Daily Energy Expenditure (kcal/day)")
    activity_multiplier: float = Field(..., description="Activity level multiplier")
    goal_adjustment: int = Field(..., description="Goal-based calorie adjustment (kcal/day)")
    goal_adjusted: float = Field(..., description="TDEE + goal adjustment (kcal/day)")
    final_target: int = Field(..., description="Final calorie target after clamping (kcal/day)")
    clamped: bool = Field(..., description="Whether target was clamped to minimum")
    warning: Optional[str] = Field(None, description="Warning message if clamped")


class QuizSubmissionResponse(BaseModel):
    """Response after successful quiz submission."""

    success: bool = True
    quiz_id: str = Field(..., description="Unique quiz response ID")
    calorie_target: int = Field(..., description="Calculated daily calorie target")
    calorie_breakdown: CalorieBreakdown = Field(..., description="Detailed calorie calculation breakdown")
    message: str = "Quiz submitted successfully"


@router.post("/submit", response_model=QuizSubmissionResponse)
async def submit_quiz(
    request: QuizSubmissionRequest,
    db: AsyncSession = Depends(get_db),
) -> QuizSubmissionResponse:
    """
    Submit completed 20-step quiz and calculate calorie target.

    This endpoint:
    1. Validates quiz data (Pydantic handles this)
    2. Validates food item count (FR-Q-017: minimum 10 items)
    3. Normalizes email address to prevent duplicates
    4. Calculates calorie target using Mifflin-St Jeor equation
    5. Saves quiz response to database
    6. Returns quiz ID and calorie target

    Args:
        request: Quiz submission data including email and quiz responses
        db: Database session (injected dependency)

    Returns:
        QuizSubmissionResponse with quiz_id and calculated calorie_target

    Raises:
        HTTPException 400: Invalid quiz data or insufficient food items
        HTTPException 500: Database or calculation errors
    """
    try:
        # FR-Q-017: Validate minimum food item count (10 items)
        total_food_items = request.quiz_data.get_total_food_items()
        if total_food_items < 10:
            raise HTTPException(
                status_code=400,
                detail=f"Please select at least 10 food items. Currently selected: {total_food_items}",
            )

        # Normalize email for duplicate detection (FR-P-010)
        normalized_email = normalize_email(request.email)

        # Calculate calorie target using Mifflin-St Jeor equation
        biometrics = request.quiz_data.step_20

        # Map string values to enum types
        gender = Gender.MALE if request.quiz_data.step_1 == "male" else Gender.FEMALE
        activity_map = {
            "sedentary": ActivityLevel.SEDENTARY,
            "lightly_active": ActivityLevel.LIGHTLY_ACTIVE,
            "moderately_active": ActivityLevel.MODERATELY_ACTIVE,
            "very_active": ActivityLevel.VERY_ACTIVE,
            "super_active": ActivityLevel.SUPER_ACTIVE,
        }
        activity = activity_map[request.quiz_data.step_2]

        goal_map = {
            "weight_loss": Goal.WEIGHT_LOSS,
            "maintenance": Goal.MAINTENANCE,
            "muscle_gain": Goal.MUSCLE_GAIN,
        }
        goal = goal_map[biometrics.goal]

        # Calculate calorie target
        calorie_result = calculate_calorie_target(
            age=biometrics.age,
            weight_kg=biometrics.weight_kg,
            height_cm=biometrics.height_cm,
            gender=gender,
            activity_level=activity,
            goal=goal,
        )

        # Convert quiz_data to dict for JSONB storage
        quiz_data_dict = request.quiz_data.model_dump()

        # Create quiz response record
        quiz_response = QuizResponse(
            id=str(uuid.uuid4()),
            user_id=None,  # NULL for unauthenticated flow (hybrid auth - FR-Q-020)
            email=request.email,
            normalized_email=normalized_email,
            quiz_data=quiz_data_dict,
            calorie_target=calorie_result.final_target,
            created_at=datetime.utcnow(),
            payment_id=None,  # Will be set by webhook handler
            pdf_delivered_at=None,  # Will be set after PDF delivery
        )

        # Save to database
        db.add(quiz_response)
        await db.commit()
        await db.refresh(quiz_response)

        logger.info(
            f"Quiz submitted successfully: quiz_id={quiz_response.id}, "
            f"email={request.email}, calorie_target={calorie_result.final_target}"
        )

        # Build detailed calorie breakdown for display
        breakdown = CalorieBreakdown(
            bmr=calorie_result.bmr,
            tdee=calorie_result.tdee,
            activity_multiplier=ACTIVITY_MULTIPLIERS[activity],
            goal_adjustment=GOAL_ADJUSTMENTS[goal],
            goal_adjusted=calorie_result.goal_adjusted,
            final_target=calorie_result.final_target,
            clamped=calorie_result.clamped,
            warning=calorie_result.warning,
        )

        return QuizSubmissionResponse(
            quiz_id=quiz_response.id,
            calorie_target=calorie_result.final_target,
            calorie_breakdown=breakdown,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except IntegrityError as e:
        # Database constraint violation
        await db.rollback()
        logger.error(f"Database integrity error during quiz submission: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to save quiz data. Please try again.",
        )

    except ValueError as e:
        # Validation errors from calorie calculator or email normalization
        logger.error(f"Validation error during quiz submission: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        # Unexpected errors
        await db.rollback()
        logger.error(f"Unexpected error during quiz submission: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later.",
        )


# =============================================================================
# QUIZ PROGRESS SAVING (T113, T114)
# =============================================================================


class SaveProgressRequest(BaseModel):
    """Request body for saving quiz progress (T113)."""

    current_step: int = Field(..., ge=1, le=20, description="Current quiz step (1-20)")
    quiz_data: Dict[str, Any] = Field(..., description="Partial or complete quiz data")


class SaveProgressResponse(BaseModel):
    """Response after saving quiz progress."""

    success: bool = True
    saved_at: str = Field(..., description="ISO 8601 timestamp of save")
    current_step: int = Field(..., description="Current step that was saved")


class LoadProgressResponse(BaseModel):
    """Response when loading saved quiz progress."""

    quiz_data: Dict[str, Any] = Field(..., description="Partial or complete quiz data")
    current_step: int = Field(..., description="Step user was on when they last saved")
    saved_at: str = Field(..., description="ISO 8601 timestamp of last save")


def get_current_user(authorization: str = Header(None)) -> Dict[str, Any]:
    """
    Dependency to extract and verify user from JWT access token.

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        Dict with user_id and email from JWT payload

    Raises:
        HTTPException 401: Missing, invalid, or expired token
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header",
        )

    # Extract token from "Bearer <token>" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected: Bearer <token>",
        )

    token = parts[1]

    # Verify token
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    return {
        "user_id": payload.get("sub"),
        "email": payload.get("email"),
    }


@router.post("/save-progress", response_model=SaveProgressResponse)
async def save_quiz_progress(
    request: SaveProgressRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SaveProgressResponse:
    """
    Save incremental quiz progress for authenticated users (T113).

    Enables cross-device sync by storing partial quiz data to database.
    This endpoint requires authentication via JWT access token.

    If user has existing quiz progress, it will be updated. Otherwise, a new
    record is created.

    Args:
        request: Quiz progress data (current step + partial quiz data)
        db: Database session (injected)
        current_user: Authenticated user info from JWT (injected)

    Returns:
        SaveProgressResponse with success status and timestamp

    Raises:
        HTTPException 401: Not authenticated or invalid token
        HTTPException 500: Database errors
    """
    try:
        user_id = current_user["user_id"]
        user_email = current_user["email"]

        # Check if user has existing quiz progress (async)
        stmt = (
            select(QuizResponse)
            .where(
                QuizResponse.user_id == user_id,
                QuizResponse.payment_id == None,  # Only in-progress quizzes (not submitted)
            )
            .order_by(QuizResponse.created_at.desc())
        )
        result = await db.execute(stmt)
        existing_progress = result.scalar_one_or_none()

        saved_at = datetime.utcnow()

        if existing_progress:
            # Update existing progress
            existing_progress.quiz_data = request.quiz_data
            existing_progress.updated_at = saved_at

            logger.info(
                f"Updated quiz progress for user {user_id} at step {request.current_step}"
            )
        else:
            # Create new progress record
            quiz_response = QuizResponse(
                id=str(uuid.uuid4()),
                user_id=user_id,
                email=user_email,
                normalized_email=normalize_email(user_email),
                quiz_data=request.quiz_data,
                calorie_target=0,  # Will be calculated on final submission
                created_at=saved_at,
                payment_id=None,  # NULL indicates in-progress (not submitted)
                pdf_delivered_at=None,
            )

            db.add(quiz_response)

            logger.info(
                f"Created new quiz progress for user {user_id} at step {request.current_step}"
            )

        await db.commit()

        return SaveProgressResponse(
            saved_at=saved_at.isoformat(),
            current_step=request.current_step,
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        # Unexpected errors
        await db.rollback()
        logger.error(f"Unexpected error saving quiz progress: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to save quiz progress. Please try again.",
        )


@router.get("/load-progress", response_model=LoadProgressResponse)
async def load_quiz_progress(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> LoadProgressResponse:
    """
    Load saved quiz progress for authenticated users (T114).

    Enables cross-device resume by retrieving user's last saved quiz state.
    Returns the most recent in-progress quiz (payment_id is NULL).

    Args:
        db: Database session (injected)
        current_user: Authenticated user info from JWT (injected)

    Returns:
        LoadProgressResponse with quiz data and current step

    Raises:
        HTTPException 401: Not authenticated or invalid token
        HTTPException 404: No saved progress found
        HTTPException 500: Database errors
    """
    try:
        user_id = current_user["user_id"]

        # Find most recent in-progress quiz (async)
        stmt = (
            select(QuizResponse)
            .where(
                QuizResponse.user_id == user_id,
                QuizResponse.payment_id == None,  # Only in-progress quizzes
            )
            .order_by(QuizResponse.created_at.desc())
        )
        result = await db.execute(stmt)
        saved_progress = result.scalar_one_or_none()

        if not saved_progress:
            raise HTTPException(
                status_code=404,
                detail="No saved quiz progress found",
            )

        # Infer current step from quiz_data keys
        # Count how many steps have data
        quiz_data = saved_progress.quiz_data
        current_step = 1
        for i in range(1, 21):
            step_key = f"step_{i}"
            if step_key in quiz_data and quiz_data[step_key]:
                current_step = i

        logger.info(
            f"Loaded quiz progress for user {user_id}, step {current_step}"
        )

        return LoadProgressResponse(
            quiz_data=quiz_data,
            current_step=current_step,
            saved_at=saved_progress.created_at.isoformat(),
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error loading quiz progress: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to load quiz progress. Please try again.",
        )
