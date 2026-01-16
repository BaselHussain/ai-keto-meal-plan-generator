'use client';

import { StepProgress } from './StepProgress';
import { Step01Gender } from './steps/Step01Gender';
import { Step02Activity } from './steps/Step02Activity';
import { Step17Restrictions } from './steps/Step17Restrictions';
import { Step20Biometrics } from './steps/Step20Biometrics';
import { useQuizState } from '../../hooks/useQuizState';

export function QuizContainer() {
  const {
    form,
    currentStep,
    totalSteps,
    nextStep,
    previousStep,
    canGoBack,
    isLastStep,
  } = useQuizState();

  const { setValue, watch } = form;

  // Render the current step component
  const renderStep = () => {
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
      case 20:
        return (
          <Step20Biometrics
            value={watch('step_20')}
            onChange={(value) => setValue('step_20', value)}
          />
        );
      default:
        // Placeholder for steps 3-16, 18-19 (food selection steps not yet implemented)
        return (
          <div className="text-center py-12">
            <div className="text-xl font-semibold text-gray-700 mb-4">
              Step {currentStep}: Food Selection
            </div>
            <p className="text-gray-600 mb-8">
              This step will be implemented in Phase 6. For now, you can navigate through the quiz structure.
            </p>
            <div className="text-sm text-gray-500">
              Available steps to test: 1, 2, 17, 20
            </div>
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
        <div className="bg-white rounded-2xl shadow-xl p-6 md:p-8">
          {/* Step Content */}
          <div className="min-h-[400px]">
            {renderStep()}
          </div>

          {/* Navigation Buttons */}
          <div className="flex justify-between items-center mt-8 pt-6 border-t border-gray-200">
            <button
              type="button"
              onClick={previousStep}
              disabled={!canGoBack}
              className={`px-6 py-3 rounded-lg font-medium transition-all duration-200 ${
                !canGoBack
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
              aria-label="Go to previous step"
            >
              ← Back
            </button>

            <div className="text-sm text-gray-500">
              Step {currentStep} of {totalSteps}
            </div>

            <button
              type="button"
              onClick={nextStep}
              disabled={isLastStep}
              className={`px-6 py-3 rounded-lg font-medium transition-all duration-200 ${
                isLastStep
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-green-600 text-white hover:bg-green-700 shadow-md hover:shadow-lg'
              }`}
              aria-label="Go to next step"
            >
              {isLastStep ? 'Review' : 'Next →'}
            </button>
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
    </div>
  );
}
