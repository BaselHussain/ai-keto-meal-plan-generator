"""
Common Pydantic schemas used across multiple endpoints.

Error response models for consistent API error formatting.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """
    Standard error response format for all API endpoints.

    Used for client errors (4xx) and server errors (5xx).
    """
    error: str = Field(
        min_length=1,
        description="Human-readable error message",
        examples=["Invalid quiz data"]
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error context (field-level errors, debugging info)",
        examples=[{"field": "email", "issue": "Invalid email format"}]
    )


class ValidationErrorResponse(BaseModel):
    """
    Validation error response for AI-generated content validation failures.

    Used when meal plan validation fails (keto compliance or structure).
    Functional requirements: FR-A-007, FR-A-015
    """
    error: str = Field(
        min_length=1,
        description="High-level error description",
        examples=["Keto compliance validation failed"]
    )
    validation_errors: List[str] = Field(
        default_factory=list,
        description="List of specific validation failures",
        examples=[["Day 5 exceeds 30g carbs (32g)", "Missing dinner for Day 12"]]
    )
    retry_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of retries attempted before final failure",
        examples=[2]
    )
