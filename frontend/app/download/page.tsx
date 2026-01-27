'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  verifyMagicLink,
  RecoveryServiceError,
  VerifyMagicLinkResponse,
} from '@/services/recoveryService';

/**
 * Download Page Component (T097)
 *
 * Displays meal plan details and download button after magic link verification.
 *
 * Route: /download?token=<magic_link_token>
 *
 * Flow:
 * 1. On page load, verify token via GET /api/v1/recovery/verify
 * 2. Show loading state while verifying
 * 3. If valid: display meal plan details and download button
 * 4. If invalid: show appropriate error (expired, used, not found)
 *
 * Features:
 * - Token verification on mount
 * - Loading state with animations
 * - Success state with meal plan details
 * - Error states for expired/used/invalid tokens
 * - Download button with scale animation
 * - Mobile-first responsive design
 *
 * Reference:
 *   Phase 7.3 - PDF download page (T097)
 *   specs/001-keto-meal-plan-generator/contracts/recovery-api.yaml
 */

// Animation variants
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
    transition: { duration: 0.5, ease: 'easeOut' },
  },
};

const checkmarkVariants = {
  hidden: { pathLength: 0, opacity: 0 },
  visible: {
    pathLength: 1,
    opacity: 1,
    transition: {
      pathLength: { duration: 0.5, ease: 'easeInOut' },
      opacity: { duration: 0.2 },
    },
  },
};

const downloadButtonVariants = {
  initial: { scale: 1 },
  hover: {
    scale: 1.05,
    boxShadow: '0 10px 40px -10px rgba(34, 197, 94, 0.5)',
    transition: { duration: 0.2, ease: 'easeOut' },
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
      ease: 'easeInOut',
    },
  },
};

// Loading spinner animation
const spinnerVariants = {
  animate: {
    rotate: 360,
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: 'linear',
    },
  },
};

type PageState = 'loading' | 'success' | 'error';

interface ErrorDetails {
  code: string;
  message: string;
  title: string;
}

function DownloadPageContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token');

  const [pageState, setPageState] = useState<PageState>('loading');
  const [mealPlan, setMealPlan] = useState<VerifyMagicLinkResponse | null>(null);
  const [error, setError] = useState<ErrorDetails | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);

  // Verify token on mount
  useEffect(() => {
    if (!token) {
      setPageState('error');
      setError({
        code: 'MISSING_TOKEN',
        title: 'Invalid Link',
        message: 'This link is missing required information. Please use the link from your email.',
      });
      return;
    }

    async function verify() {
      try {
        const result = await verifyMagicLink(token!);
        setMealPlan(result);
        setPageState('success');
      } catch (err) {
        setPageState('error');

        if (err instanceof RecoveryServiceError) {
          // Map error codes to user-friendly messages
          switch (err.code) {
            case 'TOKEN_EXPIRED':
              setError({
                code: err.code,
                title: 'Link Expired',
                message: 'This magic link has expired. Magic links are valid for 24 hours.',
              });
              break;
            case 'TOKEN_ALREADY_USED':
              setError({
                code: err.code,
                title: 'Link Already Used',
                message: 'This magic link has already been used. Each link can only be used once for security.',
              });
              break;
            case 'TOKEN_INVALID':
              setError({
                code: err.code,
                title: 'Invalid Link',
                message: 'This magic link is invalid. Please request a new one.',
              });
              break;
            case 'NO_MEAL_PLANS':
              setError({
                code: err.code,
                title: 'No Meal Plans Found',
                message: 'No meal plans were found for this account. Please complete the quiz to generate your plan.',
              });
              break;
            case 'network_error':
              setError({
                code: err.code,
                title: 'Connection Error',
                message: 'Unable to connect to the server. Please check your internet connection and try again.',
              });
              break;
            default:
              setError({
                code: err.code || 'unknown_error',
                title: 'Verification Failed',
                message: err.message || 'Failed to verify magic link. Please try again or request a new link.',
              });
          }
        } else {
          setError({
            code: 'unknown_error',
            title: 'Unexpected Error',
            message: 'An unexpected error occurred. Please try again or request a new magic link.',
          });
        }
      }
    }

    verify();
  }, [token]);

  // Handle download button click
  const handleDownload = async () => {
    if (!token || !mealPlan) return;

    setIsDownloading(true);

    try {
      // Download PDF via GET /api/v1/download-pdf?token=
      const response = await fetch(`/api/v1/download-pdf?token=${encodeURIComponent(token)}`, {
        method: 'GET',
      });

      if (!response.ok) {
        throw new Error(`Download failed: ${response.statusText}`);
      }

      // Get PDF blob
      const blob = await response.blob();

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `keto-meal-plan-${mealPlan.meal_plan_id.substring(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();

      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Download failed:', err);
      alert('Failed to download PDF. Please try again or contact support.');
    } finally {
      setIsDownloading(false);
    }
  };

  // Format date for display
  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    } catch {
      return dateString;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 py-12 px-4">
      <div className="max-w-lg mx-auto">
        <AnimatePresence mode="wait">
          {/* Loading State */}
          {pageState === 'loading' && (
            <motion.div
              key="loading"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              className="bg-white rounded-2xl shadow-xl p-8 text-center"
            >
              {/* Animated spinner */}
              <div className="relative w-24 h-24 mx-auto mb-6">
                <motion.div
                  variants={spinnerVariants}
                  animate="animate"
                  className="absolute inset-2 rounded-full border-4 border-green-200 border-t-green-600"
                />
              </div>

              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Verifying Link
              </h2>
              <p className="text-gray-600">
                Please wait while we verify your magic link...
              </p>
            </motion.div>
          )}

          {/* Success State */}
          {pageState === 'success' && mealPlan && (
            <motion.div
              key="success"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white rounded-2xl shadow-xl p-8 text-center"
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
                Your Meal Plan is Ready
              </motion.h1>

              {/* Email info */}
              <motion.p variants={itemVariants} className="text-gray-600 mb-6">
                Plan for{' '}
                <span className="font-medium text-gray-900">{mealPlan.email}</span>
              </motion.p>

              {/* Meal plan details */}
              <motion.div
                variants={itemVariants}
                className="bg-gray-50 rounded-lg p-4 mb-6 text-left"
              >
                <h3 className="font-semibold text-gray-900 mb-3 text-center">
                  Plan Details
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Created:</span>
                    <span className="font-medium text-gray-900">
                      {formatDate(mealPlan.created_at)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Plan ID:</span>
                    <span className="font-mono text-xs text-gray-700">
                      {mealPlan.meal_plan_id.substring(0, 8)}...
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">PDF Status:</span>
                    <span className={`font-medium ${mealPlan.pdf_available ? 'text-green-600' : 'text-red-600'}`}>
                      {mealPlan.pdf_available ? 'Available' : 'Not Available'}
                    </span>
                  </div>
                </div>
              </motion.div>

              {/* Download button */}
              {mealPlan.pdf_available ? (
                <motion.div variants={itemVariants}>
                  <motion.button
                    variants={downloadButtonVariants}
                    initial="initial"
                    whileHover="hover"
                    whileTap="tap"
                    animate={isDownloading ? 'initial' : 'pulse'}
                    onClick={handleDownload}
                    disabled={isDownloading}
                    className="w-full bg-gradient-to-r from-green-500 to-green-600 text-white font-semibold py-4 px-8 rounded-xl shadow-lg hover:from-green-600 hover:to-green-700 transition-colors duration-200 flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isDownloading ? (
                      <>
                        <svg
                          className="animate-spin h-6 w-6"
                          xmlns="http://www.w3.org/2000/svg"
                          fill="none"
                          viewBox="0 0 24 24"
                        >
                          <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                          ></circle>
                          <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                          ></path>
                        </svg>
                        <span>Downloading...</span>
                      </>
                    ) : (
                      <>
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
                      </>
                    )}
                  </motion.button>
                </motion.div>
              ) : (
                <motion.div
                  variants={itemVariants}
                  className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-sm text-yellow-800"
                >
                  <p className="font-medium">PDF Not Available</p>
                  <p className="mt-1">
                    Your meal plan is still being generated. Please check back shortly or check your email.
                  </p>
                </motion.div>
              )}

              {/* Divider */}
              <motion.div
                variants={itemVariants}
                className="my-6 border-t border-gray-200"
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
                      transition={{ delay: 0.6 + index * 0.1 }}
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
          )}

          {/* Error State */}
          {pageState === 'error' && error && (
            <motion.div
              key="error"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              className="bg-white rounded-2xl shadow-xl p-8 text-center"
            >
              {/* Error icon */}
              <div className="w-24 h-24 mx-auto mb-6 bg-red-100 rounded-full flex items-center justify-center">
                <svg
                  className="w-12 h-12 text-red-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>

              {/* Error title */}
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                {error.title}
              </h1>

              {/* Error message */}
              <p className="text-gray-600 mb-6">{error.message}</p>

              {/* Action buttons */}
              <div className="space-y-3">
                {(error.code === 'TOKEN_EXPIRED' || error.code === 'TOKEN_ALREADY_USED' || error.code === 'TOKEN_INVALID') && (
                  <a
                    href="/recover-plan"
                    className="block w-full bg-green-600 text-white font-semibold py-3 px-6 rounded-lg hover:bg-green-700 transition-colors"
                  >
                    Request New Magic Link
                  </a>
                )}

                {error.code === 'NO_MEAL_PLANS' && (
                  <a
                    href="/"
                    className="block w-full bg-green-600 text-white font-semibold py-3 px-6 rounded-lg hover:bg-green-700 transition-colors"
                  >
                    Start Quiz
                  </a>
                )}

                <a
                  href="/"
                  className="block w-full border border-gray-300 text-gray-700 font-medium py-3 px-6 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Go to Home
                </a>
              </div>

              {/* Help text */}
              <p className="mt-6 text-sm text-gray-500">
                Need help?{' '}
                <a
                  href="mailto:support@example.com"
                  className="text-green-600 hover:text-green-700 font-medium"
                >
                  Contact Support
                </a>
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Footer info */}
        {pageState === 'success' && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
            className="mt-6 text-center text-sm text-gray-500"
          >
            Your PDF is available for download for 90 days.
            <br />
            This link can only be used once for security.
          </motion.p>
        )}
      </div>
    </div>
  );
}

// Wrap content in Suspense to handle useSearchParams
export default function DownloadPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 flex items-center justify-center">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-green-200 border-t-green-600 mb-4"></div>
            <p className="text-gray-600">Loading...</p>
          </div>
        </div>
      }
    >
      <DownloadPageContent />
    </Suspense>
  );
}
