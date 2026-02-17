'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { StepProgress } from './StepProgress';
import { Step01Gender } from './steps/Step01Gender';
import { Step02Activity } from './steps/Step02Activity';
import { Step17Restrictions } from './steps/Step17Restrictions';
import { Step18MealFrequency } from './steps/Step18MealFrequency';
import { Step19PersonalTraits } from './steps/Step19PersonalTraits';
import { Step20Biometrics } from './steps/Step20Biometrics';
import { FoodSelectionGrid } from './FoodSelectionGrid';
import { SaveProgressModal } from './SaveProgressModal';
import { ReviewScreen } from './ReviewScreen';
import { EmailVerification } from './EmailVerification';
import { useQuizState } from '../../hooks/useQuizState';
import { getFoodCategoryByStep } from '../../lib/foodCategories';
import {
  submitQuiz,
  saveQuizProgress,
  loadQuizProgress,
} from '../../services/quizService';
import { triggerDevDelivery } from '../../services/deliveryService';
import { isAuthenticated as checkAuth } from '../../services/authService';
import type { CompleteQuizData } from '../../lib/validations/quiz/steps';
import type { CalorieBreakdown } from '../../services/quizService';

// Flow phases after quiz completion
type Phase = 'quiz' | 'email_collect' | 'review' | 'email_verify' | 'processing' | 'success' | 'error';

// Animation variants for step transitions (300-400ms ease-in-out per T108)
const stepVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 300 : -300,
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
  },
  exit: (direction: number) => ({
    x: direction < 0 ? 300 : -300,
    opacity: 0,
  }),
};

const stepTransition = {
  type: 'tween' as const,
  ease: 'easeInOut' as const,
  duration: 0.35, // 350ms (within 300-400ms range)
};

// Phase transition animation
const phaseVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 },
};

