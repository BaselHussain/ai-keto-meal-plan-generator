'use client';

import { useState, ReactNode } from 'react';
import { StepProgress } from './StepProgress';

interface QuizContainerProps {
  children?: ReactNode;
}

export function QuizContainer({ children }: QuizContainerProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const totalSteps = 20;

  const handleNext = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
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
          {/* Step Content - Will be replaced with actual step components via state management */}
          <div className="min-h-[400px]">
            {children || (
              <div className="text-center text-gray-500">
                Quiz step {currentStep} will render here
              </div>
            )}
          </div>

          {/* Navigation Buttons */}
          <div className="flex justify-between items-center mt-8 pt-6 border-t border-gray-200">
            <button
              type="button"
              onClick={handleBack}
              disabled={currentStep === 1}
              className={`px-6 py-3 rounded-lg font-medium transition-all duration-200 ${
                currentStep === 1
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
              onClick={handleNext}
              disabled={currentStep === totalSteps}
              className={`px-6 py-3 rounded-lg font-medium transition-all duration-200 ${
                currentStep === totalSteps
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-green-600 text-white hover:bg-green-700 shadow-md hover:shadow-lg'
              }`}
              aria-label="Go to next step"
            >
              {currentStep === totalSteps ? 'Review' : 'Next →'}
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
