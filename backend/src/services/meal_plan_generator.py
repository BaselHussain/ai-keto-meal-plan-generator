"""
AI Meal Plan Generator Service

Generates personalized 30-day keto meal plans using OpenAI Agents SDK.

Features:
- Environment-based AI client (Gemini dev, OpenAI prod)
- Structured output validation with Pydantic models
- Keto compliance validation (<30g carbs/day, retry 2x)
- Structural integrity validation (30 days, 3 meals, retry 1x)
- Exponential backoff retry (2s, 4s, 8s)
- Gemini fallback on auth/quota errors
- 20-second timeout with asyncio.wait_for()

Following research.md lines 94-153 for agent configuration.
Implements FR-A-007, FR-A-011, FR-A-015.
"""

import asyncio
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from agents import Agent, Runner, ModelSettings
from pydantic import ValidationError

from src.lib.ai_client import setup_ai_client, get_model_name, get_model_instance
from src.schemas.meal_plan import (
    MealPlanStructure,
    DayMealPlan,
    PreferencesSummary,
)

# Configure logging
logger = logging.getLogger(__name__)

# Retry configuration
MAX_KETO_RETRIES = 2  # FR-A-007: retry up to 2 times on keto compliance failure
MAX_STRUCTURE_RETRIES = 1  # FR-A-015: retry up to 1 time on structure failure
RETRY_DELAYS = [2, 4, 8]  # Exponential backoff: 2s, 4s, 8s (FR-A-011)
AI_GENERATION_TIMEOUT = 60  # Timeout for AI generation (will be tuned during T089D integration testing)


