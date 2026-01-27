'use client';

import { motion } from 'framer-motion';

interface DeviceWarningProps {
  isAuthenticated: boolean;
}

/**
 * DeviceWarning Component (T115)
 *
 * Displays a warning message on quiz start page for unauthenticated users.
 * Informs users that quiz progress is saved only on their current device,
 * and they can create an account during the quiz to enable cross-device sync.
 *
 * Features:
 * - Only shows for unauthenticated users
 * - Clear messaging about device-specific storage
 * - Mentions mid-quiz account creation option
 * - Responsive design (mobile-first)
 * - ARIA labels for accessibility
 *
 * @param isAuthenticated - Whether user is logged in (hides warning if true)
 */
export function DeviceWarning({ isAuthenticated }: DeviceWarningProps) {
  // Don't show warning for authenticated users
  if (isAuthenticated) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg"
      role="alert"
      aria-live="polite"
    >
      <div className="flex items-start">
        {/* Warning icon */}
        <div className="flex-shrink-0">
          <svg
            className="w-5 h-5 text-amber-600 mt-0.5"
            fill="currentColor"
            viewBox="0 0 20 20"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
        </div>

        {/* Warning content */}
        <div className="ml-3 flex-1">
          <h3 className="text-sm font-semibold text-amber-800">
            Device-Only Storage
          </h3>
          <p className="mt-1 text-sm text-amber-700 leading-relaxed">
            Your quiz progress is saved only on this device. To save progress
            across all your devices,{' '}
            <strong>create a free account during the quiz</strong> (we'll
            prompt you after Step 10).
          </p>
        </div>
      </div>
    </motion.div>
  );
}
