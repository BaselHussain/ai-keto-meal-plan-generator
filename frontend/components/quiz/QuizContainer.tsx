'use client';

import { useState, useEffect } from 'react';
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
import { useQuizState } from '../../hooks/useQuizState';
import { getFoodCategoryByStep } from '../../lib/foodCategories';
import { saveQuizProgress, loadQuizProgress } from '../../services/quizService';
import { isAuthenticated as checkAuth } from '../../services/authService';

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
      // Don't block navigation on save failure
    }
  };

  // Wrapped navigation handlers to set direction
  const handleNext = async () => {
    // Save progress before navigating (for authenticated users)
    await saveProgressIfAuthenticated();

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
    // Redirect to create account page with return URL
    router.push('/create-account?return=/quiz');
  };

  // Handle "Continue Without Account" from SaveProgressModal
  const handleContinueWithoutAccount = () => {
    setShowSaveModal(false);
  };

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
              ← Back
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
              disabled={isLastStep}
              whileHover={!isLastStep ? { scale: 1.02 } : {}}
              whileTap={!isLastStep ? { scale: 0.98 } : {}}
              className={`px-6 py-3 rounded-lg font-medium transition-colors duration-200 ${
                isLastStep
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-green-600 text-white hover:bg-green-700 shadow-md hover:shadow-lg'
              }`}
              aria-label="Go to next step"
            >
              {isLastStep ? 'Review' : 'Next →'}
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