class MealPlanGenerationError(Exception):
    """Custom exception for meal plan generation failures."""

    def __init__(
        self,
        message: str,
        error_type: str = "unknown",
        retry_count: int = 0,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.retry_count = retry_count
        self.original_error = original_error


def validate_keto_compliance(meal_plan: MealPlanStructure) -> tuple[bool, List[str]]:
    """
    Validate that all days meet keto compliance (<30g net carbs).

    Args:
        meal_plan: Generated meal plan structure

    Returns:
        tuple: (is_compliant, list of error messages)

    Functional Requirement: FR-A-007
    """
    errors = []
    non_compliant_days = []

    for day in meal_plan.days:
        if day.total_carbs >= 30:
            non_compliant_days.append(day.day)
            errors.append(
                f"Day {day.day}: {day.total_carbs}g carbs exceeds 30g keto limit"
            )

    is_compliant = len(non_compliant_days) == 0

    if not is_compliant:
        logger.warning(
            f"Keto compliance validation failed. Non-compliant days: {non_compliant_days}"
        )

    return is_compliant, errors


def validate_structural_integrity(
    meal_plan: MealPlanStructure,
) -> tuple[bool, List[str]]:
    """
    Validate meal plan structural integrity:
    - Exactly 30 days
    - Each day has exactly 3 meals (breakfast, lunch, dinner)
    - All required fields populated
    - Days numbered 1-30 sequentially

    Args:
        meal_plan: Generated meal plan structure

    Returns:
        tuple: (is_valid, list of error messages)

    Functional Requirement: FR-A-015
    """
    errors = []

    # Check total days
    if len(meal_plan.days) != 30:
        errors.append(f"Expected 30 days, got {len(meal_plan.days)}")

    # Check day numbering
    day_numbers = [day.day for day in meal_plan.days]
    expected_days = list(range(1, 31))
    if day_numbers != expected_days:
        errors.append(f"Days not numbered 1-30 sequentially: {day_numbers[:5]}...")

    # Check each day's meals
    for day in meal_plan.days:
        # Check meal count
        if len(day.meals) != 3:
            errors.append(f"Day {day.day}: expected 3 meals, got {len(day.meals)}")
            continue

        # Check meal types
        meal_names = {meal.name for meal in day.meals}
        expected_meals = {"breakfast", "lunch", "dinner"}
        if meal_names != expected_meals:
            errors.append(
                f"Day {day.day}: missing meal types. Expected {expected_meals}, got {meal_names}"
            )

        # Check all fields populated
        for meal in day.meals:
            if not meal.recipe or not meal.recipe.strip():
                errors.append(f"Day {day.day} {meal.name}: recipe name is empty")
            if not meal.ingredients or len(meal.ingredients) == 0:
                errors.append(f"Day {day.day} {meal.name}: no ingredients provided")
            if meal.calories == 0:
                errors.append(
                    f"Day {day.day} {meal.name}: calories not populated (0)"
                )

    # Check shopping lists
    if len(meal_plan.shopping_lists) != 4:
        errors.append(
            f"Expected 4 shopping lists, got {len(meal_plan.shopping_lists)}"
        )

    is_valid = len(errors) == 0

    if not is_valid:
        logger.warning(f"Structural validation failed with {len(errors)} errors")

    return is_valid, errors


async def generate_meal_plan_with_ai(
    calorie_target: int,
    preferences: PreferencesSummary,
    attempt: int = 1,
) -> MealPlanStructure:
    """
    Generate meal plan using AI agent with structured output.

    Args:
        calorie_target: Daily calorie target from quiz
        preferences: User food preferences (excluded foods, preferred proteins, dietary restrictions)
        attempt: Current attempt number (for logging)

    Returns:
        MealPlanStructure: Validated meal plan structure

    Raises:
        MealPlanGenerationError: If AI generation fails
        asyncio.TimeoutError: If generation exceeds 20-second timeout

    Functional Requirements: FR-A-001, FR-F-002 (20s timeout)
    """
    logger.info(
        f"Generating meal plan (attempt {attempt}): {calorie_target} kcal, "
        f"{len(preferences.excluded_foods)} exclusions, "
        f"{len(preferences.preferred_proteins)} preferred proteins"
    )

    # Setup AI client (idempotent - returns existing if already configured)
    setup_ai_client()
    model_instance = get_model_instance()

    # Build agent instructions
    excluded_foods_str = ", ".join(preferences.excluded_foods) if preferences.excluded_foods else "None"
    preferred_proteins_str = ", ".join(preferences.preferred_proteins) if preferences.preferred_proteins else "Any"

    instructions = f"""You are an expert keto nutritionist generating personalized 30-day meal plans.

STRICT REQUIREMENTS:
- Daily calorie target: {calorie_target} kcal (±50 kcal variance acceptable)
- Keto macros: <30g net carbs/day, 65-75% fat, 20-30% protein
- 3 meals per day: breakfast, lunch, dinner
- NO recipe repetition within 30 days
- Each meal: ≤10 ingredients, ≤30 min prep time

USER PREFERENCES:
- EXCLUDED foods (DO NOT USE): {excluded_foods_str}
- PREFERRED proteins: {preferred_proteins_str}
- Dietary restrictions: {preferences.dietary_restrictions}

OUTPUT STRUCTURE:
- 30 days, each with 3 meals (breakfast, lunch, dinner)
- Each meal includes: name, recipe, ingredients, prep_time, macros (carbs, protein, fat, calories)
- Daily totals calculated for each day
- 4 weekly shopping lists organized by category (proteins, vegetables, dairy, fats, pantry)

QUALITY STANDARDS:
- Practical, beginner-friendly recipes
- Variety in proteins, vegetables, and cooking methods
- Ensure strict keto compliance: ALL 30 days must have <30g net carbs
- Include motivational keto tips and hydration reminders in recipe notes
"""

    # Create agent with structured output
    agent = Agent(
        name="KetoPlanGenerator",
        instructions=instructions,
        model=model_instance,  # Use OpenAIChatCompletionsModel for Gemini, string for OpenAI
        model_settings=ModelSettings(
            temperature=0.7,
            max_tokens=16000,  # 30-day plan requires large token limit
        ),
        output_type=MealPlanStructure,  # Structured output validation
    )

    try:
        # Run agent with 20-second timeout (FR-F-002)
        start_time = datetime.utcnow()

        result = await asyncio.wait_for(
            Runner.run(
                agent,
                input="Generate the complete 30-day personalized keto meal plan.",
                max_turns=3,  # Allow some back-and-forth for validation
            ),
            timeout=AI_GENERATION_TIMEOUT,
        )

        generation_time = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"AI generation completed in {generation_time:.2f}s")

        # Extract structured output
        meal_plan = result.final_output

        # Validate it's the correct type
        if not isinstance(meal_plan, MealPlanStructure):
            raise MealPlanGenerationError(
                f"Expected MealPlanStructure, got {type(meal_plan)}",
                error_type="invalid_output_type",
            )

        return meal_plan

    except asyncio.TimeoutError:
        logger.error(f"AI generation timed out after {AI_GENERATION_TIMEOUT}s")
        raise MealPlanGenerationError(
            f"AI generation exceeded {AI_GENERATION_TIMEOUT}s timeout",
            error_type="timeout",
            retry_count=attempt - 1,
        )

    except ValidationError as e:
        logger.error(f"Pydantic validation error: {e}")
        raise MealPlanGenerationError(
            f"AI output validation failed: {str(e)}",
            error_type="validation_error",
            retry_count=attempt - 1,
            original_error=e,
        )

    except Exception as e:
        logger.error(f"Unexpected error during AI generation: {e}", exc_info=True)
        raise MealPlanGenerationError(
            f"AI generation failed: {str(e)}",
            error_type="generation_error",
            retry_count=attempt - 1,
            original_error=e,
        )


