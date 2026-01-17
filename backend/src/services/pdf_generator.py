"""
PDF Generator Service for 30-Day Keto Meal Plan

Generates professional PDF documents using ReportLab's Platypus framework.

Features:
- Cover page with user info, calorie target, and macro breakdown
- 30 days of meals with macronutrient tables
- 4 weekly shopping lists organized by category
- Green theme (#22c55e) with professional styling
- 20-second timeout with error handling
- PDF validation (non-zero bytes, valid header)

Implements: T074, T075, T076, T077
Functional Requirements: FR-D-001 to FR-D-004
"""

import asyncio
import logging
from datetime import datetime
from io import BytesIO
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak,
    KeepTogether,
)

from src.schemas.meal_plan import MealPlanStructure

# Configure logging
logger = logging.getLogger(__name__)

# PDF generation timeout (T076)
PDF_GENERATION_TIMEOUT = 20  # seconds

# Theme colors (T075)
KETO_GREEN = colors.HexColor("#22c55e")
KETO_GREEN_LIGHT = colors.HexColor("#86efac")
KETO_GREEN_DARK = colors.HexColor("#16a34a")
HEADER_BG = colors.HexColor("#f0fdf4")  # Very light green for alternating rows
ROW_ALT_COLOR = colors.HexColor("#f8fafc")  # Subtle gray for alternating rows


class PDFGenerationError(Exception):
    """Custom exception for PDF generation failures."""

    def __init__(
        self,
        message: str,
        error_type: str = "unknown",
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.original_error = original_error


def _create_custom_styles() -> dict:
    """
    Create custom paragraph styles for the meal plan PDF.

    Returns:
        dict: Dictionary of ParagraphStyle objects

    Implements: T075 - Custom PDF styles with green theme
    """
    base_styles = getSampleStyleSheet()

    custom_styles = {
        "base": base_styles,

        # Title style for cover page
        "title": ParagraphStyle(
            "CustomTitle",
            parent=base_styles["Heading1"],
            fontSize=28,
            textColor=KETO_GREEN_DARK,
            alignment=TA_CENTER,
            spaceAfter=20,
            spaceBefore=40,
            fontName="Helvetica-Bold",
        ),

        # Subtitle for cover page
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base_styles["Normal"],
            fontSize=14,
            textColor=colors.HexColor("#374151"),
            alignment=TA_CENTER,
            spaceAfter=8,
        ),

        # Cover page info text
        "cover_info": ParagraphStyle(
            "CoverInfo",
            parent=base_styles["Normal"],
            fontSize=12,
            textColor=colors.HexColor("#1f2937"),
            alignment=TA_CENTER,
            spaceAfter=6,
            leading=18,
        ),

        # Day header (Day 1, Day 2, etc.)
        "day_header": ParagraphStyle(
            "DayHeader",
            parent=base_styles["Heading2"],
            fontSize=16,
            textColor=KETO_GREEN_DARK,
            spaceBefore=12,
            spaceAfter=8,
            fontName="Helvetica-Bold",
        ),

        # Section header (Week 1 Shopping List, etc.)
        "section_header": ParagraphStyle(
            "SectionHeader",
            parent=base_styles["Heading2"],
            fontSize=18,
            textColor=KETO_GREEN_DARK,
            spaceBefore=16,
            spaceAfter=12,
            fontName="Helvetica-Bold",
        ),

        # Category header in shopping list
        "category_header": ParagraphStyle(
            "CategoryHeader",
            parent=base_styles["Heading3"],
            fontSize=12,
            textColor=KETO_GREEN,
            spaceBefore=10,
            spaceAfter=4,
            fontName="Helvetica-Bold",
        ),

        # Shopping list item
        "list_item": ParagraphStyle(
            "ListItem",
            parent=base_styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#374151"),
            leftIndent=12,
            spaceAfter=2,
            bulletIndent=0,
        ),

        # Italic motivational text
        "motivational": ParagraphStyle(
            "Motivational",
            parent=base_styles["Italic"],
            fontSize=11,
            textColor=colors.HexColor("#6b7280"),
            alignment=TA_CENTER,
            spaceAfter=12,
            spaceBefore=12,
        ),

        # Footer text
        "footer": ParagraphStyle(
            "Footer",
            parent=base_styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#9ca3af"),
            alignment=TA_CENTER,
        ),
    }

    return custom_styles


