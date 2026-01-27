'use client';

import { useState } from 'react';
import { requestMagicLink, RecoveryServiceError } from '@/services/recoveryService';

/**
 * Recover Plan Page (T092)
 *
 * Allows users to request a magic link for passwordless plan recovery.
 * Implements:
 * - Email input form with validation
 * - Submit button to request magic link
 * - Success/error messaging
 * - Mobile-first responsive design
 * - Loading states
 *
 * Rate Limits:
 * - 3 requests per email per 24 hours
 * - 5 requests per IP per hour
 *
 * Reference:
 *   Phase 7.1 - Magic link generation (T090-T093)
 *   specs/001-keto-meal-plan-generator/contracts/recovery-api.yaml
 */
export default function RecoverPlanPage() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);

  /**
   * Validate email format (client-side)
   */
  const validateEmail = (email: string): boolean => {
    // Basic email regex (same as HTML5 email input)
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  /**
   * Handle form submission
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Reset messages
    setSuccessMessage(null);
    setErrorMessage(null);
    setEmailError(null);

    // Validate email
    if (!email.trim()) {
      setEmailError('Email address is required');
      return;
    }

    if (!validateEmail(email)) {
      setEmailError('Please enter a valid email address');
      return;
    }

    setIsLoading(true);

    try {
      const response = await requestMagicLink(email);
      setSuccessMessage(response.message);
      setEmail(''); // Clear input on success
    } catch (error) {
      if (error instanceof RecoveryServiceError) {
        // Handle specific error codes
        if (error.code === 'RATE_LIMITED') {
          setErrorMessage(
            error.message ||
            'Too many requests. Please try again later.'
          );
        } else if (error.code === 'network_error') {
          setErrorMessage(
            'Network error. Please check your internet connection and try again.'
          );
        } else {
          setErrorMessage(
            error.message ||
            'Failed to send magic link. Please try again.'
          );
        }
      } else {
        setErrorMessage('An unexpected error occurred. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 sm:text-4xl">
            Recover Your Plan
          </h1>
          <p className="mt-3 text-base text-gray-600 sm:text-lg">
            Enter your email to receive a secure magic link to access your keto meal plan.
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          <div>
            <label htmlFor="email" className="sr-only">
              Email address
            </label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setEmailError(null); // Clear error on change
              }}
              disabled={isLoading}
              className={`
                appearance-none relative block w-full px-4 py-3
                border ${emailError ? 'border-red-500' : 'border-gray-300'}
                placeholder-gray-500 text-gray-900 rounded-lg
                focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500
                focus:z-10 text-base sm:text-lg
                disabled:bg-gray-100 disabled:cursor-not-allowed
              `}
              placeholder="Enter your email address"
              aria-invalid={!!emailError}
              aria-describedby={emailError ? 'email-error' : undefined}
            />
            {emailError && (
              <p id="email-error" className="mt-2 text-sm text-red-600">
                {emailError}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className={`
              group relative w-full flex justify-center py-3 px-4
              border border-transparent text-base font-medium rounded-lg
              text-white bg-green-600 hover:bg-green-700
              focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500
              transition-colors duration-200
              disabled:bg-gray-400 disabled:cursor-not-allowed
              sm:text-lg
            `}
          >
            {isLoading ? (
              <span className="flex items-center">
                <svg
                  className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
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
                Sending...
              </span>
            ) : (
              'Send Magic Link'
            )}
          </button>
        </form>

        {/* Success Message */}
        {successMessage && (
          <div
            className="rounded-lg bg-green-50 p-4 border border-green-200"
            role="alert"
          >
            <div className="flex">
              <div className="flex-shrink-0">
                <svg
                  className="h-5 w-5 text-green-400"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-green-800">
                  Check your email
                </h3>
                <div className="mt-2 text-sm text-green-700">
                  <p>{successMessage}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Error Message */}
        {errorMessage && (
          <div
            className="rounded-lg bg-red-50 p-4 border border-red-200"
            role="alert"
          >
            <div className="flex">
              <div className="flex-shrink-0">
                <svg
                  className="h-5 w-5 text-red-400"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">
                  Error
                </h3>
                <div className="mt-2 text-sm text-red-700">
                  <p>{errorMessage}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Info Box */}
        <div className="rounded-lg bg-blue-50 p-4 border border-blue-200">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-blue-400"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3 flex-1">
              <h3 className="text-sm font-medium text-blue-800">
                Security Information
              </h3>
              <div className="mt-2 text-sm text-blue-700">
                <ul className="list-disc list-inside space-y-1">
                  <li>Magic links expire in 24 hours</li>
                  <li>Each link can only be used once</li>
                  <li>Check your spam folder if you don't see the email</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center text-sm text-gray-600">
          <p>
            Don't have a meal plan yet?{' '}
            <a
              href="/"
              className="font-medium text-green-600 hover:text-green-500 transition-colors"
            >
              Start your quiz
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
