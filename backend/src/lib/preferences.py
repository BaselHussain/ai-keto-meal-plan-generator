"""
Food preference summary derivation service.

This module provides logic to derive a structured food preferences summary
from user quiz responses. It maps quiz responses (steps 3-17) to excluded foods,
preferred proteins, and dietary restrictions.

Requirements: FR-A-014 (Food preference summary derivation)
"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class PreferencesSummary(BaseModel):
    """
    Structured summary of user's food preferences derived from quiz responses.

    Attributes:
        excluded_foods: List of food items the user did NOT select (implicitly excluded).
        preferred_proteins: List of protein sources the user selected from meat, fish, and shellfish.
        dietary_restrictions: Free-text dietary restrictions or preferences from step 17.
    """
    excluded_foods: List[str] = Field(
        default_factory=list,
        description="Food items not selected by user across all food preference steps"
    )
    preferred_proteins: List[str] = Field(
        default_factory=list,
        description="Protein sources selected from meat, fish, and shellfish categories"
    )
    dietary_restrictions: str = Field(
        default="",
        description="Free-text dietary restrictions or special preferences"
    )


# Complete food items catalog organized by quiz steps
ALL_FOOD_ITEMS: Dict[str, List[str]] = {
    "step_3": ["beef", "lamb", "chicken", "pork", "turkey"],  # Meat
    "step_4": ["tuna", "salmon", "mackerel", "cod", "pollock"],  # Fish
    "step_5": ["avocado", "asparagus", "bell_pepper", "zucchini", "celery", "mushrooms"],  # Low-carb veggies
    "step_6": ["brussels_sprouts", "kale", "broccoli", "cauliflower"],  # Cruciferous vegetables
    "step_7": ["lettuce", "spinach", "arugula", "cilantro", "iceberg", "napa_cabbage"],  # Leafy greens
    "step_8": ["chickpeas", "lentils", "black_beans"],  # Legumes
    "step_9": ["clams", "shrimp", "crab", "lobster"],  # Shellfish
    "step_10": ["apple", "banana", "orange", "berries"],  # Fruits
    "step_11": ["strawberries", "blueberries", "raspberries"],  # Berries
    "step_12": ["rice", "quinoa", "oats"],  # Grains
    "step_13": ["pasta", "bread", "potatoes"],  # Starches
    "step_14": ["coconut_oil", "olive_oil", "peanut_butter", "butter", "lard"],  # Fats
    "step_15": ["water", "coffee", "tea", "soda"],  # Beverages
    "step_16": ["greek_yogurt", "cheese", "sour_cream", "cottage_cheese"],  # Dairy
}

# Steps that contain protein sources for preferred_proteins calculation
PROTEIN_STEPS = ["step_3", "step_4", "step_9"]  # Meat, Fish, Shellfish


def derive_preferences_summary(quiz_responses: Dict[str, Any]) -> PreferencesSummary:
    """
    Derive a structured food preferences summary from quiz responses.

    This function processes quiz responses from steps 3-17 to extract:
    1. Excluded foods: All food items NOT selected by the user
    2. Preferred proteins: Selected items from meat, fish, and shellfish steps
    3. Dietary restrictions: Free-text input from step 17

    Args:
        quiz_responses: Dictionary containing quiz responses with keys like "step_3", "step_4", etc.
                       Each food preference step contains a list of selected food items.
                       Step 17 contains a string with dietary restrictions.

    Returns:
        PreferencesSummary: Structured summary with excluded_foods, preferred_proteins,
                           and dietary_restrictions.

    Example:
        >>> responses = {
        ...     "step_3": ["chicken", "turkey"],
        ...     "step_4": ["salmon"],
        ...     "step_9": ["shrimp"],
        ...     "step_17": "No gluten, dairy-free"
        ... }
        >>> summary = derive_preferences_summary(responses)
        >>> assert "beef" in summary.excluded_foods
        >>> assert "chicken" in summary.preferred_proteins
        >>> assert summary.dietary_restrictions == "No gluten, dairy-free"
    """
    # Step 1: Collect all items the user selected across all food preference steps
    selected_items: set[str] = set()

    for step_key, food_items in ALL_FOOD_ITEMS.items():
        user_selections = quiz_responses.get(step_key, [])

        # Ensure user_selections is a list
        if not isinstance(user_selections, list):
            user_selections = []

        # Add all selected items to the set
        selected_items.update(user_selections)

    # Step 2: Calculate excluded_foods (all items NOT selected)
    all_possible_items: set[str] = set()
    for food_items in ALL_FOOD_ITEMS.values():
        all_possible_items.update(food_items)

    excluded_foods = sorted(list(all_possible_items - selected_items))

    # Step 3: Calculate preferred_proteins (selected items from protein steps only)
    preferred_proteins: List[str] = []

    for step_key in PROTEIN_STEPS:
        user_selections = quiz_responses.get(step_key, [])

        # Ensure user_selections is a list
        if not isinstance(user_selections, list):
            user_selections = []

        preferred_proteins.extend(user_selections)

    # Remove duplicates and sort for consistency
    preferred_proteins = sorted(list(set(preferred_proteins)))

    # Step 4: Extract dietary restrictions from step 17
    dietary_restrictions = quiz_responses.get("step_17", "")

    # Ensure dietary_restrictions is a string
    if not isinstance(dietary_restrictions, str):
        dietary_restrictions = str(dietary_restrictions) if dietary_restrictions else ""

    # Return structured summary
    return PreferencesSummary(
        excluded_foods=excluded_foods,
        preferred_proteins=preferred_proteins,
        dietary_restrictions=dietary_restrictions.strip()
    )