def _create_meal_table_style() -> TableStyle:
    """
    Create table style for daily meal tables.

    Implements: T075 - Table layouts with macronutrient breakdown
    """
    return TableStyle([
        # Header row - green background
        ("BACKGROUND", (0, 0), (-1, 0), KETO_GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 10),

        # Alternating row colors for readability (T075)
        ("BACKGROUND", (0, 1), (-1, 1), colors.white),
        ("BACKGROUND", (0, 2), (-1, 2), ROW_ALT_COLOR),
        ("BACKGROUND", (0, 3), (-1, 3), colors.white),

        # Daily totals row - highlighted
        ("BACKGROUND", (0, -1), (-1, -1), HEADER_BG),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 10),
        ("TOPPADDING", (0, -1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 8),

        # Body text
        ("FONTSIZE", (0, 1), (-1, -2), 9),
        ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
        ("TOPPADDING", (0, 1), (-1, -2), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -2), 6),

        # Alignment
        ("ALIGN", (0, 0), (0, -1), "LEFT"),  # Meal name column left-aligned
        ("ALIGN", (1, 0), (1, -1), "LEFT"),  # Recipe column left-aligned
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),  # Numeric columns centered
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        # Grid lines
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ("BOX", (0, 0), (-1, -1), 1, KETO_GREEN),
    ])


def _build_cover_page(
    story: list,
    styles: dict,
    calorie_target: int,
    fat_percent: int,
    protein_percent: int,
    carb_percent: int,
    user_email: Optional[str],
) -> None:
    """
    Build the cover page with user info and plan overview.

    Implements: T074 - Cover page with user info, calorie target, macros
    """
    # Main title
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("Your Personalized", styles["subtitle"]))
    story.append(Paragraph("30-Day Keto Meal Plan", styles["title"]))
    story.append(Spacer(1, 0.5 * inch))

    # Decorative line
    line_data = [["" * 50]]
    line_table = Table(line_data, colWidths=[4 * inch])
    line_table.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 2, KETO_GREEN),
    ]))
    story.append(line_table)
    story.append(Spacer(1, 0.5 * inch))

    # User info section
    generation_date = datetime.utcnow().strftime("%B %d, %Y")
    story.append(Paragraph(
        f"<b>Generated:</b> {generation_date}",
        styles["cover_info"]
    ))

    if user_email:
        story.append(Paragraph(
            f"<b>Prepared for:</b> {user_email}",
            styles["cover_info"]
        ))

    story.append(Spacer(1, 0.3 * inch))

    # Calorie and macro info box
    macro_data = [
        ["Daily Calorie Target", f"{calorie_target} kcal"],
        ["Fat", f"{fat_percent}%"],
        ["Protein", f"{protein_percent}%"],
        ["Net Carbs", f"{carb_percent}%"],
    ]

    macro_table = Table(macro_data, colWidths=[2.5 * inch, 1.5 * inch])
    macro_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), KETO_GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("BACKGROUND", (0, 1), (-1, -1), HEADER_BG),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 1, KETO_GREEN),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
    ]))
    story.append(macro_table)

    story.append(Spacer(1, 0.5 * inch))

    # Motivational message
    story.append(Paragraph(
        "<i>Your personalized keto journey starts here!</i>",
        styles["motivational"]
    ))
    story.append(Paragraph(
        "<i>Each meal has been carefully crafted to keep you in ketosis</i>",
        styles["motivational"]
    ))
    story.append(Paragraph(
        "<i>while providing delicious, satisfying nutrition.</i>",
        styles["motivational"]
    ))

    story.append(Spacer(1, 0.5 * inch))

    # What's inside section
    story.append(Paragraph(
        "<b>What's Inside:</b>",
        styles["cover_info"]
    ))
    story.append(Paragraph(
        "90 unique keto recipes (3 meals x 30 days)",
        styles["cover_info"]
    ))
    story.append(Paragraph(
        "Complete macronutrient breakdown for every meal",
        styles["cover_info"]
    ))
    story.append(Paragraph(
        "4 organized weekly shopping lists",
        styles["cover_info"]
    ))

    story.append(PageBreak())


