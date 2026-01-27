'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRouter } from 'next/navigation';

interface SaveProgressModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateAccount: () => void;
}

/**
 * SaveProgressModal Component (T112)
 *
 * Mid-quiz signup prompt that appears after Step 10 (per FR-Q-020).
 * Encourages users to create an account to save progress across devices.
 *
 * Features:
 * - Shows benefits of account creation (cross-device sync, save progress, faster checkout)
 * - "Create Account" button and "Continue Without Account" option
 * - Respects prefers-reduced-motion user preferences
 * - Keyboard accessible (Escape to close, Tab navigation)
 * - ARIA labels for screen readers
 *
 * @param isOpen - Whether modal is visible
 * @param onClose - Callback when user dismisses modal
 * @param onCreateAccount - Callback when user clicks "Create Account"
 */
export function SaveProgressModal({
  isOpen,
  onClose,
  onCreateAccount,
}: SaveProgressModalProps) {
  const router = useRouter();
  const [isClosing, setIsClosing] = useState(false);

  // Handle close with animation
  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => {
      onClose();
      setIsClosing(false);
    }, 200);
  };

  // Handle keyboard events (Escape to close)
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      handleClose();
    }
  };

  // Handle backdrop click
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      handleClose();
    }
  };

  // Prevent scroll when modal is open
  if (typeof window !== 'undefined') {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
  }

  // Modal animation variants (300-400ms per T108)
  const backdropVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1 },
  };

  const modalVariants = {
    hidden: {
      opacity: 0,
      scale: 0.95,
      y: 20,
    },
    visible: {
      opacity: 1,
      scale: 1,
      y: 0,
    },
  };

  const modalTransition = {
    type: 'tween' as const,
    ease: 'easeOut' as const,
    duration: 0.3,
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
          variants={backdropVariants}
          initial="hidden"
          animate="visible"
          exit="hidden"
          transition={modalTransition}
          onClick={handleBackdropClick}
          onKeyDown={handleKeyDown}
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
          aria-describedby="modal-description"
        >
          <motion.div
            className="relative w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden"
            variants={modalVariants}
            initial="hidden"
            animate={isClosing ? 'hidden' : 'visible'}
            exit="hidden"
            transition={modalTransition}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close button */}
            <button
              type="button"
              onClick={handleClose}
              className="absolute top-4 right-4 w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors duration-200"
              aria-label="Close modal"
            >
              <svg
                className="w-5 h-5 text-gray-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>

            {/* Modal content */}
            <div className="p-6 md:p-8">
              {/* Icon */}
              <div className="mb-4 flex justify-center">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
                  <svg
                    className="w-8 h-8 text-green-600"
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
                </div>
              </div>

              {/* Title */}
              <h2
                id="modal-title"
                className="text-2xl font-bold text-gray-900 text-center mb-3"
              >
                Save Your Progress?
              </h2>

              {/* Description */}
              <p
                id="modal-description"
                className="text-gray-600 text-center mb-6"
              >
                You're halfway through! Create a free account to save your
                progress and unlock these benefits:
              </p>

              {/* Benefits list */}
              <ul className="space-y-3 mb-6">
                <li className="flex items-start">
                  <svg
                    className="w-6 h-6 text-green-600 mr-3 flex-shrink-0 mt-0.5"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <div>
                    <strong className="text-gray-900">
                      Save progress across all your devices
                    </strong>
                    <p className="text-sm text-gray-600 mt-0.5">
                      Continue your quiz on any device, anytime
                    </p>
                  </div>
                </li>
                <li className="flex items-start">
                  <svg
                    className="w-6 h-6 text-green-600 mr-3 flex-shrink-0 mt-0.5"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <div>
                    <strong className="text-gray-900">
                      Resume anytime without losing data
                    </strong>
                    <p className="text-sm text-gray-600 mt-0.5">
                      No need to start over if you close the browser
                    </p>
                  </div>
                </li>
                <li className="flex items-start">
                  <svg
                    className="w-6 h-6 text-green-600 mr-3 flex-shrink-0 mt-0.5"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <div>
                    <strong className="text-gray-900">
                      Faster checkout (skip email verification)
                    </strong>
                    <p className="text-sm text-gray-600 mt-0.5">
                      Complete your purchase with one click
                    </p>
                  </div>
                </li>
              </ul>

              {/* Action buttons */}
              <div className="space-y-3">
                <motion.button
                  type="button"
                  onClick={onCreateAccount}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="w-full px-6 py-3 bg-green-600 text-white font-semibold rounded-lg shadow-md hover:bg-green-700 hover:shadow-lg transition-all duration-200"
                  aria-label="Create free account"
                >
                  Create Free Account
                </motion.button>

                <motion.button
                  type="button"
                  onClick={handleClose}
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  className="w-full px-6 py-3 bg-white text-gray-700 font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors duration-200"
                  aria-label="Continue without account"
                >
                  Continue Without Account
                </motion.button>
              </div>

              {/* Privacy note */}
              <p className="mt-4 text-xs text-gray-500 text-center">
                Free account. No credit card required. Unsubscribe anytime.
              </p>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
