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
from .meal_plan_generator import (
    generate_meal_plan,
    validate_keto_compliance,
    validate_structural_integrity,
    MealPlanGenerationError,
)
from .pdf_generator import (
    generate_pdf,
    validate_pdf,
    PDFGenerationError,
)
from .blob_storage import (
    upload_pdf_to_vercel_blob,
    generate_signed_download_url,
    delete_blob,
    delete_blobs_batch,
    BlobStorageError,
)
from .delivery_orchestrator import (
    orchestrate_meal_plan_delivery,
    retry_failed_delivery,
    rollback_failed_delivery,
    DeliveryOrchestrationError,
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
    "generate_meal_plan",
    "validate_keto_compliance",
    "validate_structural_integrity",
    "MealPlanGenerationError",
    "generate_pdf",
    "validate_pdf",
    "PDFGenerationError",
    "upload_pdf_to_vercel_blob",
    "generate_signed_download_url",
    "delete_blob",
    "delete_blobs_batch",
    "BlobStorageError",
    "orchestrate_meal_plan_delivery",
    "retry_failed_delivery",
    "rollback_failed_delivery",
    "DeliveryOrchestrationError",
]
