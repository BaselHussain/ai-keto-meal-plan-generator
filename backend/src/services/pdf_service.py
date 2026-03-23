"""
PDF Service Module
Handles the business logic for PDF generation with enhanced features
"""

from typing import Dict, List, Any
from ..pdf.generator import create_enhanced_pdf, generate_food_suggestions
from ..models.meal_plan import MealPlan
from ..models.user import User


def generate_pdf_with_suggestions(
    user: User,
    meal_plan: MealPlan,
    quiz_responses: Dict[str, Any]
) -> bytes:
    """
    Generate a PDF with meal plan and personalized food suggestions
    """
    # Generate personalized food suggestions based on user's quiz responses
    food_suggestions = generate_food_suggestions(quiz_responses)

    # Create the enhanced PDF with food suggestions
    pdf_content = create_enhanced_pdf(
        meal_plan_data=meal_plan.daily_meals,
        user_quiz_responses=quiz_responses,
        food_suggestions=food_suggestions
    )

    return pdf_content


def validate_food_suggestions_keto_compliance(food_suggestions: List[Dict[str, Any]]) -> bool:
    """
    Validate that food suggestions comply with keto guidelines
    """
    # This is a basic validation - in a real implementation, this would check
    # more detailed keto compliance rules
    for suggestion in food_suggestions:
        if not suggestion.get("keto_friendly", False):
            return False

    return True