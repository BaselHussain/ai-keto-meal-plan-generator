"""
Calorie calculator service using the Mifflin-St Jeor equation.

This module provides functionality to calculate daily calorie targets based on
user demographics, activity level, and fitness goals. It implements the
Mifflin-St Jeor equation for Basal Metabolic Rate (BMR) calculation and applies
activity multipliers and goal adjustments to determine Total Daily Energy
Expenditure (TDEE) and final calorie targets.

References:
    - Mifflin-St Jeor Equation: MD Mifflin et al. (1990)
    - FR-C-004: Calorie Target Calculation requirement
"""

import logging
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Gender(str, Enum):
    """User gender for BMR calculation."""

    MALE = "male"
    FEMALE = "female"


class ActivityLevel(str, Enum):
    """Physical activity level with associated TDEE multipliers.

    Activity levels range from sedentary (little to no exercise) to super active
    (very hard exercise or physical job). Each level has a multiplier used to
    calculate Total Daily Energy Expenditure (TDEE) from BMR.
    """

    SEDENTARY = "sedentary"  # Little to no exercise
    LIGHTLY_ACTIVE = "lightly_active"  # Exercise 1-3 days/week
    MODERATELY_ACTIVE = "moderately_active"  # Exercise 3-5 days/week
    VERY_ACTIVE = "very_active"  # Exercise 6-7 days/week
    SUPER_ACTIVE = "super_active"  # Very hard exercise or physical job


class Goal(str, Enum):
    """Fitness goal with associated calorie adjustments.

    Goals define the calorie surplus or deficit relative to TDEE:
    - WEIGHT_LOSS: Creates a calorie deficit for fat loss
    - MUSCLE_GAIN: Creates a calorie surplus for muscle building
    - MAINTENANCE: Maintains current weight
    """

    WEIGHT_LOSS = "weight_loss"
    MUSCLE_GAIN = "muscle_gain"
    MAINTENANCE = "maintenance"


# Activity level multipliers for TDEE calculation
ACTIVITY_MULTIPLIERS: dict[ActivityLevel, float] = {
    ActivityLevel.SEDENTARY: 1.2,
    ActivityLevel.LIGHTLY_ACTIVE: 1.375,
    ActivityLevel.MODERATELY_ACTIVE: 1.55,
    ActivityLevel.VERY_ACTIVE: 1.725,
    ActivityLevel.SUPER_ACTIVE: 1.9,
}

# Goal-based calorie adjustments (kcal/day)
GOAL_ADJUSTMENTS: dict[Goal, int] = {
    Goal.WEIGHT_LOSS: -400,  # Moderate deficit for sustainable fat loss
    Goal.MUSCLE_GAIN: 250,  # Modest surplus for lean muscle gain
    Goal.MAINTENANCE: 0,  # No adjustment
}

# Minimum calorie floors to prevent unhealthy undereating
CALORIE_FLOOR_MALE = 1500
CALORIE_FLOOR_FEMALE = 1200


class CalorieCalculation(BaseModel):
    """Result of calorie target calculation.

    Attributes:
        bmr: Basal Metabolic Rate in kcal/day (calories burned at rest)
        tdee: Total Daily Energy Expenditure in kcal/day (BMR × activity multiplier)
        goal_adjusted: TDEE adjusted for fitness goal (before clamping)
        final_target: Final calorie target after applying safety floors
        clamped: Whether the target was clamped to minimum safe value
        warning: Optional warning message if clamping occurred
    """

    bmr: float = Field(..., description="Basal Metabolic Rate (kcal/day)")
    tdee: float = Field(..., description="Total Daily Energy Expenditure (kcal/day)")
    goal_adjusted: float = Field(
        ..., description="TDEE adjusted for goal (kcal/day)"
    )
    final_target: int = Field(
        ..., description="Final calorie target after clamping (kcal/day)"
    )
    clamped: bool = Field(
        ..., description="Whether the target was clamped to minimum"
    )
    warning: Optional[str] = Field(
        None, description="Warning message if clamping occurred"
    )


