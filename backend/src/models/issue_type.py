"""
Issue Type Enum
Defines the valid issue types for manual resolution queue entries.

File: backend/src/models/issue_type.py
"""
from enum import Enum


class IssueType(str, Enum):
    """
    Manual resolution issue type enum.

    Values:
        MISSING_QUIZ_DATA: Quiz response not found during meal plan generation
        AI_VALIDATION_FAILED: Meal plan validation failed after multiple attempts
        EMAIL_DELIVERY_FAILED: Email delivery failed after all retry attempts
        MANUAL_REFUND_REQUIRED: Refund requires admin review (pattern detected)
    """
    MISSING_QUIZ_DATA = "missing_quiz_data"
    AI_VALIDATION_FAILED = "ai_validation_failed"
    EMAIL_DELIVERY_FAILED = "email_delivery_failed"
    MANUAL_REFUND_REQUIRED = "manual_refund_required"


# For backward compatibility where string values are expected
ISSUE_TYPE_CHOICES = [
    IssueType.MISSING_QUIZ_DATA,
    IssueType.AI_VALIDATION_FAILED,
    IssueType.EMAIL_DELIVERY_FAILED,
    IssueType.MANUAL_REFUND_REQUIRED,
]