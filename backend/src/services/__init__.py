"""
Service layer for business logic.

This package contains service modules that encapsulate business logic
and calculations for the meal plan generator application.
"""

from .calorie_calculator import (
    ActivityLevel,
    CalorieCalculation,
    Gender,
    Goal,
    calculate_calorie_target,
)

__all__ = [
    "Gender",
    "ActivityLevel",
    "Goal",
    "CalorieCalculation",
    "calculate_calorie_target",
]
