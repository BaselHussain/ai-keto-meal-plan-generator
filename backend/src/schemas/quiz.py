"""
Pydantic schemas for quiz submission and progress saving.

Based on: specs/001-keto-meal-plan-generator/contracts/quiz-api.yaml
Functional requirements: FR-Q-001 to FR-Q-020
"""

from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator


class BiometricsData(BaseModel):
    """
    User biometric data for calorie calculation (Mifflin-St Jeor formula).

    Functional requirements: FR-C-001 to FR-C-006
    """
    age: int = Field(
        ge=18,
        le=100,
        description="User's age in years",
        examples=[35]
    )
    weight_kg: float = Field(
        ge=13.6,
        le=227.0,
        description="User's current weight in kilograms (30-500 lbs)",
        examples=[70.0]
    )
    height_cm: float = Field(
        ge=122.0,
        le=229.0,
        description="User's height in centimeters (4-7.5 feet)",
        examples=[170.0]
    )
    goal: Literal["weight_loss", "muscle_gain", "maintenance"] = Field(
        description="User's fitness goal",
        examples=["weight_loss"]
    )


class QuizSubmission(BaseModel):
    """
    Complete 20-step quiz submission payload.

    Supports both authenticated and unauthenticated flows:
    - Unauthenticated: Quiz saved to DB on submission
    - Authenticated: Incremental saves enabled via /quiz/save-progress

    Functional requirements: FR-Q-001 to FR-Q-018
    """
    email: EmailStr = Field(
        description="User's email address for PDF delivery and verification",
        examples=["user@example.com"]
    )

    # Step 1: Gender
    step_1: Literal["male", "female"] = Field(
        description="User's biological gender for calorie calculation",
        examples=["female"]
    )

    # Step 2: Activity level
    step_2: Literal[
        "sedentary",
        "lightly_active",
        "moderately_active",
        "very_active",
        "super_active"
    ] = Field(
        description="Physical activity level for calorie adjustment",
        examples=["moderately_active"]
    )

    # Step 3: Meat preferences
    step_3: Optional[List[Literal["beef", "lamb", "chicken", "pork", "turkey"]]] = Field(
        default=None,
        description="Preferred meat types (empty array if none)",
        examples=[["chicken", "turkey"]]
    )

    # Step 4: Fish preferences
    step_4: Optional[List[Literal["tuna", "salmon", "mackerel", "cod", "pollock"]]] = Field(
        default=None,
        description="Preferred fish types (empty array if none)",
        examples=[["salmon", "cod"]]
    )

    # Step 5: Vegetables
    step_5: Optional[List[str]] = Field(
        default=None,
        description="Preferred vegetables (free text from multi-select)",
        examples=[["spinach", "broccoli", "cauliflower"]]
    )

    # Step 6: Cruciferous vegetables
    step_6: Optional[List[str]] = Field(
        default=None,
        description="Preferred cruciferous vegetables",
        examples=[["broccoli", "brussels sprouts"]]
    )

    # Step 7: Leafy greens
    step_7: Optional[List[str]] = Field(
        default=None,
        description="Preferred leafy greens",
        examples=[["kale", "spinach", "arugula"]]
    )

    # Step 8: Legumes
    step_8: Optional[List[str]] = Field(
        default=None,
        description="Preferred legumes (limited on keto)",
        examples=[["edamame"]]
    )

    # Step 9: Shellfish
    step_9: Optional[List[str]] = Field(
        default=None,
        description="Preferred shellfish types",
        examples=[["shrimp", "crab", "lobster"]]
    )

    # Step 10: Fruits
    step_10: Optional[List[str]] = Field(
        default=None,
        description="Preferred fruits (limited on keto)",
        examples=[["avocado", "tomato"]]
    )

    # Step 11: Berries
    step_11: Optional[List[str]] = Field(
        default=None,
        description="Preferred berries (keto-friendly in moderation)",
        examples=[["strawberries", "blueberries"]]
    )

    # Step 12: Grains
    step_12: Optional[List[str]] = Field(
        default=None,
        description="Preferred grains (typically avoided on keto)",
        examples=[[]]
    )

    # Step 13: Other carbs
    step_13: Optional[List[str]] = Field(
        default=None,
        description="Other carbohydrate sources",
        examples=[["sweet potato"]]
    )

    # Step 14: Cooking fats
    step_14: Optional[List[str]] = Field(
        default=None,
        description="Preferred cooking fats and oils",
        examples=[["olive oil", "coconut oil", "butter"]]
    )

    # Step 15: Beverages
    step_15: Optional[List[str]] = Field(
        default=None,
        description="Preferred beverages",
        examples=[["water", "coffee", "tea"]]
    )

    # Step 16: Dairy products
    step_16: Optional[List[str]] = Field(
        default=None,
        description="Preferred dairy products",
        examples=[["cheese", "heavy cream", "greek yogurt"]]
    )

    # Step 17: Dietary restrictions (free text with privacy notice)
    step_17: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Free-text dietary restrictions and allergies",
        examples=["No dairy from cows. Prefer coconut-based alternatives."]
    )

    # Step 18: Eating frequency
    step_18: Optional[Literal["1_meal", "2_meals", "3_meals", "4_plus_meals"]] = Field(
        default=None,
        description="Preferred number of meals per day",
        examples=["3_meals"]
    )

    # Step 19: Personal traits
    step_19: Optional[List[Literal[
        "tired_waking_up",
        "frequent_cravings",
        "prefer_salty",
        "prefer_sweet",
        "struggle_appetite_control"
    ]]] = Field(
        default=None,
        description="Personal habits and preferences",
        examples=[["prefer_salty", "struggle_appetite_control"]]
    )

    # Step 20: Biometrics and goal
    step_20: BiometricsData = Field(
        description="Biometric data for calorie calculation"
    )

    @field_validator("step_17")
    @classmethod
    def validate_dietary_restrictions(cls, v: Optional[str]) -> Optional[str]:
        """Ensure dietary restrictions don't contain sensitive PII beyond expected info."""
        if v and len(v.strip()) == 0:
            return None
        return v


class QuizSubmissionResponse(BaseModel):
    """
    Response after successful quiz submission.

    Functional requirements: FR-Q-018, FR-Q-019
    """
    quiz_id: UUID = Field(
        description="Unique identifier for the submitted quiz",
        examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
    )
    email: EmailStr = Field(
        description="Email address where verification code will be sent",
        examples=["user@example.com"]
    )
    calorie_target: int = Field(
        ge=1000,
        le=4000,
        description="Calculated daily calorie target (Mifflin-St Jeor formula)",
        examples=[1650]
    )
    verification_required: bool = Field(
        description="True if email verification needed (unauthenticated users)",
        examples=[True]
    )


class QuizProgressSaveRequest(BaseModel):
    """
    Request to save quiz progress for authenticated users.

    Enables cross-device resume capability.
    Functional requirement: FR-Q-011
    """
    quiz_id: Optional[UUID] = Field(
        default=None,
        description="Existing quiz ID if resuming; null for new quiz"
    )
    step_data: dict = Field(
        description="Partial quiz data (steps completed so far)",
        examples=[{"step_1": "female", "step_2": "moderately_active"}]
    )
    current_step: int = Field(
        ge=1,
        le=20,
        description="Current step number (1-20)",
        examples=[5]
    )


class QuizProgressSaveResponse(BaseModel):
    """Response after saving quiz progress."""
    quiz_id: UUID = Field(
        description="Quiz ID for future progress saves",
        examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
    )
    message: str = Field(
        description="Confirmation message",
        examples=["Progress saved successfully"]
    )