def calculate_calorie_target(
    gender: Gender,
    age: int,
    weight_kg: float,
    height_cm: float,
    activity_level: ActivityLevel,
    goal: Goal,
) -> CalorieCalculation:
    """Calculate daily calorie target using Mifflin-St Jeor equation.

    This function implements a multi-step calculation:
    1. Calculate BMR using the Mifflin-St Jeor equation
    2. Apply activity multiplier to get TDEE
    3. Adjust for fitness goal
    4. Enforce minimum calorie floors for safety

    The Mifflin-St Jeor equation is considered one of the most accurate
    predictors of resting metabolic rate (RMR) and is widely used in
    nutritional planning.

    Args:
        gender: User's biological gender (affects BMR calculation)
        age: User's age in years
        weight_kg: User's weight in kilograms
        height_cm: User's height in centimeters
        activity_level: User's physical activity level
        goal: User's fitness goal (weight loss, muscle gain, or maintenance)

    Returns:
        CalorieCalculation object containing BMR, TDEE, goal-adjusted calories,
        final target, and clamping information.

    Example:
        >>> result = calculate_calorie_target(
        ...     gender=Gender.MALE,
        ...     age=30,
        ...     weight_kg=80,
        ...     height_cm=180,
        ...     activity_level=ActivityLevel.MODERATELY_ACTIVE,
        ...     goal=Goal.WEIGHT_LOSS
        ... )
        >>> result.final_target
        2247

    Notes:
        - Minimum calorie floors: 1500 kcal (male), 1200 kcal (female)
        - If goal-adjusted target falls below minimum, it will be clamped
          and a warning will be issued
        - All clamping events are logged for monitoring
    """
    # Step 1: Calculate Basal Metabolic Rate (BMR) using Mifflin-St Jeor
    if gender == Gender.MALE:
        # Male formula: (10 × weight_kg) + (6.25 × height_cm) - (5 × age) + 5
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:
        # Female formula: (10 × weight_kg) + (6.25 × height_cm) - (5 × age) - 161
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

    # Step 2: Calculate Total Daily Energy Expenditure (TDEE)
    activity_multiplier = ACTIVITY_MULTIPLIERS[activity_level]
    tdee = bmr * activity_multiplier

    # Step 3: Apply goal adjustment
    goal_adjustment = GOAL_ADJUSTMENTS[goal]
    goal_adjusted = tdee + goal_adjustment

    # Step 4: Enforce calorie floors
    calorie_floor = CALORIE_FLOOR_MALE if gender == Gender.MALE else CALORIE_FLOOR_FEMALE

    clamped = False
    warning = None
    final_target = int(round(goal_adjusted))

    if goal_adjusted < calorie_floor:
        clamped = True
        final_target = calorie_floor
        warning = (
            f"Calculated target ({int(round(goal_adjusted))} kcal) is below "
            f"the minimum safe threshold of {calorie_floor} kcal. "
            f"Target has been adjusted to {calorie_floor} kcal for health safety."
        )

        # Log clamping event for monitoring
        logger.warning(
            "Calorie target clamped to minimum safe value",
            extra={
                "gender": gender.value,
                "age": age,
                "weight_kg": weight_kg,
                "height_cm": height_cm,
                "activity_level": activity_level.value,
                "goal": goal.value,
                "bmr": round(bmr, 1),
                "tdee": round(tdee, 1),
                "goal_adjusted": round(goal_adjusted, 1),
                "calorie_floor": calorie_floor,
                "final_target": final_target,
            }
        )

    return CalorieCalculation(
        bmr=round(bmr, 1),
        tdee=round(tdee, 1),
        goal_adjusted=round(goal_adjusted, 1),
        final_target=final_target,
        clamped=clamped,
        warning=warning,
    )
