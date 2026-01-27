'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * LoadingScreen Component (T109)
 *
 * Displays an animated loading screen with multi-step progress messages
 * that animate sequentially while the meal plan is being generated.
 *
 * Features:
 * - Smooth spinner animation
 * - Sequential progress messages with fade transitions
 * - Progress bar visualization
 * - Estimated time remaining
 */

interface LoadingScreenProps {
  /** Current step in the loading process (0-based) */
  currentStep?: number;
  /** Total number of steps */
  totalSteps?: number;
  /** Custom loading messages (optional) */
  messages?: string[];
  /** Whether to auto-advance through messages */
  autoAdvance?: boolean;
  /** Interval between auto-advance steps (ms) */
  advanceInterval?: number;
}

// Default loading messages for meal plan generation
const DEFAULT_MESSAGES = [
  'Analyzing your preferences...',
  'Calculating your nutritional needs...',
  'Generating keto-compliant recipes...',
  'Building your 30-day meal plan...',
  'Creating weekly shopping lists...',
  'Finalizing your personalized plan...',
  'Almost ready...',
];

// Animation variants
const messageVariants = {
  enter: {
    opacity: 0,
    y: 20,
  },
  center: {
    opacity: 1,
    y: 0,
  },
  exit: {
    opacity: 0,
    y: -20,
  },
};

const spinnerVariants = {
  animate: {
    rotate: 360,
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: 'linear' as const,
    },
  },
};

const pulseVariants = {
  animate: {
    scale: [1, 1.05, 1],
    opacity: [0.7, 1, 0.7],
    transition: {
      duration: 2,
      repeat: Infinity,
      ease: 'easeInOut' as const,
    },
  },
};

export function LoadingScreen({
  currentStep: controlledStep,
  totalSteps: controlledTotal,
  messages = DEFAULT_MESSAGES,
  autoAdvance = true,
  advanceInterval = 3000,
}: LoadingScreenProps) {
  const [internalStep, setInternalStep] = useState(0);

  // Use controlled step if provided, otherwise use internal state
  const currentStep = controlledStep ?? internalStep;
  const totalSteps = controlledTotal ?? messages.length;

  // Calculate progress percentage
  const progress = Math.min(((currentStep + 1) / totalSteps) * 100, 100);

  // Auto-advance through messages
  useEffect(() => {
    if (!autoAdvance || controlledStep !== undefined) return;

    const interval = setInterval(() => {
      setInternalStep((prev) => {
        if (prev < messages.length - 1) {
          return prev + 1;
        }
        return prev;
      });
    }, advanceInterval);

    return () => clearInterval(interval);
  }, [autoAdvance, controlledStep, messages.length, advanceInterval]);

  return (
    <div className="fixed inset-0 bg-gradient-to-br from-green-50 to-blue-50 flex items-center justify-center z-50">
      <div className="max-w-md w-full mx-4">
        {/* Main loading card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4 }}
          className="bg-white rounded-2xl shadow-xl p-8 text-center"
        >
          {/* Animated spinner */}
          <div className="relative w-24 h-24 mx-auto mb-8">
            {/* Outer pulse ring */}
            <motion.div
              variants={pulseVariants}
              animate="animate"
              className="absolute inset-0 rounded-full bg-green-100"
            />

            {/* Spinning ring */}
            <motion.div
              variants={spinnerVariants}
              animate="animate"
              className="absolute inset-2 rounded-full border-4 border-green-200 border-t-green-600"
            />

            {/* Center icon */}
            <div className="absolute inset-0 flex items-center justify-center">
              <motion.svg
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
                className="w-10 h-10 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                />
              </motion.svg>
            </div>
          </div>

          {/* Title */}
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Creating Your Meal Plan
          </h2>

          {/* Animated message */}
          <div className="h-8 mb-6">
            <AnimatePresence mode="wait">
              <motion.p
                key={currentStep}
                variants={messageVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.3 }}
                className="text-gray-600"
              >
                {messages[Math.min(currentStep, messages.length - 1)]}
              </motion.p>
            </AnimatePresence>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-gray-200 rounded-full h-2 mb-4 overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-green-500 to-green-600 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
            />
          </div>

          {/* Step indicator */}
          <div className="flex justify-between text-sm text-gray-500">
            <span>Step {currentStep + 1} of {totalSteps}</span>
            <span>{Math.round(progress)}% complete</span>
          </div>

          {/* Estimated time */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-6 text-sm text-gray-400"
          >
            This usually takes less than 90 seconds
          </motion.p>
        </motion.div>

        {/* Floating decorative elements */}
        <motion.div
          animate={{
            y: [0, -10, 0],
            rotate: [0, 5, 0],
          }}
          transition={{
            duration: 4,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
          className="absolute top-20 left-10 w-16 h-16 bg-green-100 rounded-full opacity-50 blur-xl"
        />
        <motion.div
          animate={{
            y: [0, 10, 0],
            rotate: [0, -5, 0],
          }}
          transition={{
            duration: 5,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: 1,
          }}
          className="absolute bottom-20 right-10 w-20 h-20 bg-blue-100 rounded-full opacity-50 blur-xl"
        />
      </div>
    </div>
  );
}

// Export step messages for use in other components
export const LOADING_MESSAGES = DEFAULT_MESSAGES;
