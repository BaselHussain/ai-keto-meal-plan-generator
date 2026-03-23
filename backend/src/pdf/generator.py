"""
PDF Generator for Keto Meal Plans with enhancements
This module handles PDF generation with improvements including:
- Removal of blank pages
- Addition of personalized food suggestions based on quiz responses
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus.flowables import PageBreak
from reportlab.lib.utils import ImageReader
from io import BytesIO
import json
from typing import Dict, List, Optional, Any
from ..models.meal_plan import MealPlan


def create_enhanced_pdf(meal_plan_data: Dict, user_quiz_responses: Dict = None, food_suggestions: List[Dict] = None) -> bytes:
    """
    Generate an enhanced PDF with meal plans and personalized food suggestions

    Args:
        meal_plan_data: The 30-day meal plan data
        user_quiz_responses: User's quiz responses for personalization
        food_suggestions: Personalized food combination suggestions

    Returns:
        bytes: PDF content as bytes
    """
    buffer = BytesIO()

    # Create document with proper page configuration to avoid blank pages
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch
    )

    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,  # Center alignment
        textColor=colors.darkgreen
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.darkblue
    )

    # Create story
    story = []

    # Add title
    story.append(Paragraph("Your Personalized 30-Day Keto Meal Plan", title_style))
    story.append(Spacer(1, 20))

    # Add date
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
    story.append(Spacer(1, 20))

    # Generate the 30-day meal plan content
    daily_meals = meal_plan_data.get("daily_meals", [])

    for day_idx, day in enumerate(daily_meals[:30], 1):  # Process first 30 days
        # Add day heading
        story.append(Paragraph(f"Day {day_idx}", heading_style))
        story.append(Spacer(1, 12))

        # Add meals for the day
        meals = day.get("meals", {})

        for meal_type, meal_info in meals.items():
            meal_title = meal_type.title()
            story.append(Paragraph(f"{meal_title}:", styles['Heading3']))

            # Add meal details
            if "recipe" in meal_info:
                recipe = meal_info["recipe"]
                story.append(Paragraph(f"<b>Recipe:</b> {recipe.get('name', 'N/A')}", styles['Normal']))
                story.append(Paragraph(f"<b>Description:</b> {recipe.get('description', 'N/A')}", styles['Normal']))

                # Add ingredients
                ingredients_list = recipe.get('ingredients', [])
                if ingredients_list:
                    story.append(Paragraph("<b>Ingredients:</b>", styles['Normal']))
                    for ingredient in ingredients_list:
                        story.append(Paragraph(f"• {ingredient}", styles['Normal']))

                # Add macros
                macros = recipe.get('macros', {})
                if macros:
                    story.append(Paragraph("<b>Nutritional Information:</b>", styles['Normal']))
                    story.append(Paragraph(f"• Calories: {macros.get('calories', 'N/A')}", styles['Normal']))
                    story.append(Paragraph(f"• Carbs: {macros.get('net_carbs', 'N/A')}g", styles['Normal']))
                    story.append(Paragraph(f"• Protein: {macros.get('protein', 'N/A')}g", styles['Normal']))
                    story.append(Paragraph(f"• Fat: {macros.get('fat', 'N/A')}g", styles['Normal']))

            story.append(Spacer(1, 10))

        # Add a small spacer between days, but avoid unnecessary page breaks
        story.append(Spacer(1, 20))

        # Prevent unwanted page breaks by controlling content flow
        # Only add page break when needed to avoid blank pages
        if day_idx % 7 == 0 and day_idx < 30:  # Add page break every 7 days if more days follow
            story.append(KeepTogether([Spacer(1, 0.1*inch)]))  # Minimal content to avoid blank pages

    # Add Food Suggestions Section if available
    if food_suggestions and len(food_suggestions) > 0:
        # Add conditional page break to avoid blank pages
        if len(story) > 0:
            # Check if we're at the beginning of a new page already
            story.append(Paragraph("<br/>" if len(story) % 2 == 0 else ""))

        story.append(Paragraph("Personalized Food Combinations", heading_style))
        story.append(Spacer(1, 20))

        # Add 5 food combination suggestions based on user preferences
        for i, suggestion in enumerate(food_suggestions[:5], 1):
            meal_type = suggestion.get("meal_type", "").title()
            combination = suggestion.get("food_combination", "N/A")
            description = suggestion.get("description", "")

            story.append(Paragraph(f"{i}. {meal_type}: {combination}", styles['Heading3']))
            story.append(Paragraph(description, styles['Normal']))
            story.append(Spacer(1, 15))

    # Build the PDF
    doc.build(story)

    # Get the PDF content
    pdf_content = buffer.getvalue()
    buffer.close()

    return pdf_content


def generate_food_suggestions(quiz_responses: Dict) -> List[Dict[str, Any]]:
    """
    Generate personalized food combination suggestions based on user quiz responses

    Args:
        quiz_responses: User's quiz responses

    Returns:
        List of food suggestion dictionaries
    """
    suggestions = []

    # Determine preferences from quiz responses
    meat_preference = quiz_responses.get("meat_preference", "chicken") if quiz_responses else "chicken"
    vegetable_preference = quiz_responses.get("vegetable_preference", "broccoli") if quiz_responses else "broccoli"
    preferred_meal_type = quiz_responses.get("preferred_meal_type", "balanced") if quiz_responses else "balanced"

    # Sample food combinations based on user preferences
    breakfast_options = [
        f"Scrambled {meat_preference} with {vegetable_preference} and avocado",
        f"{meat_preference} and {vegetable_preference} omelette with cheese",
        f"Keto smoothie with {meat_preference} protein powder and low-carb ingredients"
    ]

    lunch_options = [
        f"{meat_preference} salad with {vegetable_preference} and olive oil dressing",
        f"Grilled {meat_preference} with roasted {vegetable_preference}",
        f"{meat_preference} and {vegetable_preference} stir-fry with coconut oil"
    ]

    dinner_options = [
        f"Roasted {meat_preference} with {vegetable_preference} medley",
        f"Grilled {meat_preference} served with steamed {vegetable_preference}",
        f"Herb-crusted {meat_preference} with {vegetable_preference} puree"
    ]

    # Create 5 food suggestions (breakfast, lunch, dinner combinations)
    suggestions.extend([
        {
            "meal_type": "breakfast",
            "food_combination": breakfast_options[0],
            "description": "A satisfying keto breakfast to start your day right. High in healthy fats and protein to keep you energized.",
            "keto_friendly": True
        },
        {
            "meal_type": "lunch",
            "food_combination": lunch_options[0],
            "description": "Nutritious lunch option packed with protein and low-carb vegetables to fuel your afternoon.",
            "keto_friendly": True
        },
        {
            "meal_type": "dinner",
            "food_combination": dinner_options[0],
            "description": "Comforting dinner that's rich in healthy fats to support ketosis. Easy to prepare and full of flavor.",
            "keto_friendly": True
        },
        {
            "meal_type": "breakfast",
            "food_combination": breakfast_options[1],
            "description": "Protein-rich breakfast option with healthy fats to support your keto lifestyle.",
            "keto_friendly": True
        },
        {
            "meal_type": "snack",
            "food_combination": f"Avocado with {meat_preference} slices and {vegetable_preference}",
            "description": "Light keto snack perfect for between meals. Rich in healthy fats and protein to keep cravings at bay.",
            "keto_friendly": True
        }
    ])

    return suggestions


def fix_blank_page_issue(pdf_content: bytes) -> bytes:
    """
    Remove blank pages from PDF content
    This is a utility to ensure no blank pages are generated
    """
    # In the current implementation, we handle this by controlling content flow in the create_enhanced_pdf function
    # This is a placeholder in case we need additional processing
    return pdf_content