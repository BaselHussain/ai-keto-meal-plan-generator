/**
 * Email Verification Service
 * Handles API communication for email verification during checkout
 * Following FR-Q-019 requirements: 6-digit codes, 10-min expiry, 24h verified status
 */

// API Response Types
export interface SendCodeResponse {
  success: boolean;
  message: string;
  code?: string; // Only present in development/testing
  cooldown_remaining?: number; // Seconds until next send allowed
}

export interface VerifyCodeResponse {
  success: boolean;
  message: string;
  verified_until?: string; // ISO timestamp (24h from now)
}

export interface VerificationStatusResponse {
  email: string;
  verified: boolean;
  verified_ttl?: number; // Seconds until verification expires
}

// Error Response Type
interface VerificationErrorResponse {
  detail: {
    code: string;
    message: string;
    cooldown_remaining?: number;
  };
}

// Custom Error Class
export class VerificationServiceError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public code?: string,
    public cooldownRemaining?: number
  ) {
    super(message);
    this.name = 'VerificationServiceError';
  }
}

// API Base URL (relative to frontend, proxied in development)
const API_BASE_URL = '/api/verification';

/**
 * Send verification code to email
 * POST /api/verification/send-code
 *
 * @param email Email address to send code to
 * @returns SendCodeResponse with success status and optional code (dev only)
 * @throws VerificationServiceError on failure
 */
export async function sendVerificationCode(
  email: string
): Promise<SendCodeResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/send-code`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) {
      // Handle HTTP errors
      const errorData: VerificationErrorResponse = await response
        .json()
        .catch(() => ({
          detail: {
            code: 'unknown_error',
            message: 'Failed to send verification code',
          },
        }));

      const detail = errorData.detail || { code: 'unknown_error', message: 'Unknown error' };

      throw new VerificationServiceError(
        detail.message || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        detail.code,
        detail.cooldown_remaining
      );
    }

    const data: SendCodeResponse = await response.json();
    return data;
  } catch (error) {
    // Handle network errors and other exceptions
    if (error instanceof VerificationServiceError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new VerificationServiceError(
        'Network error. Please check your internet connection and try again.',
        0,
        'network_error'
      );
    }

    // Unknown error
    throw new VerificationServiceError(
      'An unexpected error occurred. Please try again.',
      500,
      'unknown_error'
    );
  }
}

/**
 * Verify email with 6-digit code
 * POST /api/verification/verify-code
 *
 * @param email Email address to verify
 * @param code 6-digit verification code
 * @returns VerifyCodeResponse with success status and verified_until timestamp
 * @throws VerificationServiceError on failure
 */
export async function verifyCode(
  email: string,
  code: string
): Promise<VerifyCodeResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/verify-code`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, code }),
    });

    if (!response.ok) {
      // Handle HTTP errors
      const errorData: VerificationErrorResponse = await response
        .json()
        .catch(() => ({
          detail: {
            code: 'unknown_error',
            message: 'Failed to verify code',
          },
        }));

      const detail = errorData.detail || { code: 'unknown_error', message: 'Unknown error' };

      throw new VerificationServiceError(
        detail.message || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        detail.code
      );
    }

    const data: VerifyCodeResponse = await response.json();
    return data;
  } catch (error) {
    // Handle network errors and other exceptions
    if (error instanceof VerificationServiceError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new VerificationServiceError(
        'Network error. Please check your internet connection and try again.',
        0,
        'network_error'
      );
    }

    // Unknown error
    throw new VerificationServiceError(
      'An unexpected error occurred. Please try again.',
      500,
      'unknown_error'
    );
  }
}

/**
 * Check if email is currently verified (24h window)
 * GET /api/verification/status/{email}
 *
 * @param email Email address to check
 * @returns VerificationStatusResponse with verified status and TTL
 * @throws VerificationServiceError on failure
 */
export async function checkVerificationStatus(
  email: string
): Promise<VerificationStatusResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/status/${encodeURIComponent(email)}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      // Handle HTTP errors
      const errorData: VerificationErrorResponse = await response
        .json()
        .catch(() => ({
          detail: {
            code: 'unknown_error',
            message: 'Failed to check verification status',
          },
        }));

      const detail = errorData.detail || { code: 'unknown_error', message: 'Unknown error' };

      throw new VerificationServiceError(
        detail.message || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        detail.code
      );
    }

    const data: VerificationStatusResponse = await response.json();
    return data;
  } catch (error) {
    // Handle network errors and other exceptions
    if (error instanceof VerificationServiceError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new VerificationServiceError(
        'Network error. Please check your internet connection and try again.',
        0,
        'network_error'
      );
    }

    // Unknown error
    throw new VerificationServiceError(
      'An unexpected error occurred. Please try again.',
      500,
      'unknown_error'
    );
  }
}

// LocalStorage helpers for 24h verified status persistence
const VERIFICATION_STORAGE_KEY = 'email_verification';

export interface VerificationStorage {
  email: string;
  verified: boolean;
  verifiedUntil: string; // ISO date string
}

/**
 * Save verified status to localStorage (24h persistence)
 */
export function saveVerificationStatus(email: string, verifiedUntil: Date): void {
  const storage: VerificationStorage = {
    email,
    verified: true,
    verifiedUntil: verifiedUntil.toISOString(),
  };
  localStorage.setItem(VERIFICATION_STORAGE_KEY, JSON.stringify(storage));
}

/**
 * Get verified status from localStorage
 * Returns null if not found or expired
 */
export function getVerificationStatus(): VerificationStorage | null {
  try {
    const stored = localStorage.getItem(VERIFICATION_STORAGE_KEY);
    if (!stored) return null;

    const data: VerificationStorage = JSON.parse(stored);

    // Check if expired
    const verifiedUntil = new Date(data.verifiedUntil);
    if (verifiedUntil < new Date()) {
      // Expired - clear storage
      clearVerificationStatus();
      return null;
    }

    return data;
  } catch (error) {
    // Invalid data - clear storage
    clearVerificationStatus();
    return null;
  }
}

/**
 * Clear verification status from localStorage
 */
export function clearVerificationStatus(): void {
  localStorage.removeItem(VERIFICATION_STORAGE_KEY);
}
