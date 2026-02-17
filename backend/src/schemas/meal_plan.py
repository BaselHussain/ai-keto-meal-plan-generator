"""
Pydantic schemas for AI meal plan generation and validation.

Based on: specs/001-keto-meal-plan-generator/contracts/ai-generation.yaml
Functional requirements: FR-A-001 to FR-A-015, FR-D-001 to FR-D-008
"""

from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator


class PreferencesSummary(BaseModel):
    """
    User food preferences derived from quiz responses.

    Used as input to AI meal plan generation.
    Functional requirement: FR-A-014
    """
    excluded_foods: List[str] = Field(
        description="Foods to exclude from meal plan (from quiz steps 3-16)",
        examples=[["beef", "pork", "rice", "pasta"]]
    )
    preferred_proteins: List[str] = Field(
        description="Preferred protein sources (from quiz steps 3-4, 9)",
        examples=[["chicken", "salmon", "shrimp"]]
    )
    dietary_restrictions: str = Field(
        max_length=500,
        description="Free-text dietary restrictions from quiz step 17",
        examples=["No dairy from cows. Prefer coconut-based alternatives."]
    )


class GenerationRequest(BaseModel):
    """
    Internal request to generate meal plan.

    Triggered by payment webhook after successful payment.
    Functional requirement: FR-A-001
    """
    payment_id: str = Field(
        description="Paddle payment transaction ID",
        examples=["pay_01h2x3y4z5a6b7c8d9e0f1"]
    )
    email: EmailStr = Field(
        description="User email for PDF delivery",
        examples=["user@example.com"]
    )
    calorie_target: int = Field(
        ge=1000,
        le=4000,
        description="Daily calorie target from quiz calculation",
        examples=[1650]
    )
    preferences: PreferencesSummary = Field(
        description="User food preferences from quiz"
    )


class Ingredient(BaseModel):
    """
    Shopping list ingredient with quantity.

    Functional requirement: FR-A-015
    """
    name: str = Field(
        min_length=1,
        max_length=100,
        description="Ingredient name",
        examples=["Chicken breast"]
    )
    quantity: str = Field(
        min_length=1,
        max_length=50,
        description="Quantity with units",
        examples=["2 lbs"]
    )


class Meal(BaseModel):
    """
    Single meal with recipe, ingredients, and nutritional data.

    Functional requirement: FR-A-015
    """
    name: Literal["breakfast", "lunch", "dinner"] = Field(
        description="Meal type",
        examples=["breakfast"]
    )
    recipe: str = Field(
        min_length=1,
        max_length=200,
        description="Recipe name",
        examples=["Avocado & Bacon Scramble"]
    )
    ingredients: List[str] = Field(
        max_length=10,
        description="Recipe ingredients (max 10 per meal)",
        examples=[["2 eggs", "1/2 avocado", "2 strips bacon", "1 tbsp butter"]]
    )
    prep_time: int = Field(
        ge=1,
        le=30,
        description="Preparation time in minutes (max 30 for quick keto meals)",
        examples=[15]
    )
    carbs: int = Field(
        ge=0,
        description="Net carbohydrates in grams",
        examples=[5]
    )
    protein: int = Field(
        ge=0,
        description="Protein in grams",
        examples=[18]
    )
    fat: int = Field(
        ge=0,
        description="Fat in grams",
        examples=[25]
    )
    calories: int = Field(
        ge=0,
        description="Total calories",
        examples=[323]
    )

    @field_validator("ingredients")
    @classmethod
    def validate_ingredients_count(cls, v: List[str]) -> List[str]:
        """Ensure max 10 ingredients per meal."""
        if len(v) > 10:
            raise ValueError("Maximum 10 ingredients per meal")
        if len(v) == 0:
            raise ValueError("At least 1 ingredient required")
        return v


class DayMealPlan(BaseModel):
    """
    Complete meal plan for a single day (breakfast, lunch, dinner).

    Functional requirement: FR-A-015
    """
    day: int = Field(
        ge=1,
        le=30,
        description="Day number (1-30)",
        examples=[1]
    )
    meals: List[Meal] = Field(
        min_length=3,
        max_length=3,
        description="Exactly 3 meals: breakfast, lunch, dinner"
    )
    total_carbs: int = Field(
        le=30,
        description="Total daily net carbs (must be <30g for keto compliance)",
        examples=[25]
    )
    total_protein: int = Field(
        ge=0,
        description="Total daily protein in grams",
        examples=[120]
    )
    total_fat: int = Field(
        ge=0,
        description="Total daily fat in grams",
        examples=[135]
    )
    total_calories: int = Field(
        ge=0,
        description="Total daily calories",
        examples=[1650]
    )

    @field_validator("meals")
    @classmethod
    def validate_meal_types(cls, v: List[Meal]) -> List[Meal]:
        """Ensure exactly one breakfast, lunch, and dinner."""
        meal_names = [meal.name for meal in v]
        if len(meal_names) != 3:
            raise ValueError("Exactly 3 meals required per day")
        if set(meal_names) != {"breakfast", "lunch", "dinner"}:
            raise ValueError("Must have exactly one breakfast, lunch, and dinner")
        return v

    @field_validator("total_carbs")
    @classmethod
    def validate_keto_compliance(cls, v: int) -> int:
        """Enforce keto compliance: <30g net carbs per day."""
        if v > 30:
            raise ValueError(f"Keto compliance violation: {v}g carbs exceeds 30g limit")
        return v


