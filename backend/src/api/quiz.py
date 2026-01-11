"""
Quiz submission API endpoints.

This module handles quiz submission from the frontend, including validation,
calorie calculation, email normalization, and database persistence.

Endpoints:
    POST /api/quiz/submit - Submit completed 20-step quiz
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.lib.database import get_db
from src.lib.email_utils import normalize_email
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
    db: Session = Depends(get_db),
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
