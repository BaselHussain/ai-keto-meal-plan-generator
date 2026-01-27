/**
 * Authentication Service
 * Handles account registration and login API communication
 * Following Phase 7.3 requirements: optional account creation with signup tokens
 */

// API Response Types
export interface RegisterResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  email: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  email: string;
}

export interface SignupTokenPayload {
  email: string;
  meal_plan_id?: string;
  payment_id?: string;
  exp: number;
  iat: number;
}

// Error Response Type
interface AuthErrorResponse {
  detail: {
    code: string;
    message: string;
  };
}

// Custom Error Class
export class AuthServiceError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public code?: string
  ) {
    super(message);
    this.name = 'AuthServiceError';
  }
}

// API Base URL (uses Next.js API proxy)
const API_BASE_URL = '/api/v1/auth';

/**
 * Decode JWT token payload without verification (client-side preview only).
 * WARNING: This does NOT verify signature - only for displaying data to user.
 * Server MUST verify token signature in POST /api/v1/auth/register.
 *
 * @param token JWT token string
 * @returns Decoded payload or null if invalid format
 */
export function decodeSignupToken(token: string): SignupTokenPayload | null {
  try {
    // JWT format: header.payload.signature
    const parts = token.split('.');
    if (parts.length !== 3) {
      return null;
    }

    // Decode base64url payload (second part)
    const payload = parts[1];
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    const parsed = JSON.parse(decoded);

    // Basic validation
    if (!parsed.email || !parsed.exp || parsed.type !== 'signup') {
      return null;
    }

    return parsed;
  } catch (error) {
    console.error('Failed to decode signup token:', error);
    return null;
  }
}

/**
 * Register new user account
 * POST /api/v1/auth/register
 *
 * Supports two flows:
 * 1. Direct registration: email + password
 * 2. Token-based registration: email (from token, readonly) + password
 *
 * @param email User email address
 * @param password User password (min 8 chars)
 * @param signupToken Optional signup token from delivery email
 * @returns RegisterResponse with access token
 * @throws AuthServiceError on failure
 */
export async function registerAccount(
  email: string,
  password: string,
  signupToken?: string
): Promise<RegisterResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        password,
        signup_token: signupToken || null,
      }),
    });

    if (!response.ok) {
      // Handle HTTP errors
      const errorData: AuthErrorResponse = await response
        .json()
        .catch(() => ({
          detail: {
            code: 'unknown_error',
            message: 'Failed to create account',
          },
        }));

      const detail = errorData.detail || {
        code: 'unknown_error',
        message: 'Unknown error',
      };

      throw new AuthServiceError(
        detail.message || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        detail.code
      );
    }

    const data: RegisterResponse = await response.json();
    return data;
  } catch (error) {
    // Handle network errors and other exceptions
    if (error instanceof AuthServiceError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new AuthServiceError(
        'Network error. Please check your internet connection and try again.',
        0,
        'network_error'
      );
    }

    // Unknown error
    throw new AuthServiceError(
      'An unexpected error occurred. Please try again.',
      500,
      'unknown_error'
    );
  }
}

/**
 * Login with email and password
 * POST /api/v1/auth/login
 *
 * @param email User email address
 * @param password User password
 * @returns LoginResponse with access token
 * @throws AuthServiceError on failure (invalid credentials, etc.)
 */
export async function loginAccount(
  email: string,
  password: string
): Promise<LoginResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      // Handle HTTP errors
      const errorData: AuthErrorResponse = await response
        .json()
        .catch(() => ({
          detail: {
            code: 'unknown_error',
            message: 'Failed to login',
          },
        }));

      const detail = errorData.detail || {
        code: 'unknown_error',
        message: 'Unknown error',
      };

      throw new AuthServiceError(
        detail.message || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        detail.code
      );
    }

    const data: LoginResponse = await response.json();
    return data;
  } catch (error) {
    // Handle network errors and other exceptions
    if (error instanceof AuthServiceError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new AuthServiceError(
        'Network error. Please check your internet connection and try again.',
        0,
        'network_error'
      );
    }

    // Unknown error
    throw new AuthServiceError(
      'An unexpected error occurred. Please try again.',
      500,
      'unknown_error'
    );
  }
}

/**
 * Store access token in localStorage
 * WARNING: Consider using httpOnly cookies for better security
 *
 * @param token Access token from login/register response
 */
export function storeAccessToken(token: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem('access_token', token);
  }
}

/**
 * Get stored access token from localStorage
 *
 * @returns Access token or null if not found
 */
export function getAccessToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('access_token');
  }
  return null;
}

/**
 * Clear stored access token (logout)
 */
export function clearAccessToken(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('access_token');
  }
}

/**
 * Check if user is authenticated
 *
 * @returns true if access token exists, false otherwise
 */
export function isAuthenticated(): boolean {
  return getAccessToken() !== null;
}
