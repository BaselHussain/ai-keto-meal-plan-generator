"""
QuizResponse Model

Temporary storage for 20-step quiz responses with automatic data retention policies.

Schema Design:
- Supports both authenticated (user_id populated) and unauthenticated (user_id NULL) flows
- Email normalization prevents Gmail alias abuse (dots, plus signs)
- JSONB storage for flexible quiz data structure with efficient querying
- Calorie target pre-calculated using Mifflin-St Jeor equation for performance
- Payment tracking via Paddle webhook integration

Indexes:
- idx_quiz_normalized_email: Fast lookups for duplicate email detection
- idx_quiz_created_at: Efficient cleanup job queries (7-day unpaid retention)
- idx_quiz_pdf_delivered_at: 24-hour paid retention policy enforcement

Relationships:
- user: Many-to-one relationship with User (nullable for unauthenticated flow)

Data Retention Policies:
- Paid responses (payment_id NOT NULL): Deleted 24 hours after pdf_delivered_at
- Unpaid responses (payment_id NULL): Deleted 7 days after created_at
- Automatic cleanup via scheduled cleanup job (see T092-T095)
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.lib.database import Base


class QuizResponse(Base):
    """
    Quiz response entity storing 20-step keto quiz answers.

    Supports both authenticated and unauthenticated quiz submissions.
    Quiz data is stored as JSONB for flexibility and efficient querying.

    Attributes:
        id: Unique quiz response identifier (UUID as string)
        user_id: Optional reference to authenticated user (NULL for guests)
        email: Original email address (for communications and PDF delivery)
        normalized_email: Normalized email for duplicate detection
        quiz_data: Full 20-step quiz responses (JSONB structure below)
        calorie_target: Pre-calculated daily calorie target (Mifflin-St Jeor)
        created_at: Quiz submission timestamp (UTC)
        payment_id: Paddle payment ID (NULL until webhook confirmation)
        pdf_delivered_at: PDF email delivery timestamp (triggers 24h retention)

    Quiz Data JSONB Structure:
        {
            "step_1": "female",                              # Gender
            "step_2": "moderately_active",                   # Activity level
            "step_3": ["chicken", "turkey"],                 # Poultry preferences
            "step_4": ["salmon", "tuna"],                    # Fish preferences
            "step_5": ["avocado", "zucchini", "bell_pepper"], # Vegetables
            "step_6": ["broccoli", "cauliflower"],           # Cruciferous vegetables
            "step_7": ["spinach", "arugula"],                # Leafy greens
            "step_8": [],                                    # Nuts/seeds (empty if none)
            "step_9": ["shrimp"],                            # Seafood
            "step_10": [],                                   # Eggs/egg products
            "step_11": ["blueberries", "strawberries"],      # Low-carb fruits
            "step_12": [],                                   # Keto sweeteners
            "step_13": [],                                   # Condiments/sauces
            "step_14": ["olive_oil", "coconut_oil", "butter"], # Fats/oils
            "step_15": ["water", "coffee", "tea"],           # Beverages
            "step_16": ["cheese", "greek_yogurt"],           # Dairy products
            "step_17": "No dairy from cows, goat dairy OK. Prefer coconut-based alternatives.", # Special notes
            "step_18": "3_meals",                            # Meals per day
            "step_19": ["prefer_salty", "struggle_appetite_control"], # Preferences/challenges
            "step_20": {                                     # Biometric data
                "age": 35,
                "weight_kg": 65,
                "height_cm": 165,
                "goal": "weight_loss"  # Options: weight_loss, maintenance, muscle_gain
            }
        }

    Calorie Calculation (Mifflin-St Jeor Equation):
        BMR (female) = (10 × weight_kg) + (6.25 × height_cm) - (5 × age) - 161
        BMR (male) = (10 × weight_kg) + (6.25 × height_cm) - (5 × age) + 5
        TDEE = BMR × activity_multiplier
        Target = TDEE × goal_multiplier
    """

    __tablename__ = "quiz_responses"

    # Primary key (UUID as string)
    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique quiz response identifier (UUID)"
    )

    # Foreign key to users (nullable for unauthenticated flow)
    user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        doc="User ID for authenticated quiz submissions (NULL for guests)"
    )

    # Email fields
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Original email address for communications and PDF delivery"
    )

    normalized_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Normalized email for duplicate detection (prevents Gmail alias abuse)"
    )

    # Quiz data (JSONB for flexible schema)
    quiz_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        doc="Full 20-step quiz responses (see class docstring for structure)"
    )

    # Calculated calorie target
    calorie_target: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Daily calorie target calculated using Mifflin-St Jeor equation"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="Quiz submission timestamp (UTC)"
    )

    # Payment tracking
    payment_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Paddle payment ID (NULL until payment webhook confirmation)"
    )

    # PDF delivery tracking
    pdf_delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="PDF email delivery timestamp (triggers 24-hour retention policy)"
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="quiz_responses",
        lazy="joined",
        doc="Related user account (NULL for unauthenticated submissions)"
    )

    # Table-level constraints and indexes
    __table_args__ = (
        Index("idx_quiz_normalized_email", "normalized_email"),
        Index("idx_quiz_created_at", "created_at"),
        Index("idx_quiz_pdf_delivered_at", "pdf_delivered_at"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<QuizResponse(id={self.id}, email={self.email}, "
            f"user_id={self.user_id}, payment_id={self.payment_id}, "
            f"created_at={self.created_at})>"
        )
