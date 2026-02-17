"""
Pydantic schemas for API request/response validation.

This module exports all schema models for quiz submission, meal plan generation,
authentication, and account recovery endpoints.

All schemas are based on OpenAPI contracts in:
- specs/001-keto-meal-plan-generator/contracts/quiz-api.yaml
- specs/001-keto-meal-plan-generator/contracts/ai-generation.yaml
- specs/001-keto-meal-plan-generator/contracts/recovery-api.yaml
"""

from .auth import (
    CheckoutInitiateRequest,
    CheckoutInitiateResponse,
    EmailVerificationCodeRequest,
    EmailVerificationCodeResponse,
    EmailVerificationRequest,
    EmailVerificationResponse,
)
from .common import (
    ErrorResponse,
    ValidationErrorResponse,
)
from .meal_plan import (
    DayMealPlan,
    GenerationRequest,
    GenerationResponse,
    Ingredient,
    KetoTip,
    Meal,
    MealPlanStructure,
    MealPlanValidationRequest,
    PreferencesSummary,
    ValidationError,
    ValidationResult,
    WeeklyShoppingList,
)
from .quiz import (
    BiometricsData,
    QuizProgressSaveRequest,
    QuizProgressSaveResponse,
    QuizSubmission,
    QuizSubmissionResponse,
)
from .recovery import (
    AccountCreateRequest,
    AccountCreateResponse,
    DashboardMealPlan,
    DashboardResponse,
    DownloadPDFResponse,
    MagicLinkVerifyResponse,
    RecoverPlanRequest,
    RecoverPlanResponse,
)

__all__ = [
    # Auth schemas (email verification and checkout)
    "EmailVerificationCodeRequest",
    "EmailVerificationCodeResponse",
    "EmailVerificationRequest",
    "EmailVerificationResponse",
    "CheckoutInitiateRequest",
    "CheckoutInitiateResponse",
    # Common error schemas
    "ErrorResponse",
    "ValidationErrorResponse",
    # Quiz schemas (20-step quiz submission and progress)
    "BiometricsData",
    "QuizSubmission",
    "QuizSubmissionResponse",
    "QuizProgressSaveRequest",
    "QuizProgressSaveResponse",
    # Meal plan schemas (AI generation and validation)
    "PreferencesSummary",
    "GenerationRequest",
    "GenerationResponse",
    "Ingredient",
    "Meal",
    "DayMealPlan",
    "WeeklyShoppingList",
    "MealPlanStructure",
    "MealPlanValidationRequest",
    "ValidationResult",
    "ValidationError",
    # Recovery schemas (magic links and account management)
    "RecoverPlanRequest",
    "RecoverPlanResponse",
    "MagicLinkVerifyResponse",
    "DownloadPDFResponse",
    "AccountCreateRequest",
    "AccountCreateResponse",
    "DashboardMealPlan",
    "DashboardResponse",
]
