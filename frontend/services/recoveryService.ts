/**
 * Recovery Service
 * Handles API communication for magic link-based plan recovery
 * Following Phase 7.1 requirements: magic link generation with rate limiting
 */

// API Response Types
export interface RequestMagicLinkResponse {
  message: string;
}

export interface VerifyMagicLinkResponse {
  meal_plan_id: string;
  email: string;
  created_at: string;
  pdf_available: boolean;
}

// Error Response Type
interface RecoveryErrorResponse {
  detail: {
    code: string;
    message: string;
    retry_after?: string; // ISO timestamp when rate limit resets
  };
}

// Custom Error Class
export class RecoveryServiceError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public code?: string,
    public retryAfter?: string
  ) {
    super(message);
    this.name = 'RecoveryServiceError';
  }
}

// API Base URL (uses Next.js API proxy)
const API_BASE_URL = '/api/v1/recovery';

/**
 * Request magic link for plan recovery
 * POST /api/v1/recovery/request-magic-link
 *
 * Rate limits:
 * - 3 requests per email per 24 hours
 * - 5 requests per IP per hour
 *
 * @param email Email address to send magic link to
 * @returns RequestMagicLinkResponse with generic success message
 * @throws RecoveryServiceError on failure (rate limit, network error, etc.)
 */
export async function requestMagicLink(
  email: string
): Promise<RequestMagicLinkResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/request-magic-link`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) {
      // Handle HTTP errors
      const errorData: RecoveryErrorResponse = await response
        .json()
        .catch(() => ({
          detail: {
            code: 'unknown_error',
            message: 'Failed to request magic link',
          },
        }));

      const detail = errorData.detail || { code: 'unknown_error', message: 'Unknown error' };

      throw new RecoveryServiceError(
        detail.message || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        detail.code,
        detail.retry_after
      );
    }

    const data: RequestMagicLinkResponse = await response.json();
    return data;
  } catch (error) {
    // Handle network errors and other exceptions
    if (error instanceof RecoveryServiceError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new RecoveryServiceError(
        'Network error. Please check your internet connection and try again.',
        0,
        'network_error'
      );
    }

    // Unknown error
    throw new RecoveryServiceError(
      'An unexpected error occurred. Please try again.',
      500,
      'unknown_error'
    );
  }
}

/**
 * Verify magic link token (T097)
 * GET /api/v1/recovery/verify
 *
 * Validates token and returns meal plan details if valid.
 * Token must be valid, unused, and not expired (24h validity).
 *
 * @param token Magic link token from email
 * @returns VerifyMagicLinkResponse with meal plan details
 * @throws RecoveryServiceError on failure (invalid, expired, used token)
 */
export async function verifyMagicLink(
  token: string
): Promise<VerifyMagicLinkResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/verify?token=${encodeURIComponent(token)}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      // Handle HTTP errors
      const errorData: RecoveryErrorResponse = await response
        .json()
        .catch(() => ({
          detail: {
            code: 'unknown_error',
            message: 'Failed to verify magic link',
          },
        }));

      const detail = errorData.detail || { code: 'unknown_error', message: 'Unknown error' };

      throw new RecoveryServiceError(
        detail.message || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        detail.code
      );
    }

    const data: VerifyMagicLinkResponse = await response.json();
    return data;
  } catch (error) {
    // Handle network errors and other exceptions
    if (error instanceof RecoveryServiceError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new RecoveryServiceError(
        'Network error. Please check your internet connection and try again.',
        0,
        'network_error'
      );
    }

    // Unknown error
    throw new RecoveryServiceError(
      'An unexpected error occurred. Please try again.',
      500,
      'unknown_error'
    );
  }
}
