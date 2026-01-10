"""
SQLAlchemy Models

This package contains all SQLAlchemy ORM models for the application.

Models are defined using SQLAlchemy 2.0+ async patterns with:
- Declarative Base from src.lib.database
- Proper type hints for all columns and relationships
- Indexes for optimized query performance
- Timestamps (created_at, updated_at) on all entities

Available Models:
- User: Optional user accounts for dashboard access and cross-device sync
- QuizResponse: Temporary storage for 20-step quiz responses with retention policies
- MealPlan: Generated meal plans with PDF storage, payment tracking, and preferences
- PaymentTransaction: Payment transaction metadata for analytics, support, and compliance
- ManualResolution: Queue for failed operations requiring manual admin intervention
- MagicLinkToken: One-time authentication tokens for passwordless email login (24h retention)
- EmailBlacklist: Chargeback prevention list with 90-day retention for normalized emails

Usage:
    from src.models import User, QuizResponse, MealPlan, PaymentTransaction, ManualResolution, MagicLinkToken, EmailBlacklist
    from sqlalchemy import select

    async with get_db() as session:
        result = await session.execute(select(User).where(User.email == "user@example.com"))
        user = result.scalar_one_or_none()
"""

from src.models.user import User
from src.models.quiz_response import QuizResponse
from src.models.meal_plan import MealPlan
from src.models.payment_transaction import PaymentTransaction
from src.models.manual_resolution import ManualResolution
from src.models.magic_link import MagicLinkToken
from src.models.email_blacklist import EmailBlacklist

__all__ = [
    "User",
    "QuizResponse",
    "MealPlan",
    "PaymentTransaction",
    "ManualResolution",
    "MagicLinkToken",
    "EmailBlacklist",
]