class WeeklyShoppingList(BaseModel):
    """
    Weekly shopping list organized by food category.

    Functional requirement: FR-A-015
    """
    week: int = Field(
        ge=1,
        le=4,
        description="Week number (1-4 for 30-day plan)",
        examples=[1]
    )
    proteins: List[Ingredient] = Field(
        description="Protein sources (meat, fish, eggs)",
        examples=[[{"name": "Chicken breast", "quantity": "2 lbs"}]]
    )
    vegetables: List[Ingredient] = Field(
        description="Fresh vegetables and greens",
        examples=[[{"name": "Spinach", "quantity": "1 bunch"}]]
    )
    dairy: Optional[List[Ingredient]] = Field(
        default=None,
        description="Dairy products (optional based on preferences)",
        examples=[[{"name": "Heavy cream", "quantity": "1 pint"}]]
    )
    fats: Optional[List[Ingredient]] = Field(
        default=None,
        description="Cooking fats and oils",
        examples=[[{"name": "Olive oil", "quantity": "1 bottle"}]]
    )
    pantry: Optional[List[Ingredient]] = Field(
        default=None,
        description="Pantry staples and condiments",
        examples=[[{"name": "Salt", "quantity": "1 container"}]]
    )


class KetoTip(BaseModel):
    """
    A keto tip covering common mistakes, hydration, electrolytes, etc.

    Functional requirement: FR-A-008
    """
    title: str = Field(
        min_length=1,
        max_length=100,
        description="Short tip title",
        examples=["Stay Hydrated"]
    )
    description: str = Field(
        min_length=1,
        max_length=500,
        description="Detailed tip explanation",
        examples=["Drink at least 8 glasses of water daily. Keto increases water loss."]
    )


class MealPlanStructure(BaseModel):
    """
    Complete 30-day meal plan with shopping lists and keto tips.

    Expected output from AI generation service.
    Functional requirement: FR-A-015, FR-A-008
    """
    days: List[DayMealPlan] = Field(
        min_length=30,
        max_length=30,
        description="Exactly 30 days of meal plans"
    )
    shopping_lists: List[WeeklyShoppingList] = Field(
        min_length=4,
        max_length=4,
        description="4 weekly shopping lists (weeks 1-4)"
    )
    keto_tips: List[KetoTip] = Field(
        min_length=5,
        max_length=10,
        description="5-10 keto tips covering common mistakes, hydration, electrolytes (FR-A-008)"
    )

    @field_validator("days")
    @classmethod
    def validate_days_sequence(cls, v: List[DayMealPlan]) -> List[DayMealPlan]:
        """Ensure days are numbered 1-30 sequentially."""
        if len(v) != 30:
            raise ValueError("Exactly 30 days required")
        day_numbers = [day.day for day in v]
        if day_numbers != list(range(1, 31)):
            raise ValueError("Days must be numbered 1-30 sequentially")
        return v

    @field_validator("shopping_lists")
    @classmethod
    def validate_weeks_sequence(cls, v: List[WeeklyShoppingList]) -> List[WeeklyShoppingList]:
        """Ensure weeks are numbered 1-4 sequentially."""
        if len(v) != 4:
            raise ValueError("Exactly 4 weeks required")
        week_numbers = [week.week for week in v]
        if week_numbers != list(range(1, 5)):
            raise ValueError("Weeks must be numbered 1-4 sequentially")
        return v


class MealPlanValidationRequest(BaseModel):
    """
    Request to validate AI-generated meal plan.

    Functional requirements: FR-A-007, FR-A-015
    """
    meal_plan: MealPlanStructure = Field(
        description="AI-generated meal plan to validate"
    )


class ValidationResult(BaseModel):
    """
    Validation result for meal plan structure and keto compliance.

    Functional requirements: FR-A-007, FR-A-015
    """
    valid: bool = Field(
        description="Overall validation status",
        examples=[True]
    )
    keto_compliant: bool = Field(
        description="True if all 30 days have <30g net carbs",
        examples=[True]
    )
    structure_valid: bool = Field(
        description="True if structure matches expected format (30 days, 3 meals each)",
        examples=[True]
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of validation errors (empty if valid)",
        examples=[["Day 5 exceeds 30g carbs (32g)", "Missing dinner for Day 12"]]
    )


class ValidationError(BaseModel):
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
        description="Number of retries attempted before final failure (max 2 for keto, 1 for structure)",
        examples=[2]
    )


class GenerationResponse(BaseModel):
    """
    Response after meal plan generation completes.

    Functional requirements: FR-A-006, FR-D-004
    """
    meal_plan_id: UUID = Field(
        description="Unique identifier for generated meal plan",
        examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
    )
    pdf_url: Optional[str] = Field(
        default=None,
        description="Vercel Blob signed URL for PDF download (null if generation failed)",
        examples=["https://blob.vercel-storage.com/abc123.pdf?signature=xyz..."]
    )
    ai_model: str = Field(
        description="AI model used for generation",
        examples=["gpt-4o"]
    )
    generation_time_ms: int = Field(
        ge=0,
        description="Time taken for AI generation in milliseconds",
        examples=[18500]
    )
    status: Literal["completed", "failed", "manual_resolution"] = Field(
        description="Generation status (manual_resolution if validation failed after retries)",
        examples=["completed"]
    )
