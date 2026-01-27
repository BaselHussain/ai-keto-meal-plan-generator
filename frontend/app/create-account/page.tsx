'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  registerAccount,
  decodeSignupToken,
  storeAccessToken,
  AuthServiceError,
  SignupTokenPayload,
} from '@/services/authService';

/**
 * Create Account Page Component (T101)
 *
 * Account creation page with signup token validation.
 *
 * Route: /create-account?token=<signup_token>
 *
 * Flow:
 * 1. On mount, decode token to extract email (client-side preview)
 * 2. Show email as readonly/pre-filled field (user cannot change)
 * 3. User enters password + confirmation
 * 4. Submit to POST /api/v1/auth/register with signup_token
 * 5. On success: store access token, redirect to dashboard
 * 6. On error: show error message
 *
 * Features:
 * - Signup token decoding (client-side, no verification)
 * - Email readonly field (pre-filled from token)
 * - Password strength indicator
 * - Password confirmation validation
 * - Loading states with animations
 * - Error states for token/validation/network errors
 * - Mobile-first responsive design
 * - WCAG 2.1 AA accessibility
 *
 * Reference:
 *   Phase 7.3 - Optional Account Creation (T101)
 *   specs/001-keto-meal-plan-generator/contracts/auth-api.yaml
 *   FR-R-001 (Email must match purchase email)
 */

// Zod validation schema
const createAccountSchema = z
  .object({
    email: z
      .string()
      .email('Invalid email address')
      .min(1, 'Email is required'),
    password: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .max(128, 'Password must be less than 128 characters'),
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  });

type CreateAccountFormData = z.infer<typeof createAccountSchema>;

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: 'easeOut' },
  },
};

type PageState = 'loading' | 'ready' | 'submitting' | 'error';

interface ErrorDetails {
  code: string;
  message: string;
  title: string;
}

function CreateAccountPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get('token');

  const [pageState, setPageState] = useState<PageState>('loading');
  const [tokenPayload, setTokenPayload] = useState<SignupTokenPayload | null>(
    null
  );
  const [error, setError] = useState<ErrorDetails | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // React Hook Form setup
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setValue,
    watch,
  } = useForm<CreateAccountFormData>({
    resolver: zodResolver(createAccountSchema),
    mode: 'onBlur',
  });

  const password = watch('password');

  // Decode token on mount
  useEffect(() => {
    if (!token) {
      setPageState('error');
      setError({
        code: 'MISSING_TOKEN',
        title: 'Invalid Link',
        message:
          'This link is missing required information. Please use the link from your email or create an account directly.',
      });
      return;
    }

    // Decode token (client-side preview only, server will verify)
    const payload = decodeSignupToken(token);

    if (!payload) {
      setPageState('error');
      setError({
        code: 'INVALID_TOKEN',
        title: 'Invalid Link',
        message:
          'This account creation link is invalid. Please use the link from your email or create an account directly.',
      });
      return;
    }

    // Check if token is expired (client-side check only)
    const now = Math.floor(Date.now() / 1000);
    if (payload.exp && payload.exp < now) {
      setPageState('error');
      setError({
        code: 'TOKEN_EXPIRED',
        title: 'Link Expired',
        message:
          'This account creation link has expired. Please request a new one or create an account directly.',
      });
      return;
    }

    // Token is valid (client-side), set email and show form
    setTokenPayload(payload);
    setValue('email', payload.email);
    setPageState('ready');
  }, [token, setValue]);

  // Calculate password strength
  const getPasswordStrength = (pwd: string): number => {
    if (!pwd) return 0;
    let strength = 0;

    // Length
    if (pwd.length >= 8) strength += 25;
    if (pwd.length >= 12) strength += 25;

    // Character variety
    if (/[a-z]/.test(pwd)) strength += 15;
    if (/[A-Z]/.test(pwd)) strength += 15;
    if (/[0-9]/.test(pwd)) strength += 10;
    if (/[^a-zA-Z0-9]/.test(pwd)) strength += 10;

    return Math.min(strength, 100);
  };

  const passwordStrength = getPasswordStrength(password || '');

  const getStrengthColor = (strength: number): string => {
    if (strength < 40) return 'bg-red-500';
    if (strength < 70) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getStrengthLabel = (strength: number): string => {
    if (strength < 40) return 'Weak';
    if (strength < 70) return 'Good';
    return 'Strong';
  };

  // Handle form submission
  const onSubmit = async (data: CreateAccountFormData) => {
    if (!token) {
      setSubmitError('Missing signup token. Please use the link from your email.');
      return;
    }

    setPageState('submitting');
    setSubmitError(null);

    try {
      // Register account with signup token
      const response = await registerAccount(
        data.email,
        data.password,
        token
      );

      // Store access token
      storeAccessToken(response.access_token);

      // Redirect to dashboard (or meal plan page)
      router.push('/dashboard');
    } catch (err) {
      setPageState('ready');

      if (err instanceof AuthServiceError) {
        // Map error codes to user-friendly messages
        switch (err.code) {
          case 'EMAIL_ALREADY_EXISTS':
            setSubmitError(
              'An account with this email already exists. Please login instead.'
            );
            break;
          case 'INVALID_TOKEN':
            setSubmitError(
              'This account creation link is invalid. Please request a new one.'
            );
            break;
          case 'TOKEN_EXPIRED':
            setSubmitError(
              'This account creation link has expired. Please request a new one.'
            );
            break;
          case 'EMAIL_MISMATCH':
            setSubmitError(
              'Email does not match the account creation link. Please use the email from your purchase.'
            );
            break;
          case 'network_error':
            setSubmitError(
              'Unable to connect to the server. Please check your internet connection and try again.'
            );
            break;
          default:
            setSubmitError(
              err.message || 'Failed to create account. Please try again.'
            );
        }
      } else {
        setSubmitError('An unexpected error occurred. Please try again.');
      }
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 py-12 px-4">
      <div className="max-w-md mx-auto">
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
              <div className="relative w-16 h-16 mx-auto mb-4">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    ease: 'linear',
                  }}
                  className="absolute inset-2 rounded-full border-4 border-green-200 border-t-green-600"
                />
              </div>
              <h2 className="text-xl font-bold text-gray-900 mb-2">
                Loading...
              </h2>
              <p className="text-gray-600 text-sm">
                Preparing your account creation
              </p>
            </motion.div>
          )}

          {/* Ready State - Account Creation Form */}
          {(pageState === 'ready' || pageState === 'submitting') &&
            tokenPayload && (
              <motion.div
                key="form"
                variants={containerVariants}
                initial="hidden"
                animate="visible"
                exit={{ opacity: 0, scale: 0.95 }}
                className="bg-white rounded-2xl shadow-xl p-8"
              >
                {/* Header */}
                <motion.div variants={itemVariants} className="text-center mb-6">
                  <div className="w-16 h-16 mx-auto mb-4 bg-green-100 rounded-full flex items-center justify-center">
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
                        d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"
                      />
                    </svg>
                  </div>
                  <h1 className="text-3xl font-bold text-gray-900 mb-2">
                    Create Your Account
                  </h1>
                  <p className="text-gray-600">
                    Get permanent access to your meal plan
                  </p>
                </motion.div>

                {/* Form */}
                <motion.form
                  variants={itemVariants}
                  onSubmit={handleSubmit(onSubmit)}
                  className="space-y-5"
                >
                  {/* Email field (readonly) */}
                  <div>
                    <label
                      htmlFor="email"
                      className="block text-sm font-medium text-gray-700 mb-2"
                    >
                      Email Address
                    </label>
                    <input
                      id="email"
                      type="email"
                      readOnly
                      {...register('email')}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg bg-gray-50 text-gray-700 cursor-not-allowed focus:outline-none"
                      aria-describedby="email-help"
                    />
                    <p
                      id="email-help"
                      className="mt-2 text-xs text-gray-500 flex items-center gap-1"
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
                          d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                        />
                      </svg>
                      Email from your purchase (cannot be changed)
                    </p>
                  </div>

                  {/* Password field */}
                  <div>
                    <label
                      htmlFor="password"
                      className="block text-sm font-medium text-gray-700 mb-2"
                    >
                      Password
                    </label>
                    <input
                      id="password"
                      type="password"
                      {...register('password')}
                      className={`w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 transition-colors ${
                        errors.password
                          ? 'border-red-500 focus:ring-red-500'
                          : 'border-gray-300 focus:ring-green-500'
                      }`}
                      placeholder="Enter your password (min 8 characters)"
                      aria-describedby="password-error password-strength"
                      disabled={pageState === 'submitting'}
                    />
                    {errors.password && (
                      <p
                        id="password-error"
                        className="mt-2 text-sm text-red-600"
                        role="alert"
                      >
                        {errors.password.message}
                      </p>
                    )}

                    {/* Password strength indicator */}
                    {password && password.length > 0 && (
                      <div className="mt-3" id="password-strength">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs text-gray-600">
                            Password strength:
                          </span>
                          <span
                            className={`text-xs font-medium ${
                              passwordStrength < 40
                                ? 'text-red-600'
                                : passwordStrength < 70
                                ? 'text-yellow-600'
                                : 'text-green-600'
                            }`}
                          >
                            {getStrengthLabel(passwordStrength)}
                          </span>
                        </div>
                        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${passwordStrength}%` }}
                            transition={{ duration: 0.3 }}
                            className={`h-full ${getStrengthColor(
                              passwordStrength
                            )} transition-colors duration-300`}
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Confirm Password field */}
                  <div>
                    <label
                      htmlFor="confirmPassword"
                      className="block text-sm font-medium text-gray-700 mb-2"
                    >
                      Confirm Password
                    </label>
                    <input
                      id="confirmPassword"
                      type="password"
                      {...register('confirmPassword')}
                      className={`w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 transition-colors ${
                        errors.confirmPassword
                          ? 'border-red-500 focus:ring-red-500'
                          : 'border-gray-300 focus:ring-green-500'
                      }`}
                      placeholder="Re-enter your password"
                      aria-describedby="confirm-password-error"
                      disabled={pageState === 'submitting'}
                    />
                    {errors.confirmPassword && (
                      <p
                        id="confirm-password-error"
                        className="mt-2 text-sm text-red-600"
                        role="alert"
                      >
                        {errors.confirmPassword.message}
                      </p>
                    )}
                  </div>

                  {/* Submit error */}
                  {submitError && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3"
                      role="alert"
                    >
                      <svg
                        className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                      <p className="text-sm text-red-800">{submitError}</p>
                    </motion.div>
                  )}

                  {/* Submit button */}
                  <motion.button
                    whileHover={
                      pageState !== 'submitting' ? { scale: 1.02 } : undefined
                    }
                    whileTap={
                      pageState !== 'submitting' ? { scale: 0.98 } : undefined
                    }
                    type="submit"
                    disabled={pageState === 'submitting'}
                    className="w-full bg-gradient-to-r from-green-500 to-green-600 text-white font-semibold py-4 px-6 rounded-xl shadow-lg hover:from-green-600 hover:to-green-700 transition-colors duration-200 flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {pageState === 'submitting' ? (
                      <>
                        <svg
                          className="animate-spin h-5 w-5"
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
                        <span>Creating Account...</span>
                      </>
                    ) : (
                      <>
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
                        <span>Create Account</span>
                      </>
                    )}
                  </motion.button>
                </motion.form>

                {/* Footer */}
                <motion.div
                  variants={itemVariants}
                  className="mt-6 text-center"
                >
                  <p className="text-sm text-gray-600">
                    Already have an account?{' '}
                    <a
                      href="/login"
                      className="text-green-600 hover:text-green-700 font-medium"
                    >
                      Login here
                    </a>
                  </p>
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
                <a
                  href="/recover-plan"
                  className="block w-full bg-green-600 text-white font-semibold py-3 px-6 rounded-lg hover:bg-green-700 transition-colors"
                >
                  Request New Link
                </a>
                <a
                  href="/"
                  className="block w-full border border-gray-300 text-gray-700 font-medium py-3 px-6 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Go to Home
                </a>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

// Wrap content in Suspense to handle useSearchParams
export default function CreateAccountPage() {
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
      <CreateAccountPageContent />
    </Suspense>
  );
}
