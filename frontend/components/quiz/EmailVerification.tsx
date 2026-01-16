'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  sendVerificationCode,
  verifyCode,
  checkVerificationStatus,
  saveVerificationStatus,
  getVerificationStatus,
  clearVerificationStatus,
  VerificationServiceError,
} from '../../services/verificationService';

export interface EmailVerificationProps {
  /** Email address to verify */
  email: string;
  /** Callback when verification succeeds */
  onVerified: () => void;
  /** Optional cancel button callback */
  onCancel?: () => void;
}

/**
 * Email Verification Component
 *
 * Implements FR-Q-019 email verification flow:
 * - Send 6-digit code with 60s cooldown
 * - Verify code with constant-time comparison
 * - 24-hour verified status persistence
 * - Mobile-first responsive design
 */
export function EmailVerification({
  email,
  onVerified,
  onCancel,
}: EmailVerificationProps) {
  // State management
  const [code, setCode] = useState('');
  const [isVerified, setIsVerified] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cooldownSeconds, setCooldownSeconds] = useState(0);
  const [verifiedUntil, setVerifiedUntil] = useState<Date | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);

  // Refs
  const codeInputRef = useRef<HTMLInputElement>(null);
  const cooldownIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Check if email is already verified on mount
  useEffect(() => {
    const stored = getVerificationStatus();
    if (stored && stored.email === email && stored.verified) {
      setIsVerified(true);
      setVerifiedUntil(new Date(stored.verifiedUntil));
      setShowSuccess(true);
      // Auto-call onVerified after brief delay
      setTimeout(() => onVerified(), 1000);
    }
  }, [email, onVerified]);

  // Cooldown timer
  useEffect(() => {
    if (cooldownSeconds > 0) {
      cooldownIntervalRef.current = setInterval(() => {
        setCooldownSeconds((prev) => {
          if (prev <= 1) {
            if (cooldownIntervalRef.current) {
              clearInterval(cooldownIntervalRef.current);
            }
            return 0;
          }
          return prev - 1;
        });
      }, 1000);

      return () => {
        if (cooldownIntervalRef.current) {
          clearInterval(cooldownIntervalRef.current);
        }
      };
    }
  }, [cooldownSeconds]);

  // Auto-focus code input
  useEffect(() => {
    if (!isVerified && codeInputRef.current) {
      codeInputRef.current.focus();
    }
  }, [isVerified]);

  /**
   * Send verification code to email
   */
  const handleSendCode = useCallback(async () => {
    setIsSending(true);
    setError(null);

    try {
      const response = await sendVerificationCode(email);

      // Start 60s cooldown
      setCooldownSeconds(60);

      // Show success message
      setError(null);

      // In development, log the code (will be removed in production)
      if (response.code) {
        console.log(`[DEV] Verification code: ${response.code}`);
      }
    } catch (err) {
      if (err instanceof VerificationServiceError) {
        if (err.cooldownRemaining) {
          setCooldownSeconds(err.cooldownRemaining);
          setError(`Please wait ${err.cooldownRemaining} seconds before requesting a new code.`);
        } else {
          setError(err.message);
        }
      } else {
        setError('Failed to send verification code. Please try again.');
      }
    } finally {
      setIsSending(false);
    }
  }, [email]);

  /**
   * Verify the entered code
   */
  const handleVerifyCode = useCallback(async () => {
    if (code.length !== 6) {
      setError('Please enter a 6-digit code.');
      return;
    }

    setIsVerifying(true);
    setError(null);

    try {
      const response = await verifyCode(email, code);

      if (response.success) {
        // Parse verified_until timestamp
        const verifiedUntilDate = response.verified_until
          ? new Date(response.verified_until)
          : new Date(Date.now() + 24 * 60 * 60 * 1000); // 24h from now

        // Save to localStorage
        saveVerificationStatus(email, verifiedUntilDate);

        // Update state
        setIsVerified(true);
        setVerifiedUntil(verifiedUntilDate);
        setShowSuccess(true);

        // Clear code input
        setCode('');

        // Call onVerified callback after brief success animation
        setTimeout(() => onVerified(), 1500);
      }
    } catch (err) {
      if (err instanceof VerificationServiceError) {
        setError(err.message);
      } else {
        setError('Failed to verify code. Please try again.');
      }
      // Clear code on error
      setCode('');
      codeInputRef.current?.focus();
    } finally {
      setIsVerifying(false);
    }
  }, [email, code, onVerified]);

  /**
   * Handle code input change (numbers only, max 6 digits)
   */
  const handleCodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, ''); // Remove non-digits
    if (value.length <= 6) {
      setCode(value);
      setError(null);
    }
  };

  /**
   * Handle Enter key press
   */
  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && code.length === 6 && !isVerifying) {
      handleVerifyCode();
    }
  };

  // Success state
  if (showSuccess && isVerified) {
    return (
      <div className="flex flex-col items-center justify-center space-y-4 p-6 bg-green-50 border-2 border-green-200 rounded-lg">
        {/* Success checkmark */}
        <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center animate-bounce">
          <svg
            className="w-10 h-10 text-white"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={3}
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>

        {/* Success message */}
        <div className="text-center">
          <h3 className="text-xl font-semibold text-green-800 mb-2">
            Email Verified!
          </h3>
          <p className="text-sm text-green-700">
            {email}
          </p>
          <p className="text-xs text-green-600 mt-2">
            Proceeding to payment...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md mx-auto space-y-6 p-6 bg-white border border-gray-200 rounded-lg shadow-sm">
      {/* Header */}
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-gray-900">
          Verify Your Email
        </h2>
        <p className="text-sm text-gray-600">
          We'll send a verification code to:
        </p>
        <p className="text-base font-medium text-gray-900">
          {email}
        </p>
      </div>

      {/* Send Code Button */}
      {!isVerified && cooldownSeconds === 0 && (
        <button
          onClick={handleSendCode}
          disabled={isSending}
          className="w-full py-3 px-4 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
          aria-label="Send verification code"
        >
          {isSending ? (
            <span className="flex items-center justify-center space-x-2">
              <svg
                className="animate-spin h-5 w-5 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              <span>Sending...</span>
            </span>
          ) : (
            'Send Verification Code'
          )}
        </button>
      )}

      {/* Cooldown message */}
      {cooldownSeconds > 0 && (
        <div className="text-center space-y-4">
          <p className="text-sm text-gray-600">
            Code sent! Check your email.
          </p>

          {/* Code Input */}
          <div className="space-y-2">
            <label htmlFor="verification-code" className="block text-sm font-medium text-gray-700">
              Enter 6-digit code
            </label>
            <input
              ref={codeInputRef}
              id="verification-code"
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={6}
              value={code}
              onChange={handleCodeChange}
              onKeyPress={handleKeyPress}
              placeholder="000000"
              disabled={isVerifying}
              className="w-full text-center text-3xl font-mono tracking-widest px-4 py-4 border-2 border-gray-300 rounded-lg focus:border-green-500 focus:ring-2 focus:ring-green-200 focus:outline-none disabled:bg-gray-100 disabled:cursor-not-allowed"
              aria-label="6-digit verification code"
              aria-describedby={error ? 'verification-error' : undefined}
              autoComplete="off"
            />
          </div>

          {/* Verify Button */}
          <button
            onClick={handleVerifyCode}
            disabled={code.length !== 6 || isVerifying}
            className="w-full py-3 px-4 bg-green-600 hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
            aria-label="Verify code"
          >
            {isVerifying ? (
              <span className="flex items-center justify-center space-x-2">
                <svg
                  className="animate-spin h-5 w-5 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                <span>Verifying...</span>
              </span>
            ) : (
              'Verify Code'
            )}
          </button>

          {/* Resend button */}
          <button
            onClick={handleSendCode}
            disabled={cooldownSeconds > 0 || isSending}
            className="w-full text-sm text-green-600 hover:text-green-700 disabled:text-gray-400 disabled:cursor-not-allowed font-medium transition-colors duration-200 focus:outline-none focus:underline"
            aria-label={cooldownSeconds > 0 ? `Resend code in ${cooldownSeconds} seconds` : 'Resend code'}
          >
            {cooldownSeconds > 0
              ? `Resend in ${cooldownSeconds}s`
              : 'Resend Code'}
          </button>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div
          id="verification-error"
          role="alert"
          className="p-3 bg-red-50 border border-red-200 rounded-lg"
        >
          <p className="text-sm text-red-800 text-center">{error}</p>
        </div>
      )}

      {/* Cancel button */}
      {onCancel && (
        <button
          onClick={onCancel}
          className="w-full text-sm text-gray-500 hover:text-gray-700 font-medium transition-colors duration-200 focus:outline-none focus:underline"
          aria-label="Cancel verification"
        >
          Cancel
        </button>
      )}

      {/* Privacy note */}
      <div className="pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-500 text-center">
          We'll only use your email to send your meal plan. Your information is never shared.
        </p>
      </div>
    </div>
  );
}
