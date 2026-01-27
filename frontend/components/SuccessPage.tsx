'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';

/**
 * SuccessPage Component (T110)
 *
 * Displays a success confirmation after meal plan generation with:
 * - Animated checkmark icon
 * - Scale effect on download button
 * - Confetti-style decorative animations
 * - Smooth entrance transitions
 */

interface SuccessPageProps {
  /** Email address for delivery confirmation */
  email?: string;
  /** Calorie target from quiz */
  calorieTarget?: number;
  /** Download URL for the PDF */
  downloadUrl?: string;
  /** Callback when download button is clicked */
  onDownload?: () => void;
  /** Callback when "Create Account" is clicked */
  onCreateAccount?: () => void;
}

// Animation variants for staggered entrance
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
      delayChildren: 0.2,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: 'easeOut' as const },
  },
};

// Checkmark animation
const checkmarkVariants = {
  hidden: { pathLength: 0, opacity: 0 },
  visible: {
    pathLength: 1,
    opacity: 1,
    transition: {
      pathLength: { duration: 0.5, ease: 'easeInOut' as const },
      opacity: { duration: 0.2 },
    },
  },
};

// Download button scale animation
const downloadButtonVariants = {
  initial: { scale: 1 },
  hover: {
    scale: 1.05,
    boxShadow: '0 10px 40px -10px rgba(34, 197, 94, 0.5)',
    transition: { duration: 0.2, ease: 'easeOut' as const },
  },
  tap: {
    scale: 0.98,
    transition: { duration: 0.1 },
  },
  pulse: {
    scale: [1, 1.02, 1],
    transition: {
      duration: 2,
      repeat: Infinity,
      ease: 'easeInOut' as const,
    },
  },
};

// Confetti particle animation
const confettiVariants = {
  initial: (i: number) => ({
    opacity: 0,
    y: -20,
    x: 0,
    rotate: 0,
  }),
  animate: (i: number) => ({
    opacity: [0, 1, 1, 0],
    y: [0, -30, 100],
    x: [(i % 2 === 0 ? -1 : 1) * (i * 10), (i % 2 === 0 ? 1 : -1) * (i * 15)],
    rotate: [0, (i % 2 === 0 ? 1 : -1) * 360],
    transition: {
      duration: 2,
      delay: i * 0.1,
      ease: 'easeOut' as const,
    },
  }),
};

