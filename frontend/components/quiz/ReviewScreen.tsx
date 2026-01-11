'use client';

import { useState } from 'react';
import {
  FaUser,
  FaUtensils,
  FaBan,
  FaCalendarAlt,
  FaBullseye,
  FaEdit,
  FaCheckCircle,
  FaChevronDown,
  FaChevronUp,
  FaCalculator,
  FaInfoCircle,
  FaExclamationTriangle,
} from 'react-icons/fa';
import { CompleteQuizData, getTotalFoodItemsCount } from '@/lib/validations/quiz/steps';

/**
 * ReviewScreen Component
 * Displays complete quiz summary with all 20 steps data
 * Following frontend-quiz-engineer.md guidelines for UI/UX consistency
 */

interface CalorieBreakdown {
  bmr: number;
  tdee: number;
  activity_multiplier: number;
  goal_adjustment: number;
  goal_adjusted: number;
  final_target: number;
  clamped: boolean;
  warning?: string;
}

interface ReviewScreenProps {
  quizData: CompleteQuizData;
  calorieTarget: number;
  calorieBreakdown: CalorieBreakdown;
  quizId: string;
  onEdit: (stepNumber: number) => void;
  onProceedToPayment: () => void;
  isSubmitting?: boolean;
  submissionError?: string;
}

// Food category mappings for display
const FOOD_CATEGORIES = {
  step_3: 'Poultry',
  step_4: 'Fish & Seafood',
  step_5: 'Low-Carb Vegetables',
  step_6: 'Cruciferous Vegetables',
  step_7: 'Leafy Greens',
  step_8: 'Additional Vegetables',
  step_9: 'Additional Proteins',
  step_10: 'Organ Meats',
  step_11: 'Berries',
  step_12: 'Nuts & Seeds',
  step_13: 'Herbs & Spices',
  step_14: 'Fats & Oils',
  step_15: 'Beverages',
  step_16: 'Dairy & Alternatives',
} as const;

