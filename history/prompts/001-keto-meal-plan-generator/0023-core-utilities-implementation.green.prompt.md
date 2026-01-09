---
id: 0023
title: core utilities implementation
stage: green
date: 2026-01-09
surface: agent
model: claude-sonnet-4-5-20250929
feature: 001-keto-meal-plan-generator
branch: 002-core-utilities
user: BaselHussain
command: /sp.implement
labels: ["core-utilities", "pydantic", "validation", "email-normalization", "calorie-calculator"]
links:
  spec: specs/001-keto-meal-plan-generator/spec.md
  ticket: null
  adr: null
  pr: https://github.com/BaselHussain/ai-keto-meal-plan-generator/pull/3
files:
  - backend/src/lib/email_utils.py
  - backend/src/lib/preferences.py
  - backend/src/services/calorie_calculator.py
  - backend/src/schemas/__init__.py
  - backend/src/schemas/quiz.py
  - backend/src/schemas/meal_plan.py
  - backend/src/schemas/auth.py
  - backend/src/schemas/recovery.py
  - backend/src/schemas/common.py
  - .claude/skills/test-imports/SKILL.md
  - specs/001-keto-meal-plan-generator/tasks.md
tests:
  - Import verification test (9 modules, all passed)
  - Email normalization logic verified
  - Calorie calculator formulas verified
  - Pydantic schema validation verified
---

## Prompt

now start T023-T026 in new branch from main with relevant sub-agents and skills in .claude make sure to mark done as the tasks complete for example if T023 is complete then mark it and move to T024

## Response snapshot

Successfully implemented core utilities tasks T023-T026:

**T023 - Email Normalization Utility:**
- Created `email_utils.py` with Gmail-specific normalization
- Lowercase and strip whitespace
- Remove dots from Gmail local part
- Strip +tags from Gmail addresses
- Convert googlemail.com → gmail.com
- Comprehensive docstrings and type hints

**T024 - Mifflin-St Jeor Calorie Calculator:**
- Created `calorie_calculator.py` with gender-specific BMR formulas
- 5 activity levels with multipliers (1.2 to 1.9)
- 3 goal adjustments (weight loss -400, muscle gain +250, maintenance 0)
- Calorie floor enforcement (1500 kcal male, 1200 kcal female)
- Logging for clamping events

**T025 - Food Preference Derivation:**
- Created `preferences.py` with preference extraction logic
- Maps 58 food items across 14 quiz steps
- Calculates excluded_foods (all items NOT selected)
- Extracts preferred_proteins (meat + fish + shellfish)
- Handles dietary_restrictions from step 17

**T026 - Pydantic API Validation Schemas:**
- Created 32 schemas across 6 files
- Quiz schemas: BiometricsData, QuizSubmission, QuizSubmissionResponse
- Meal plan schemas: PreferencesSummary, GenerationRequest, Meal, DayMealPlan, MealPlanStructure
- Auth schemas: EmailVerificationCodeRequest, EmailVerificationRequest, CheckoutInitiateRequest
- Recovery schemas: RecoverPlanRequest, MagicLinkVerifyResponse, AccountCreateRequest
- Common schemas: ErrorResponse, ValidationErrorResponse
- Comprehensive validation: email format, length constraints, enums, ranges
- Business logic: keto compliance (<30g carbs/day), meal structure validation

**Additional Work:**
- Created test-imports skill for import verification
- Fixed Pydantic and email-validator dependencies
- All 9 modules tested and importing successfully

## Outcome

- ✅ Impact: Core utilities and validation schemas fully implemented
- 🧪 Tests: Import verification (9/9 passed), basic functionality verified
- 📁 Files: 14 files created/modified (4 utilities, 6 schemas, 1 skill, 3 config)
- 🔁 Next prompts: Continue with T027-T029 (Base API Router Setup)
- 🧠 Reflection: Implementation went smoothly with backend-engineer agent. Import testing skill proved valuable for catching missing dependencies early. All schemas align with contract specifications.

## Evaluation notes (flywheel)

- Failure modes observed: Missing Pydantic and email-validator dependencies (resolved during import testing)
- Graders run and results (PASS/FAIL): Import verification PASS, Email normalization PASS, Calorie calculator PASS, Schema validation PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Consider adding unit tests for edge cases in Phase 2.5 as planned.