export function SuccessPage({
  email = 'user@example.com',
  calorieTarget = 2000,
  downloadUrl,
  onDownload,
  onCreateAccount,
}: SuccessPageProps) {
  const [hasDownloaded, setHasDownloaded] = useState(false);

  const handleDownload = () => {
    setHasDownloaded(true);
    onDownload?.();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 py-12 px-4 overflow-hidden">
      {/* Confetti particles */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        {[...Array(12)].map((_, i) => (
          <motion.div
            key={i}
            custom={i}
            variants={confettiVariants}
            initial="initial"
            animate="animate"
            className={`absolute w-3 h-3 rounded-full ${
              ['bg-green-400', 'bg-blue-400', 'bg-yellow-400', 'bg-pink-400'][
                i % 4
              ]
            }`}
            style={{
              left: `${10 + (i * 7)}%`,
              top: '20%',
            }}
          />
        ))}
      </div>

      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="max-w-lg mx-auto"
      >
        {/* Success Card */}
        <motion.div
          variants={itemVariants}
          className="bg-white rounded-2xl shadow-xl p-8 text-center relative"
        >
          {/* Animated checkmark circle */}
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{
              type: 'spring',
              stiffness: 200,
              damping: 15,
              delay: 0.1,
            }}
            className="w-24 h-24 mx-auto mb-6 bg-green-100 rounded-full flex items-center justify-center"
          >
            <svg
              className="w-12 h-12 text-green-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <motion.path
                variants={checkmarkVariants}
                initial="hidden"
                animate="visible"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={3}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </motion.div>

          {/* Success title */}
          <motion.h1
            variants={itemVariants}
            className="text-3xl font-bold text-gray-900 mb-2"
          >
            Your Meal Plan is Ready!
          </motion.h1>

          {/* Subtitle */}
          <motion.p variants={itemVariants} className="text-gray-600 mb-6">
            We&apos;ve sent your personalized 30-day keto meal plan to{' '}
            <span className="font-medium text-gray-900">{email}</span>
          </motion.p>

          {/* Calorie info badge */}
          <motion.div
            variants={itemVariants}
            className="inline-flex items-center gap-2 bg-green-50 text-green-700 px-4 py-2 rounded-full mb-8"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span className="font-medium">
              {calorieTarget.toLocaleString()} calories/day
            </span>
          </motion.div>

          {/* Download button with scale animation */}
          <motion.div variants={itemVariants}>
            <motion.button
              variants={downloadButtonVariants}
              initial="initial"
              whileHover="hover"
              whileTap="tap"
              animate={hasDownloaded ? 'initial' : 'pulse'}
              onClick={handleDownload}
              className="w-full bg-gradient-to-r from-green-500 to-green-600 text-white font-semibold py-4 px-8 rounded-xl shadow-lg hover:from-green-600 hover:to-green-700 transition-colors duration-200 flex items-center justify-center gap-3"
            >
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                />
              </svg>
              <span>Download Your Meal Plan</span>
            </motion.button>
          </motion.div>

          {/* Success indicator after download */}
          {hasDownloaded && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 text-green-600 text-sm flex items-center justify-center gap-2"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              <span>Download started!</span>
            </motion.div>
          )}

          {/* Divider */}
          <motion.div
            variants={itemVariants}
            className="my-8 border-t border-gray-200"
          />

          {/* What's included section */}
          <motion.div variants={itemVariants} className="text-left">
            <h3 className="font-semibold text-gray-900 mb-4">
              Your plan includes:
            </h3>
            <ul className="space-y-3">
              {[
                '30 days of keto-compliant meals',
                '90 delicious recipes (breakfast, lunch, dinner)',
                '4 weekly shopping lists',
                'Complete macro breakdown for each meal',
              ].map((item, index) => (
                <motion.li
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.8 + index * 0.1 }}
                  className="flex items-start gap-3 text-gray-600"
                >
                  <svg
                    className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span>{item}</span>
                </motion.li>
              ))}
            </ul>
          </motion.div>
        </motion.div>

        {/* Create Account Card (T099) */}
        <motion.div
          variants={itemVariants}
          className="mt-6 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl shadow-lg p-6 border border-blue-100"
        >
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
              <svg
                className="w-6 h-6 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-gray-900 mb-2">
                Want permanent access?
              </h3>
              <p className="text-sm text-gray-600 mb-4">
                Create a free account to access your meal plan anytime without needing magic links.
              </p>

              {/* Benefits list */}
              <ul className="space-y-2 mb-4">
                {[
                  'Access your plan anytime, anywhere',
                  'No magic links needed - just login',
                  'Save your progress and preferences',
                  'Get future updates and new features',
                ].map((benefit, index) => (
                  <motion.li
                    key={index}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 1.2 + index * 0.1 }}
                    className="flex items-start gap-2 text-sm text-gray-700"
                  >
                    <svg
                      className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    <span>{benefit}</span>
                  </motion.li>
                ))}
              </ul>

              {/* Action buttons */}
              <div className="flex gap-3">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={onCreateAccount}
                  className="flex-1 bg-blue-600 text-white font-semibold py-3 px-4 rounded-lg hover:bg-blue-700 transition-colors shadow-md"
                >
                  Create Account
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="px-4 py-3 text-gray-600 font-medium text-sm hover:text-gray-800 transition-colors"
                >
                  Skip for now
                </motion.button>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Footer note */}
        <motion.p
          variants={itemVariants}
          className="mt-6 text-center text-sm text-gray-500"
        >
          Your PDF will be available for download for 90 days.
          <br />
          Check your spam folder if you don&apos;t see the email.
        </motion.p>
      </motion.div>
    </div>
  );
}