export function ReviewScreen({
  quizData,
  calorieTarget,
  calorieBreakdown,
  quizId,
  onEdit,
  onProceedToPayment,
  isSubmitting = false,
  submissionError,
}: ReviewScreenProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const [showFullRestrictions, setShowFullRestrictions] = useState(false);
  const [showBreakdownDetails, setShowBreakdownDetails] = useState(false);

  // Format helpers
  const formatGender = (gender: string): string => {
    return gender === 'male' ? 'Male' : 'Female';
  };

  const formatActivityLevel = (level: string): string => {
    const levels: Record<string, string> = {
      sedentary: 'Sedentary',
      lightly_active: 'Lightly Active',
      moderately_active: 'Moderately Active',
      very_active: 'Very Active',
      super_active: 'Super Active',
    };
    return levels[level] || level;
  };

  const formatGoal = (goal: string): string => {
    const goals: Record<string, string> = {
      weight_loss: 'Weight Loss',
      maintenance: 'Maintenance',
      muscle_gain: 'Muscle Gain',
    };
    return goals[goal] || goal;
  };

  const formatMealsPerDay = (meals: string): string => {
    return meals === '3_meals' ? '3 Meals per Day' : meals;
  };

  // Food category counts
  const getFoodCategoryCounts = (): Array<{ category: string; count: number; step: string }> => {
    return Object.entries(FOOD_CATEGORIES).map(([step, category]) => ({
      category,
      count: (quizData[step as keyof typeof FOOD_CATEGORIES] as string[]).length,
      step,
    }));
  };

  const totalFoodItems = getTotalFoodItemsCount(quizData);
  const showFoodWarning = totalFoodItems >= 10 && totalFoodItems <= 14;

  // Toggle category expansion
  const toggleCategory = (step: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(step)) {
      newExpanded.delete(step);
    } else {
      newExpanded.add(step);
    }
    setExpandedCategories(newExpanded);
  };

  // Truncate dietary restrictions for display
  const dietaryRestrictions = quizData.step_17;
  const shouldTruncate = dietaryRestrictions.length > 200;
  const displayRestrictions = shouldTruncate && !showFullRestrictions
    ? dietaryRestrictions.slice(0, 200) + '...'
    : dietaryRestrictions;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center space-y-3 mb-8">
        <div className="flex items-center justify-center space-x-2">
          <FaCheckCircle className="text-green-500 text-3xl" aria-hidden="true" />
          <h2 className="text-2xl md:text-3xl font-bold text-gray-900">
            Review Your Personalized Profile
          </h2>
        </div>
        <p className="text-gray-600">
          Check your details before proceeding to payment
        </p>
      </div>

      {/* Submission Error */}
      {submissionError && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{submissionError}</p>
        </div>
      )}

      {/* 1. Demographics Card */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3">
            <FaUser className="text-green-600 text-xl" aria-hidden="true" />
            <h3 className="text-lg font-semibold text-gray-900">Demographics</h3>
          </div>
          <button
            type="button"
            onClick={() => onEdit(1)}
            className="flex items-center space-x-1 text-green-600 hover:text-green-700 transition-colors"
            aria-label="Edit demographics"
          >
            <FaEdit className="text-sm" aria-hidden="true" />
            <span className="text-sm font-medium">Edit</span>
          </button>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Gender:</span>
            <p className="font-medium text-gray-900">{formatGender(quizData.step_1)}</p>
          </div>
          <div>
            <span className="text-gray-500">Activity:</span>
            <p className="font-medium text-gray-900">{formatActivityLevel(quizData.step_2)}</p>
          </div>
          <div>
            <span className="text-gray-500">Age:</span>
            <p className="font-medium text-gray-900">{quizData.step_20.age} years</p>
          </div>
          <div>
            <span className="text-gray-500">Weight:</span>
            <p className="font-medium text-gray-900">{quizData.step_20.weight_kg} kg</p>
          </div>
          <div>
            <span className="text-gray-500">Height:</span>
            <p className="font-medium text-gray-900">{quizData.step_20.height_cm} cm</p>
          </div>
          <div>
            <span className="text-gray-500">Goal:</span>
            <p className="font-medium text-gray-900">{formatGoal(quizData.step_20.goal)}</p>
          </div>
        </div>
      </div>

      {/* 2. Food Preferences Card */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3">
            <FaUtensils className="text-green-600 text-xl" aria-hidden="true" />
            <h3 className="text-lg font-semibold text-gray-900">Food Preferences</h3>
          </div>
          <button
            type="button"
            onClick={() => onEdit(3)}
            className="flex items-center space-x-1 text-green-600 hover:text-green-700 transition-colors"
            aria-label="Edit food preferences"
          >
            <FaEdit className="text-sm" aria-hidden="true" />
            <span className="text-sm font-medium">Edit</span>
          </button>
        </div>

        <div className="mb-4">
          <p className="text-sm text-gray-600">
            Total food items selected: <span className="font-semibold text-gray-900">{totalFoodItems}</span>
          </p>
          {showFoodWarning && (
            <div className="mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
              <p className="text-sm text-yellow-800">
                You've selected {totalFoodItems} items. Consider adding more variety for better meal plan diversity.
              </p>
            </div>
          )}
        </div>

        {/* Collapsible category breakdown */}
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-700 mb-2">Category Breakdown:</p>
          {getFoodCategoryCounts().map(({ category, count, step }) => (
            <div key={step} className="border border-gray-200 rounded-lg">
              <button
                type="button"
                onClick={() => toggleCategory(step)}
                className="w-full flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
                aria-expanded={expandedCategories.has(step)}
                aria-controls={`category-${step}`}
              >
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium text-gray-900">{category}</span>
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                    {count} items
                  </span>
                </div>
                {expandedCategories.has(step) ? (
                  <FaChevronUp className="text-gray-400 text-xs" aria-hidden="true" />
                ) : (
                  <FaChevronDown className="text-gray-400 text-xs" aria-hidden="true" />
                )}
              </button>
              {expandedCategories.has(step) && count > 0 && (
                <div
                  id={`category-${step}`}
                  className="px-3 pb-3 pt-0"
                  role="region"
                  aria-label={`${category} items`}
                >
                  <div className="flex flex-wrap gap-2">
                    {(quizData[step as keyof typeof FOOD_CATEGORIES] as string[]).map((item) => (
                      <span
                        key={item}
                        className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 3. Dietary Restrictions Card (conditional) */}
      {dietaryRestrictions && (
        <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center space-x-3">
              <FaBan className="text-green-600 text-xl" aria-hidden="true" />
              <h3 className="text-lg font-semibold text-gray-900">Dietary Restrictions</h3>
            </div>
            <button
              type="button"
              onClick={() => onEdit(17)}
              className="flex items-center space-x-1 text-green-600 hover:text-green-700 transition-colors"
              aria-label="Edit dietary restrictions"
            >
              <FaEdit className="text-sm" aria-hidden="true" />
              <span className="text-sm font-medium">Edit</span>
            </button>
          </div>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">
            {displayRestrictions}
          </p>
          {shouldTruncate && (
            <button
              type="button"
              onClick={() => setShowFullRestrictions(!showFullRestrictions)}
              className="mt-2 text-sm text-green-600 hover:text-green-700 font-medium"
            >
              {showFullRestrictions ? 'Show less' : 'Read more'}
            </button>
          )}
        </div>
      )}

      {/* 4. Meal Plan Preferences Card */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3">
            <FaCalendarAlt className="text-green-600 text-xl" aria-hidden="true" />
            <h3 className="text-lg font-semibold text-gray-900">Meal Plan Preferences</h3>
          </div>
          <button
            type="button"
            onClick={() => onEdit(18)}
            className="flex items-center space-x-1 text-green-600 hover:text-green-700 transition-colors"
            aria-label="Edit meal plan preferences"
          >
            <FaEdit className="text-sm" aria-hidden="true" />
            <span className="text-sm font-medium">Edit</span>
          </button>
        </div>
        <div className="space-y-3">
          <div>
            <span className="text-sm text-gray-500">Meals per day:</span>
            <p className="font-medium text-gray-900">{formatMealsPerDay(quizData.step_18)}</p>
          </div>
          {quizData.step_19.length > 0 && (
            <div>
              <span className="text-sm text-gray-500">Behavioral patterns:</span>
              <div className="flex flex-wrap gap-2 mt-1">
                {quizData.step_19.map((pattern) => (
                  <span
                    key={pattern}
                    className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded"
                  >
                    {pattern}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 5. Calorie Target Card */}
      <div className="bg-gradient-to-br from-green-50 to-green-100 border-2 border-green-200 rounded-xl p-6 shadow-md">
        <div className="flex flex-col items-center space-y-4">
          <FaBullseye className="text-green-600 text-4xl" aria-hidden="true" />
          <div className="text-center">
            <h3 className="text-lg font-semibold text-gray-700 mb-2">
              Your Daily Calorie Target
            </h3>
            <p className="text-5xl font-bold text-green-600" aria-label={`${calorieTarget} calories`}>
              {calorieTarget}
            </p>
            <p className="text-sm text-gray-600 mt-1">calories per day</p>
          </div>
          <p className="text-sm text-center text-gray-600 max-w-md">
            Based on your profile, we've calculated your personalized calorie target to help you achieve your {formatGoal(quizData.step_20.goal).toLowerCase()} goal.
          </p>
        </div>
      </div>

      {/* 5a. Calorie Floor Warning Banner (T045) - Always visible when clamped */}
      {calorieBreakdown.clamped && (
        <div
          className="bg-yellow-50 border-l-4 border-yellow-400 rounded-r-lg p-5 shadow-sm"
          role="alert"
          aria-live="polite"
        >
          <div className="flex items-start space-x-3">
            <FaExclamationTriangle
              className="text-yellow-600 text-2xl flex-shrink-0 mt-0.5"
              aria-hidden="true"
            />
            <div className="flex-1">
              <h4 className="text-base font-semibold text-yellow-900 mb-2">
                Safety Minimum Applied
              </h4>
              <p className="text-sm text-yellow-800 leading-relaxed">
                {quizData.step_1 === 'male'
                  ? 'Your calculated target was below the safe minimum of 1,500 calories per day for men. We\'ve adjusted it to this minimum to ensure healthy, sustainable nutrition.'
                  : 'Your calculated target was below the safe minimum of 1,200 calories per day for women. We\'ve adjusted it to this minimum to ensure healthy, sustainable nutrition.'}
              </p>
              <div className="mt-3 flex items-start space-x-2 bg-yellow-100 rounded-md p-3">
                <FaInfoCircle className="text-yellow-700 flex-shrink-0 mt-0.5" aria-hidden="true" />
                <p className="text-xs text-yellow-900">
                  <strong>Why this matters:</strong> Consuming fewer than {quizData.step_1 === 'male' ? '1,500' : '1,200'} calories
                  can slow metabolism, cause nutrient deficiencies, and make it harder to sustain your {formatGoal(quizData.step_20.goal).toLowerCase()}
                  goal long-term. This adjusted target prioritizes your health while still supporting your goals.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 5b. Calorie Breakdown Card (T044) */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3">
            <FaCalculator className="text-green-600 text-xl" aria-hidden="true" />
            <h3 className="text-lg font-semibold text-gray-900">How We Calculated Your Target</h3>
          </div>
          <button
            type="button"
            onClick={() => setShowBreakdownDetails(!showBreakdownDetails)}
            className="flex items-center space-x-1 text-green-600 hover:text-green-700 transition-colors"
            aria-expanded={showBreakdownDetails}
            aria-label={showBreakdownDetails ? 'Hide calculation details' : 'Show calculation details'}
          >
            {showBreakdownDetails ? (
              <>
                <FaChevronUp className="text-sm" aria-hidden="true" />
                <span className="text-sm font-medium">Hide Details</span>
              </>
            ) : (
              <>
                <FaChevronDown className="text-sm" aria-hidden="true" />
                <span className="text-sm font-medium">Show Details</span>
              </>
            )}
          </button>
        </div>

        {/* Breakdown Summary (Always Visible) */}
        <div className="space-y-3">
          <div className="flex justify-between items-center py-2 border-b border-gray-100">
            <span className="text-sm text-gray-600">Basal Metabolic Rate (BMR)</span>
            <span className="font-semibold text-gray-900">{Math.round(calorieBreakdown.bmr)} kcal/day</span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-gray-100">
            <span className="text-sm text-gray-600">Activity Multiplier</span>
            <span className="font-semibold text-gray-900">×{calorieBreakdown.activity_multiplier}</span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-gray-100">
            <span className="text-sm text-gray-600">Total Daily Energy (TDEE)</span>
            <span className="font-semibold text-gray-900">{Math.round(calorieBreakdown.tdee)} kcal/day</span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-gray-100">
            <span className="text-sm text-gray-600">Goal Adjustment</span>
            <span className={`font-semibold ${calorieBreakdown.goal_adjustment < 0 ? 'text-orange-600' : calorieBreakdown.goal_adjustment > 0 ? 'text-blue-600' : 'text-gray-900'}`}>
              {calorieBreakdown.goal_adjustment > 0 ? '+' : ''}{calorieBreakdown.goal_adjustment} kcal/day
            </span>
          </div>
          <div className="flex justify-between items-center py-3 bg-green-50 rounded-lg px-3 mt-2">
            <span className="text-base font-medium text-gray-900">Final Target</span>
            <span className="text-xl font-bold text-green-600">{calorieBreakdown.final_target} kcal/day</span>
          </div>
        </div>

        {/* Detailed Explanation (Collapsible) */}
        {showBreakdownDetails && (
          <div className="mt-6 pt-6 border-t border-gray-200 space-y-4">
            <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
              <div className="flex items-start space-x-2">
                <FaInfoCircle className="text-blue-600 mt-0.5 flex-shrink-0" aria-hidden="true" />
                <div className="text-sm text-blue-900">
                  <p className="font-semibold mb-2">What is BMR?</p>
                  <p>
                    Your Basal Metabolic Rate ({Math.round(calorieBreakdown.bmr)} kcal) is the number of calories
                    your body burns at complete rest. This is calculated using the Mifflin-St Jeor equation based
                    on your age, weight, height, and gender.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-purple-50 border border-purple-100 rounded-lg p-4">
              <div className="flex items-start space-x-2">
                <FaInfoCircle className="text-purple-600 mt-0.5 flex-shrink-0" aria-hidden="true" />
                <div className="text-sm text-purple-900">
                  <p className="font-semibold mb-2">Activity Multiplier ({calorieBreakdown.activity_multiplier}×)</p>
                  <p>
                    We multiply your BMR by {calorieBreakdown.activity_multiplier} to account for your activity level
                    ({formatActivityLevel(quizData.step_2)}). This gives us your Total Daily Energy Expenditure
                    (TDEE) of {Math.round(calorieBreakdown.tdee)} kcal.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-orange-50 border border-orange-100 rounded-lg p-4">
              <div className="flex items-start space-x-2">
                <FaInfoCircle className="text-orange-600 mt-0.5 flex-shrink-0" aria-hidden="true" />
                <div className="text-sm text-orange-900">
                  <p className="font-semibold mb-2">Goal Adjustment ({calorieBreakdown.goal_adjustment} kcal)</p>
                  <p>
                    {calorieBreakdown.goal_adjustment < 0
                      ? `To support your ${formatGoal(quizData.step_20.goal).toLowerCase()} goal, we create a calorie deficit of ${Math.abs(calorieBreakdown.goal_adjustment)} kcal per day for safe, sustainable fat loss.`
                      : calorieBreakdown.goal_adjustment > 0
                      ? `To support your ${formatGoal(quizData.step_20.goal).toLowerCase()} goal, we add a calorie surplus of ${calorieBreakdown.goal_adjustment} kcal per day for lean muscle gain.`
                      : `For maintenance, your calorie target matches your TDEE with no adjustment.`
                    }
                  </p>
                </div>
              </div>
            </div>

            {calorieBreakdown.clamped && calorieBreakdown.warning && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex items-start space-x-2">
                  <FaInfoCircle className="text-yellow-600 mt-0.5 flex-shrink-0" aria-hidden="true" />
                  <div className="text-sm text-yellow-900">
                    <p className="font-semibold mb-2">Safety Floor Applied</p>
                    <p>{calorieBreakdown.warning}</p>
                  </div>
                </div>
              </div>
            )}

            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <p className="text-xs text-gray-600">
                <strong>Calculation Formula:</strong> BMR × Activity Multiplier + Goal Adjustment = Final Target
                <br />
                <strong>Your Calculation:</strong> {Math.round(calorieBreakdown.bmr)} × {calorieBreakdown.activity_multiplier} {calorieBreakdown.goal_adjustment >= 0 ? '+' : ''} {calorieBreakdown.goal_adjustment} = {calorieBreakdown.final_target} kcal/day
              </p>
            </div>
          </div>
        )}
      </div>

      {/* 6. Action Section */}
      <div className="flex flex-col sm:flex-row gap-4 pt-4">
        <button
          type="button"
          onClick={() => onEdit(1)}
          disabled={isSubmitting}
          className="flex-1 px-6 py-4 bg-white border-2 border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 hover:border-gray-400 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Review and edit quiz responses"
        >
          Review & Edit
        </button>
        <button
          type="button"
          onClick={onProceedToPayment}
          disabled={isSubmitting}
          className="flex-1 px-6 py-4 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 shadow-md hover:shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
          aria-label="Proceed to payment"
        >
          {isSubmitting ? (
            <>
              <svg
                className="animate-spin h-5 w-5 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              <span>Processing...</span>
            </>
          ) : (
            <span>Proceed to Payment</span>
          )}
        </button>
      </div>

      {/* Quiz ID Reference (for debugging/support) */}
      <div className="text-center text-xs text-gray-400 pt-2">
        Quiz ID: {quizId}
      </div>
    </div>
  );
}