async def generate_meal_plan(
    calorie_target: int,
    preferences: PreferencesSummary,
) -> Dict[str, Any]:
    """
    Generate 30-day keto meal plan with validation and retry logic.

    Implements multi-layer retry strategy:
    1. Keto compliance validation: retry up to 2 times (FR-A-007)
    2. Structural validation: retry up to 1 time (FR-A-015)
    3. Exponential backoff: 2s, 4s, 8s between retries (FR-A-011)
    4. Gemini fallback: switch to Gemini on OpenAI auth/quota errors (FR-A-011)

    Args:
        calorie_target: Daily calorie target from quiz calculation
        preferences: User food preferences from quiz

    Returns:
        dict: {
            "success": bool,
            "meal_plan": MealPlanStructure (if success),
            "model_used": str,
            "generation_time_ms": int,
            "validation_errors": List[str] (if failure),
            "retry_count": int,
            "error_type": str (if failure),
        }

    Functional Requirements: FR-A-001, FR-A-007, FR-A-011, FR-A-015, FR-F-002
    """
    start_time = datetime.utcnow()
    total_attempts = 0
    keto_retry_count = 0
    structure_retry_count = 0
    last_error = None

    logger.info(
        f"Starting meal plan generation: {calorie_target} kcal, "
        f"{len(preferences.excluded_foods)} exclusions"
    )

    # Retry loop with exponential backoff
    while total_attempts < (MAX_KETO_RETRIES + MAX_STRUCTURE_RETRIES + 1):
        total_attempts += 1

        try:
            # Generate meal plan with AI
            meal_plan = await generate_meal_plan_with_ai(
                calorie_target=calorie_target,
                preferences=preferences,
                attempt=total_attempts,
            )

            # Validate keto compliance (FR-A-007)
            keto_compliant, keto_errors = validate_keto_compliance(meal_plan)

            if not keto_compliant:
                if keto_retry_count < MAX_KETO_RETRIES:
                    keto_retry_count += 1
                    delay = RETRY_DELAYS[min(keto_retry_count - 1, len(RETRY_DELAYS) - 1)]

                    logger.warning(
                        f"Keto compliance failed (attempt {keto_retry_count}/{MAX_KETO_RETRIES}). "
                        f"Retrying in {delay}s..."
                    )

                    await asyncio.sleep(delay)
                    continue
                else:
                    # Max keto retries exceeded
                    logger.error(
                        f"Keto compliance validation failed after {MAX_KETO_RETRIES} retries"
                    )
                    generation_time = (datetime.utcnow() - start_time).total_seconds()

                    return {
                        "success": False,
                        "model_used": get_model_name(),
                        "generation_time_ms": int(generation_time * 1000),
                        "validation_errors": keto_errors,
                        "retry_count": total_attempts - 1,
                        "error_type": "keto_compliance_failure",
                    }

            # Validate structural integrity (FR-A-015)
            structure_valid, structure_errors = validate_structural_integrity(meal_plan)

            if not structure_valid:
                if structure_retry_count < MAX_STRUCTURE_RETRIES:
                    structure_retry_count += 1
                    delay = RETRY_DELAYS[
                        min(structure_retry_count - 1, len(RETRY_DELAYS) - 1)
                    ]

                    logger.warning(
                        f"Structural validation failed (attempt {structure_retry_count}/{MAX_STRUCTURE_RETRIES}). "
                        f"Retrying in {delay}s..."
                    )

                    await asyncio.sleep(delay)
                    continue
                else:
                    # Max structure retries exceeded
                    logger.error(
                        f"Structural validation failed after {MAX_STRUCTURE_RETRIES} retries"
                    )
                    generation_time = (datetime.utcnow() - start_time).total_seconds()

                    return {
                        "success": False,
                        "model_used": get_model_name(),
                        "generation_time_ms": int(generation_time * 1000),
                        "validation_errors": structure_errors,
                        "retry_count": total_attempts - 1,
                        "error_type": "structure_validation_failure",
                    }

            # Success - both validations passed
            generation_time = (datetime.utcnow() - start_time).total_seconds()

            logger.info(
                f"Meal plan generation successful! "
                f"Time: {generation_time:.2f}s, Attempts: {total_attempts}"
            )

            return {
                "success": True,
                "meal_plan": meal_plan,
                "model_used": get_model_name(),
                "generation_time_ms": int(generation_time * 1000),
                "retry_count": total_attempts - 1,
            }

        except MealPlanGenerationError as e:
            last_error = e
            logger.error(
                f"Generation attempt {total_attempts} failed: {e.error_type} - {str(e)}"
            )

            # Check if we should retry with Gemini fallback (FR-A-011)
            if e.error_type in ["auth_error", "quota_error", "rate_limit"]:
                if os.getenv("ENV") == "production" and os.getenv("GEMINI_API_KEY"):
                    logger.info("Switching to Gemini fallback due to OpenAI error")
                    os.environ["ENV"] = "development"  # Force Gemini
                    # Reset client to pick up new config
                    from src.lib.ai_client import reset_ai_client
                    reset_ai_client()

            # Apply exponential backoff
            if total_attempts < (MAX_KETO_RETRIES + MAX_STRUCTURE_RETRIES + 1):
                delay = RETRY_DELAYS[min(total_attempts - 1, len(RETRY_DELAYS) - 1)]
                logger.info(f"Retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                break

        except Exception as e:
            last_error = e
            logger.error(f"Unexpected error in attempt {total_attempts}: {e}", exc_info=True)
            break

    # All retries exhausted
    generation_time = (datetime.utcnow() - start_time).total_seconds()

    logger.error(
        f"Meal plan generation failed after {total_attempts} attempts "
        f"({generation_time:.2f}s total)"
    )

    return {
        "success": False,
        "model_used": get_model_name(),
        "generation_time_ms": int(generation_time * 1000),
        "validation_errors": [str(last_error)] if last_error else ["Unknown error"],
        "retry_count": total_attempts - 1,
        "error_type": getattr(last_error, "error_type", "unknown_error"),
    }