def _build_daily_meals(
    story: list,
    styles: dict,
    meal_plan: MealPlanStructure,
) -> None:
    """
    Build the 30 days of meal tables.

    Implements: T074 - 30 days with 3 meals table + daily totals
    """
    table_style = _create_meal_table_style()

    # Column widths for meal table
    col_widths = [0.9 * inch, 2.4 * inch, 0.7 * inch, 0.8 * inch, 0.7 * inch, 0.8 * inch]

    for day in meal_plan.days:
        # Day header
        story.append(Paragraph(f"Day {day.day}", styles["day_header"]))

        # Build meal table data
        meal_data = [
            ["Meal", "Recipe", "Carbs (g)", "Protein (g)", "Fat (g)", "Calories"],
        ]

        # Sort meals in order: breakfast, lunch, dinner
        meal_order = {"breakfast": 0, "lunch": 1, "dinner": 2}
        sorted_meals = sorted(day.meals, key=lambda m: meal_order.get(m.name, 99))

        for meal in sorted_meals:
            # Truncate recipe name if too long
            recipe_name = meal.recipe
            if len(recipe_name) > 35:
                recipe_name = recipe_name[:32] + "..."

            meal_data.append([
                meal.name.title(),
                recipe_name,
                str(meal.carbs),
                str(meal.protein),
                str(meal.fat),
                str(meal.calories),
            ])

        # Daily totals row
        meal_data.append([
            "DAILY TOTAL",
            "",
            f"{day.total_carbs}g",
            f"{day.total_protein}g",
            f"{day.total_fat}g",
            f"{day.total_calories}",
        ])

        # Create and style table
        meal_table = Table(meal_data, colWidths=col_widths)
        meal_table.setStyle(table_style)

        # Wrap in KeepTogether to avoid splitting across pages
        story.append(KeepTogether([
            Paragraph(f"Day {day.day}", styles["day_header"]),
            Spacer(1, 0.05 * inch),
            meal_table,
        ]))

        # Remove the duplicate header we added for KeepTogether
        story.pop(-1)
        story.append(meal_table)
        story.append(Spacer(1, 0.25 * inch))

        # Page break every 2 days for readability (T074)
        if day.day % 2 == 0 and day.day < 30:
            story.append(PageBreak())


def _build_shopping_lists(
    story: list,
    styles: dict,
    meal_plan: MealPlanStructure,
) -> None:
    """
    Build the 4 weekly shopping lists organized by category.

    Implements: T074 - 4 weekly shopping lists organized by category
    """
    story.append(PageBreak())
    story.append(Paragraph("Weekly Shopping Lists", styles["title"]))
    story.append(Spacer(1, 0.3 * inch))

    for week in meal_plan.shopping_lists:
        story.append(Paragraph(f"Week {week.week}", styles["section_header"]))

        # Proteins section (required)
        story.append(Paragraph("Proteins", styles["category_header"]))
        for item in week.proteins:
            story.append(Paragraph(
                f"\u2022 {item.name} \u2014 {item.quantity}",
                styles["list_item"]
            ))

        # Vegetables section (required)
        story.append(Paragraph("Vegetables", styles["category_header"]))
        for item in week.vegetables:
            story.append(Paragraph(
                f"\u2022 {item.name} \u2014 {item.quantity}",
                styles["list_item"]
            ))

        # Dairy section (optional)
        if week.dairy:
            story.append(Paragraph("Dairy", styles["category_header"]))
            for item in week.dairy:
                story.append(Paragraph(
                    f"\u2022 {item.name} \u2014 {item.quantity}",
                    styles["list_item"]
                ))

        # Fats section (optional)
        if week.fats:
            story.append(Paragraph("Fats & Oils", styles["category_header"]))
            for item in week.fats:
                story.append(Paragraph(
                    f"\u2022 {item.name} \u2014 {item.quantity}",
                    styles["list_item"]
                ))

        # Pantry section (optional)
        if week.pantry:
            story.append(Paragraph("Pantry Staples", styles["category_header"]))
            for item in week.pantry:
                story.append(Paragraph(
                    f"\u2022 {item.name} \u2014 {item.quantity}",
                    styles["list_item"]
                ))

        story.append(Spacer(1, 0.3 * inch))

        # Page break between weeks (except last)
        if week.week < 4:
            story.append(PageBreak())