export function QuizContainer() {
  const router = useRouter();
  const {
    form,
    currentStep,
    totalSteps,
    nextStep,
    previousStep,
    canGoBack,
    isLastStep,
    goToStep,
  } = useQuizState();

  const { setValue, watch, getValues } = form;

  // Track navigation direction for animation (1 = forward, -1 = backward)
  const [direction, setDirection] = useState(1);
  const [prevStep, setPrevStep] = useState(currentStep);

  // T112: SaveProgressModal state (appears after Step 10)
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [hasShownSaveModal, setHasShownSaveModal] = useState(false);

  // Check if user is authenticated
  const [isUserAuthenticated, setIsUserAuthenticated] = useState(false);

  // Post-quiz flow state
  const [phase, setPhase] = useState<Phase>('quiz');
  const [email, setEmail] = useState('');
  const [emailError, setEmailError] = useState('');
  const [quizId, setQuizId] = useState('');
  const [calorieTarget, setCalorieTarget] = useState(0);
  const [calorieBreakdown, setCalorieBreakdown] = useState<CalorieBreakdown | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionError, setSubmissionError] = useState('');
  const [deliveryError, setDeliveryError] = useState('');

  useEffect(() => {
    setIsUserAuthenticated(checkAuth());
  }, []);

  // T114: Load saved progress on mount for authenticated users
  useEffect(() => {
    const loadSavedProgress = async () => {
      if (!isUserAuthenticated) return;

      try {
        const savedProgress = await loadQuizProgress();
        if (savedProgress) {
          // Restore quiz data
          Object.entries(savedProgress.quiz_data).forEach(([key, value]) => {
            setValue(key as any, value);
          });

          console.log(`Loaded saved progress from step ${savedProgress.current_step}`);
        }
      } catch (error) {
        console.error('Failed to load saved progress:', error);
      }
    };

    loadSavedProgress();
  }, [isUserAuthenticated, setValue]);

  // Update direction when step changes
  if (currentStep !== prevStep) {
    setDirection(currentStep > prevStep ? 1 : -1);
    setPrevStep(currentStep);
  }

  // T112: Show SaveProgressModal after Step 10 (only once, only for unauthenticated users)
  useEffect(() => {
    if (
      currentStep === 11 &&
      !hasShownSaveModal &&
      !isUserAuthenticated
    ) {
      setShowSaveModal(true);
      setHasShownSaveModal(true);
    }
  }, [currentStep, hasShownSaveModal, isUserAuthenticated]);

  // T113: Save progress automatically for authenticated users
  const saveProgressIfAuthenticated = async () => {
    if (!isUserAuthenticated) return;

    try {
      const quizData = getValues();
      await saveQuizProgress(currentStep, quizData);
      console.log(`Auto-saved progress at step ${currentStep}`);
    } catch (error) {
      console.error('Failed to auto-save progress:', error);
    }
  };

  // Wrapped navigation handlers to set direction
  const handleNext = async () => {
    // Save progress before navigating (for authenticated users)
    await saveProgressIfAuthenticated();

    if (isLastStep) {
      // Move to email collection phase
      setDirection(1);
      setPhase('email_collect');
      return;
    }

    setDirection(1);
    nextStep();
  };

  const handlePrevious = () => {
    setDirection(-1);
    previousStep();
  };

  // Handle "Create Account" from SaveProgressModal
  const handleCreateAccount = () => {
    setShowSaveModal(false);
    router.push('/create-account?return=/quiz');
  };

  // Handle "Continue Without Account" from SaveProgressModal
  const handleContinueWithoutAccount = () => {
    setShowSaveModal(false);
  };

  // Email collection and quiz submission
  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setEmailError('');

    // Basic email validation
    const emailTrimmed = email.trim().toLowerCase();
    if (!emailTrimmed || !emailTrimmed.includes('@') || emailTrimmed.length < 5) {
      setEmailError('Please enter a valid email address.');
      return;
    }

    setIsSubmitting(true);
    setSubmissionError('');

    try {
      const quizData = getValues() as unknown as CompleteQuizData;
      const result = await submitQuiz(quizData, emailTrimmed);

      setQuizId(result.quiz_id);
      setCalorieTarget(result.calorie_target);
      setCalorieBreakdown(result.calorie_breakdown);
      setEmail(emailTrimmed);
      setPhase('review');
    } catch (error: any) {
      setSubmissionError(error.message || 'Failed to submit quiz. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle edit from ReviewScreen - go back to specific quiz step
  const handleEdit = useCallback((stepNumber: number) => {
    goToStep(stepNumber);
    setPhase('quiz');
    // Reset submission state so user can re-submit after editing
    setQuizId('');
    setCalorieTarget(0);
    setCalorieBreakdown(null);
  }, [goToStep]);

  // Handle "Proceed to Payment" from ReviewScreen -> go to email verification
  const handleProceedFromReview = useCallback(() => {
    setPhase('email_verify');
  }, []);

  // Handle email verification success -> trigger delivery
  const handleEmailVerified = useCallback(async () => {
    setPhase('processing');
    setDeliveryError('');

    try {
      const result = await triggerDevDelivery(quizId, email);

      if (result.success) {
        setPhase('success');
      } else {
        setDeliveryError(result.message || 'Delivery failed. Please try again.');
        setPhase('error');
      }
    } catch (error: any) {
      setDeliveryError(error.message || 'Failed to trigger delivery. Please try again.');
      setPhase('error');
    }
  }, [quizId, email]);

  // Render the current step component
  const renderStep = () => {
    // Steps 3-16: Food Selection using FoodSelectionGrid
    if (currentStep >= 3 && currentStep <= 16) {
      const category = getFoodCategoryByStep(currentStep);
      if (!category) {
        return (
          <div className="text-center py-12">
            <p className="text-red-600">Error: Category not found for step {currentStep}</p>
          </div>
        );
      }

      const fieldName = `step_${currentStep}`;

      return (
        <FoodSelectionGrid
          title={category.title}
          subtitle={category.subtitle}
          items={category.items}
          selectedItems={(watch(fieldName as any) || []) as string[]}
          onChange={(items) => setValue(fieldName as any, items)}
          minItems={category.minItems}
          maxItems={category.maxItems}
        />
      );
    }

    // Individual step components
    switch (currentStep) {
      case 1:
        return (
          <Step01Gender
            value={watch('step_1')}
            onChange={(value) => setValue('step_1', value)}
          />
        );
      case 2:
        return (
          <Step02Activity
            value={watch('step_2')}
            onChange={(value) => setValue('step_2', value)}
          />
        );
      case 17:
        return (
          <Step17Restrictions
            value={watch('step_17')}
            onChange={(value) => setValue('step_17', value)}
          />
        );
      case 18:
        return (
          <Step18MealFrequency
            value={watch('step_18')}
            onChange={(value) => setValue('step_18', value)}
          />
        );
      case 19:
        return (
          <Step19PersonalTraits
            value={watch('step_19')}
            onChange={(value) => setValue('step_19', value)}
          />
        );
      case 20:
        return (
          <Step20Biometrics
            value={watch('step_20')}
            onChange={(value) => setValue('step_20', value)}
          />
        );
      default:
        return (
          <div className="text-center py-12">
            <p className="text-red-600">Error: Unknown step {currentStep}</p>
          </div>
        );
    }
  };

  // =========================================================================
  // Phase: Email Collection (after quiz step 20)
  // =========================================================================
  if (phase === 'email_collect') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 py-8 px-4">
        <div className="max-w-lg mx-auto">
          <motion.div
            variants={phaseVariants}
            initial="initial"
            animate="animate"
            className="bg-white rounded-2xl shadow-xl p-8"
          >
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Almost There!
              </h2>
              <p className="text-gray-600">
                Enter your email to receive your personalized 30-day keto meal plan.
              </p>
            </div>

            <form onSubmit={handleEmailSubmit} className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                  Email Address
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => { setEmail(e.target.value); setEmailError(''); }}
                  placeholder="your@email.com"
                  className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-green-500 focus:ring-2 focus:ring-green-200 focus:outline-none text-lg"
                  required
                  autoFocus
                  disabled={isSubmitting}
                />
                {emailError && (
                  <p className="mt-1 text-sm text-red-600">{emailError}</p>
                )}
              </div>

              {submissionError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-800">{submissionError}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-3 px-4 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors duration-200 flex items-center justify-center space-x-2"
              >
                {isSubmitting ? (
                  <>
                    <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <span>Analyzing Your Profile...</span>
                  </>
                ) : (
                  <span>See My Results</span>
                )}
              </button>

              <button
                type="button"
                onClick={() => setPhase('quiz')}
                disabled={isSubmitting}
                className="w-full text-sm text-gray-500 hover:text-gray-700 font-medium transition-colors"
              >
                Go Back to Quiz
              </button>
            </form>

            <p className="mt-6 text-xs text-gray-400 text-center">
              We'll only use your email to send your meal plan. Your information is never shared.
            </p>
          </motion.div>
        </div>
      </div>
    );
  }

  // =========================================================================
  // Phase: Review Screen
  // =========================================================================
  if (phase === 'review' && calorieBreakdown) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 py-8 px-4">
        <div className="max-w-4xl mx-auto">
          <motion.div
            variants={phaseVariants}
            initial="initial"
            animate="animate"
          >
            <ReviewScreen
              quizData={getValues() as unknown as CompleteQuizData}
              calorieTarget={calorieTarget}
              calorieBreakdown={calorieBreakdown}
              quizId={quizId}
              onEdit={handleEdit}
              onProceedToPayment={handleProceedFromReview}
              isSubmitting={false}
              submissionError={submissionError}
            />
          </motion.div>
        </div>
      </div>
    );
  }

  // =========================================================================
  // Phase: Email Verification
  // =========================================================================
  if (phase === 'email_verify') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 py-8 px-4">
        <div className="max-w-lg mx-auto">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Verify Your Email
            </h1>
            <p className="text-gray-600">
              One last step before we generate your personalized meal plan
            </p>
          </div>
          <motion.div
            variants={phaseVariants}
            initial="initial"
            animate="animate"
          >
            <EmailVerification
              email={email}
              onVerified={handleEmailVerified}
              onCancel={() => setPhase('review')}
            />
          </motion.div>
        </div>
      </div>
    );
  }

  // =========================================================================
  // Phase: Processing (AI generating meal plan)
  // =========================================================================
  if (phase === 'processing') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 py-8 px-4">
        <div className="max-w-lg mx-auto">
          <motion.div
            variants={phaseVariants}
            initial="initial"
            animate="animate"
            className="bg-white rounded-2xl shadow-xl p-8 text-center"
          >
            <div className="mb-6">
              <div className="w-20 h-20 mx-auto mb-4 relative">
                <svg className="animate-spin w-20 h-20 text-green-600" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-3">
                Creating Your Meal Plan
              </h2>
              <p className="text-gray-600 mb-6">
                Our AI is crafting your personalized 30-day keto meal plan with shopping lists and macro breakdowns.
              </p>

              <div className="space-y-3 text-left max-w-sm mx-auto">
                <div className="flex items-center space-x-3">
                  <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <svg className="w-4 h-4 text-green-600 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span className="text-sm text-gray-700">Analyzing your food preferences...</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <svg className="w-4 h-4 text-green-600 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span className="text-sm text-gray-700">Generating 30 days of meals ({calorieTarget} cal/day)...</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <svg className="w-4 h-4 text-green-600 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span className="text-sm text-gray-700">Building PDF with shopping lists & macros...</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <svg className="w-4 h-4 text-green-600 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <span className="text-sm text-gray-700">Sending to {email}...</span>
                </div>
              </div>
            </div>

            <p className="text-xs text-gray-400">
              This may take up to 60 seconds. Please don't close this page.
            </p>
          </motion.div>
        </div>
      </div>
    );
  }

  // =========================================================================
  // Phase: Success
  // =========================================================================
  if (phase === 'success') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 py-8 px-4">
        <div className="max-w-lg mx-auto">
          <motion.div
            variants={phaseVariants}
            initial="initial"
            animate="animate"
            className="bg-white rounded-2xl shadow-xl p-8 text-center"
          >
            <div className="w-20 h-20 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            </div>

            <h2 className="text-3xl font-bold text-gray-900 mb-3">
              Your Meal Plan is On Its Way!
            </h2>
            <p className="text-lg text-gray-600 mb-6">
              We're generating your personalized 30-day keto meal plan and sending it to:
            </p>
            <p className="text-xl font-semibold text-green-600 mb-6">
              {email}
            </p>

            <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6 text-left">
              <h3 className="font-semibold text-green-800 mb-2">What's included:</h3>
              <ul className="text-sm text-green-700 space-y-1">
                <li>- 30 days of personalized keto meals ({calorieTarget} cal/day)</li>
                <li>- 3 meals per day with full recipes</li>
                <li>- 4 weekly shopping lists organized by category</li>
                <li>- Daily macro breakdowns (protein, fat, carbs)</li>
                <li>- All meals under 30g net carbs</li>
              </ul>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
              <p className="text-sm text-blue-800">
                <strong>Note:</strong> The AI generation and PDF creation may take 1-2 minutes. Check your inbox (and spam folder) shortly.
              </p>
            </div>

            <button
              type="button"
              onClick={() => {
                setPhase('quiz');
                setEmail('');
                setQuizId('');
                setCalorieTarget(0);
                setCalorieBreakdown(null);
              }}
              className="text-sm text-gray-500 hover:text-gray-700 font-medium transition-colors"
            >
              Start a New Quiz
            </button>
          </motion.div>
        </div>
      </div>
    );
  }

  // =========================================================================
  // Phase: Error
  // =========================================================================
  if (phase === 'error') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 py-8 px-4">
        <div className="max-w-lg mx-auto">
          <motion.div
            variants={phaseVariants}
            initial="initial"
            animate="animate"
            className="bg-white rounded-2xl shadow-xl p-8 text-center"
          >
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-10 h-10 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>

            <h2 className="text-2xl font-bold text-gray-900 mb-3">
              Something Went Wrong
            </h2>
            <p className="text-gray-600 mb-4">
              {deliveryError || 'We encountered an error while generating your meal plan.'}
            </p>

            <div className="space-y-3">
              <button
                type="button"
                onClick={() => handleEmailVerified()}
                className="w-full py-3 px-4 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition-colors"
              >
                Try Again
              </button>
              <button
                type="button"
                onClick={() => setPhase('review')}
                className="w-full text-sm text-gray-500 hover:text-gray-700 font-medium transition-colors"
              >
                Go Back to Review
              </button>
            </div>
          </motion.div>
        </div>
      </div>
    );
  }

  // =========================================================================
  // Phase: Quiz (Steps 1-20) - Default
  // =========================================================================
  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2">
            Your Personalized Keto Journey
          </h1>
          <p className="text-gray-600">
            Answer a few questions to get your custom 30-day meal plan
          </p>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <StepProgress currentStep={currentStep} totalSteps={totalSteps} />
        </div>

        {/* Quiz Content Card */}
        <div className="bg-white rounded-2xl shadow-xl p-6 md:p-8 overflow-hidden">
          {/* Step Content with Framer Motion Animations */}
          <div className="min-h-[400px] relative">
            <AnimatePresence mode="wait" custom={direction}>
              <motion.div
                key={currentStep}
                custom={direction}
                variants={stepVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={stepTransition}
                className="w-full"
              >
                {renderStep()}
              </motion.div>
            </AnimatePresence>
          </div>

          {/* Navigation Buttons with animated transitions */}
          <div className="flex justify-between items-center mt-8 pt-6 border-t border-gray-200">
            <motion.button
              type="button"
              onClick={handlePrevious}
              disabled={!canGoBack}
              whileHover={canGoBack ? { scale: 1.02 } : {}}
              whileTap={canGoBack ? { scale: 0.98 } : {}}
              className={`px-6 py-3 rounded-lg font-medium transition-colors duration-200 ${
                !canGoBack
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
              aria-label="Go to previous step"
            >
              &larr; Back
            </motion.button>

            <motion.div
              className="text-sm text-gray-500"
              key={currentStep}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              Step {currentStep} of {totalSteps}
            </motion.div>

            <motion.button
              type="button"
              onClick={handleNext}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="px-6 py-3 rounded-lg font-medium transition-colors duration-200 bg-green-600 text-white hover:bg-green-700 shadow-md hover:shadow-lg"
              aria-label={isLastStep ? 'Review your answers' : 'Go to next step'}
            >
              {isLastStep ? 'Get My Meal Plan &rarr;' : 'Next &rarr;'}
            </motion.button>
          </div>
        </div>

        {/* Privacy Notice Footer */}
        <div className="mt-6 text-center text-sm text-gray-600">
          <div className="flex items-center justify-center space-x-2">
            <svg
              className="w-4 h-4 text-green-600"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
                clipRule="evenodd"
              />
            </svg>
            <span>Your data is encrypted and will be deleted after 24 hours</span>
          </div>
        </div>
      </div>

      {/* T112: SaveProgressModal - appears after Step 10 for unauthenticated users */}
      <SaveProgressModal
        isOpen={showSaveModal}
        onClose={handleContinueWithoutAccount}
        onCreateAccount={handleCreateAccount}
      />
    </div>
  );
}
