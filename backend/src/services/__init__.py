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
from .email_verification import (
    generate_verification_code,
    send_verification_code,
    verify_code,
    is_email_verified,
    clear_verification,
    get_verification_status,
)

__all__ = [
    "Gender",
    "ActivityLevel",
    "Goal",
    "CalorieCalculation",
    "calculate_calorie_target",
    "generate_verification_code",
    "send_verification_code",
    "verify_code",
    "is_email_verified",
    "clear_verification",
    "get_verification_status",
]
