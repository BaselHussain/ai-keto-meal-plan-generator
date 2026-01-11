---
id: 0028
title: Implement Calorie Breakdown Display T044
stage: green
date: 2026-01-11
surface: agent
model: claude-sonnet-4-5-20250929
feature: 001-keto-meal-plan-generator
branch: main
user: BaselHussain
command: /sp.implement
labels: ["frontend", "backend", "calorie-breakdown", "t044", "api", "review-screen"]
links:
  spec: specs/001-keto-meal-plan-generator/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - backend/src/api/quiz.py
  - frontend/components/quiz/ReviewScreen.tsx
  - specs/001-keto-meal-plan-generator/tasks.md
tests:
  - None (component enhancement, API contract update)
---

## Prompt

User requested: "/sp.implement proceed to T044 check if there is any skill in .claude directory that you can use for this task otherwise just proceed"

Task T044: Implement calorie breakdown display showing BMR, activity multiplier, goal adjustment, final target

Context:
- T043 (ReviewScreen component) already completed
- Backend calorie_calculator.py already has CalorieCalculation model with breakdown data
- API currently only returns final_target, needs to return full breakdown
- ReviewScreen needs new CalorieBreakdown card component

## Response snapshot

Implemented comprehensive calorie breakdown display across backend and frontend:

**Backend Changes (quiz.py):**
1. Created `CalorieBreakdown` Pydantic schema with fields:
   - bmr, tdee, activity_multiplier, goal_adjustment, goal_adjusted, final_target, clamped, warning
2. Updated `QuizSubmissionResponse` to include `calorie_breakdown` field
3. Imported ACTIVITY_MULTIPLIERS and GOAL_ADJUSTMENTS from calorie_calculator
4. Modified submit_quiz endpoint to construct and return full breakdown

**Frontend Changes (ReviewScreen.tsx):**
1. Added CalorieBreakdown TypeScript interface matching API response
2. Updated ReviewScreenProps to include calorieBreakdown prop
3. Added new icons: FaCalculator, FaInfoCircle
4. Created comprehensive Calorie Breakdown Card (section 5a) with:
   - **Always Visible Summary**: BMR, Activity Multiplier, TDEE, Goal Adjustment, Final Target
   - **Collapsible Details** (Show/Hide Details button):
     - "What is BMR?" explanation (blue info box)
     - "Activity Multiplier" explanation (purple info box)
     - "Goal Adjustment" explanation (orange info box)
     - Conditional "Safety Floor Applied" warning (yellow info box, if clamped)
     - Calculation formula display (gray box)
   - Color-coded goal adjustments: orange (deficit), blue (surplus), gray (maintenance)
   - Accessible with ARIA attributes and keyboard navigation

**Key Features:**
- Educational tooltips explain each calculation step
- Collapsible details reduce visual clutter (default: collapsed)
- Shows actual user's calculation formula with values
- Responsive design with Tailwind CSS
- Integrates seamlessly between existing Calorie Target and Action sections

Updated tasks.md line 216: marked T044 as [X] completed.

## Outcome

- ✅ Impact: Users now understand how their calorie target was calculated, improving transparency and trust
- 🧪 Tests: API contract updated, integration tests will need updating to include breakdown field
- 📁 Files: Modified backend/src/api/quiz.py (+37 lines), frontend/components/quiz/ReviewScreen.tsx (+143 lines), tasks.md
- 🔁 Next prompts: T045 (calorie floor warning display), integration testing for new API response, QuizContainer integration
- 🧠 Reflection: Breakdown display provides excellent UX by educating users on calorie science while maintaining clean UI through collapsible design

## Evaluation notes (flywheel)

- Failure modes observed: None - straightforward enhancement building on existing CalorieCalculation model
- Graders run and results (PASS/FAIL): N/A (manual review pending)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Test with clamped scenarios to verify warning display works correctly