def _generate_pdf_sync(
    meal_plan: MealPlanStructure,
    calorie_target: int,
    fat_percent: int,
    protein_percent: int,
    carb_percent: int,
    user_email: Optional[str],
) -> bytes:
    """
    Synchronous PDF generation using ReportLab.

    This is the core PDF building function called within async wrapper.
    """
    buffer = BytesIO()

    # Configure document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        title="30-Day Keto Meal Plan",
        author="Keto Meal Plan Generator",
    )

    # Create custom styles
    styles = _create_custom_styles()

    # Build story (list of flowables)
    story = []

    # Cover page
    _build_cover_page(
        story=story,
        styles=styles,
        calorie_target=calorie_target,
        fat_percent=fat_percent,
        protein_percent=protein_percent,
        carb_percent=carb_percent,
        user_email=user_email,
    )

    # 30 days of meals
    _build_daily_meals(
        story=story,
        styles=styles,
        meal_plan=meal_plan,
    )

    # Weekly shopping lists
    _build_shopping_lists(
        story=story,
        styles=styles,
        meal_plan=meal_plan,
    )

    # Build the PDF
    doc.build(story)

    # Get bytes
    buffer.seek(0)
    return buffer.read()


async def generate_pdf(
    meal_plan: MealPlanStructure,
    calorie_target: int,
    fat_percent: int = 70,
    protein_percent: int = 25,
    carb_percent: int = 5,
    user_email: Optional[str] = None,
) -> bytes:
    """
    Generate 30-day keto meal plan PDF with timeout handling.

    Args:
        meal_plan: Complete 30-day meal plan structure
        calorie_target: Daily calorie target from quiz
        fat_percent: Target fat percentage (default 70%)
        protein_percent: Target protein percentage (default 25%)
        carb_percent: Target carb percentage (default 5%)
        user_email: Optional user email for cover page personalization

    Returns:
        bytes: Generated PDF file bytes

    Raises:
        PDFGenerationError: If PDF generation fails
        asyncio.TimeoutError: If generation exceeds 20-second timeout

    Implements: T074, T075, T076
    Functional Requirements: FR-D-001 to FR-D-004
    """
    logger.info(
        f"Starting PDF generation: {calorie_target} kcal, "
        f"{len(meal_plan.days)} days, {len(meal_plan.shopping_lists)} weeks"
    )

    start_time = datetime.utcnow()

    try:
        # Run synchronous PDF generation in thread pool with timeout (T076)
        pdf_bytes = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                _generate_pdf_sync,
                meal_plan,
                calorie_target,
                fat_percent,
                protein_percent,
                carb_percent,
                user_email,
            ),
            timeout=PDF_GENERATION_TIMEOUT,
        )

        generation_time = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"PDF generated successfully: {len(pdf_bytes)} bytes in {generation_time:.2f}s"
        )

        # Validate generated PDF (T077)
        if not validate_pdf(pdf_bytes):
            raise PDFGenerationError(
                "Generated PDF failed validation",
                error_type="validation_error",
            )

        return pdf_bytes

    except asyncio.TimeoutError:
        logger.error(f"PDF generation timed out after {PDF_GENERATION_TIMEOUT}s")
        raise PDFGenerationError(
            f"PDF generation exceeded {PDF_GENERATION_TIMEOUT}s timeout",
            error_type="timeout",
        )

    except PDFGenerationError:
        # Re-raise our custom errors
        raise

    except Exception as e:
        logger.error(f"PDF generation failed: {e}", exc_info=True)
        raise PDFGenerationError(
            f"PDF generation failed: {str(e)}",
            error_type="generation_error",
            original_error=e,
        )


def validate_pdf(pdf_bytes: bytes) -> bool:
    """
    Validate PDF has correct header and non-zero size.

    Args:
        pdf_bytes: Raw PDF file bytes

    Returns:
        bool: True if PDF is valid, False otherwise

    Implements: T077 - PDF validation
    """
    # Check non-zero bytes
    if not pdf_bytes or len(pdf_bytes) == 0:
        logger.error("PDF validation failed: empty file")
        return False

    # Check minimum reasonable size (a basic PDF should be at least a few KB)
    if len(pdf_bytes) < 1000:
        logger.error(f"PDF validation failed: file too small ({len(pdf_bytes)} bytes)")
        return False

    # Check valid PDF header (%PDF)
    if not pdf_bytes.startswith(b"%PDF"):
        logger.error("PDF validation failed: invalid PDF header")
        return False

    # Check for PDF end marker (%%EOF)
    # Allow for trailing whitespace/newlines
    if b"%%EOF" not in pdf_bytes[-128:]:
        logger.warning("PDF validation warning: EOF marker not found in last 128 bytes")
        # This is a warning, not a hard failure, as some valid PDFs may not end exactly with %%EOF

    logger.debug(f"PDF validation passed: {len(pdf_bytes)} bytes")
    return True
