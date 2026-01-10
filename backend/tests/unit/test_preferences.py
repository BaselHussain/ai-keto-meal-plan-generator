"""
Unit tests for food preference summary derivation logic.

Tests the `derive_preferences_summary` function to ensure it correctly
extracts excluded foods, preferred proteins, and dietary restrictions
from various user quiz response scenarios.

Covered Scenarios:
1. Standard user with mixed selections
2. High-protein user with many selections
3. User with dietary restrictions
4. Vegetarian user (implicit exclusions)
5. Select-all user (no exclusions)
6. Select-none user (all excluded)
"""

import pytest
from src.lib.preferences import derive_preferences_summary, ALL_FOOD_ITEMS

def test_derive_preferences_standard_user():
    """
    Test Case 1: Standard user who selects specific items.
    
    Verifies that:
    - Unselected items appear in excluded_foods
    - Selected proteins appear in preferred_proteins
    - Selected non-protein items are NOT in excluded_foods
    """
    quiz_responses = {
        "step_3": ["chicken"],  # Meat (Protein)
        "step_4": ["salmon"],   # Fish (Protein)
        "step_5": ["avocado"],  # Low-carb veggies
        "step_17": ""
    }

    summary = derive_preferences_summary(quiz_responses)

    # Check preferred proteins
    assert "chicken" in summary.preferred_proteins
    assert "salmon" in summary.preferred_proteins
    assert "beef" not in summary.preferred_proteins
    
    # Check excluded foods
    assert "beef" in summary.excluded_foods        # Unselected protein
    assert "avocado" not in summary.excluded_foods # Selected veggie
    assert "spinach" in summary.excluded_foods     # Unselected veggie
    
    # Check dietary restrictions
    assert summary.dietary_restrictions == ""


def test_derive_preferences_high_protein_user():
    """
    Test Case 2: User who selects many protein sources across categories.
    
    Verifies that:
    - All selected proteins from Meat, Fish, and Shellfish are captured
    - Unselected proteins are excluded
    """
    quiz_responses = {
        "step_3": ["beef", "chicken", "turkey"],   # Meat
        "step_4": ["tuna", "salmon"],              # Fish
        "step_9": ["shrimp", "lobster"],           # Shellfish
        "step_17": "High protein diet"
    }

    summary = derive_preferences_summary(quiz_responses)

    expected_proteins = ["beef", "chicken", "turkey", "tuna", "salmon", "shrimp", "lobster"]
    for protein in expected_proteins:
        assert protein in summary.preferred_proteins

    assert summary.dietary_restrictions == "High protein diet"
    assert "pork" in summary.excluded_foods # Not selected meat
    assert "cod" in summary.excluded_foods  # Not selected fish


def test_derive_preferences_with_restrictions():
    """
    Test Case 3: User with specific dietary restrictions.
    
    Verifies that:
    - Step 17 text input is correctly captured and stripped
    - Standard food preferences are still processed correctly
    """
    quiz_responses = {
        "step_3": ["beef"],
        "step_17": " No gluten, dairy-free " # With whitespace
    }

    summary = derive_preferences_summary(quiz_responses)

    assert summary.dietary_restrictions == "No gluten, dairy-free"
    assert "beef" in summary.preferred_proteins
    assert "chicken" in summary.excluded_foods


def test_derive_preferences_vegetarian():
    """
    Test Case 4: Vegetarian user (no meat/fish/shellfish selections).
    
    Verifies that:
    - preferred_proteins list is empty
    - All meat, fish, and shellfish items are in excluded_foods
    """
    quiz_responses = {
        "step_3": [], # No meat
        "step_4": [], # No fish
        "step_9": [], # No shellfish
        "step_5": ["avocado", "mushrooms"],
        "step_17": "Vegetarian"
    }

    summary = derive_preferences_summary(quiz_responses)

    assert summary.preferred_proteins == []
    
    # Check implicit exclusions
    assert "beef" in summary.excluded_foods
    assert "chicken" in summary.excluded_foods
    assert "salmon" in summary.excluded_foods
    assert "shrimp" in summary.excluded_foods
    
    assert summary.dietary_restrictions == "Vegetarian"


def test_derive_preferences_select_all():
    """
    Test Case 5: User who selects everything.
    
    Verifies that:
    - excluded_foods list is empty
    - preferred_proteins contains all available protein options
    """
    quiz_responses = {}
    for step, items in ALL_FOOD_ITEMS.items():
        quiz_responses[step] = items
    
    # Add a restriction string
    quiz_responses["step_17"] = "None"

    summary = derive_preferences_summary(quiz_responses)

    assert summary.excluded_foods == []
    
    # Check that protein steps are fully represented in preferred_proteins
    protein_steps = ["step_3", "step_4", "step_9"]
    all_proteins = []
    for step in protein_steps:
        all_proteins.extend(ALL_FOOD_ITEMS[step])
    
    assert sorted(summary.preferred_proteins) == sorted(all_proteins)


def test_derive_preferences_select_none():
    """
    Test Case 6: User who provides empty input (Select None).
    
    Verifies that:
    - excluded_foods contains ALL known food items
    - preferred_proteins is empty
    """
    quiz_responses = {}

    summary = derive_preferences_summary(quiz_responses)

    # Calculate total number of food items
    total_items_count = sum(len(items) for items in ALL_FOOD_ITEMS.values())
    
    assert len(summary.excluded_foods) == total_items_count
    assert summary.preferred_proteins == []
    assert summary.dietary_restrictions == ""
    
    # Random check
    assert "beef" in summary.excluded_foods
    assert "apple" in summary.excluded_foods
