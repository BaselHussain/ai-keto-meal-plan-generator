/**
 * Environment variable validation and type-safe access for Next.js frontend.
 *
 * This module provides validated, type-safe access to environment variables with
 * clear separation between client-side (NEXT_PUBLIC_*) and server-side variables.
 *
 * Key Features:
 * - TypeScript strict mode compliance
 * - Auto-validation on import with SKIP_ENV_VALIDATION=1 escape hatch
 * - Clear error messages for missing/invalid variables
 * - Graceful degradation in development, strict in production
 * - URL validation for API endpoints and Sentry DSN
 *
 * Usage:
 *   import { env, isProduction } from '@/lib/env';
 *
 *   // Client-side (browser accessible)
 *   const sentryDsn = env.NEXT_PUBLIC_SENTRY_DSN;
 *   const apiUrl = env.NEXT_PUBLIC_API_URL;
 *
 *   // Server-side only (API routes, server components)
 *   const serverSentryDsn = env.FRONTEND_SENTRY_DSN;
 */

/* eslint-disable no-console */

// =============================================================================
// Custom Error Class
// =============================================================================

export class EnvValidationError extends Error {
  constructor(
    message: string,
    public readonly errors: Array<{ field: string; message: string }>
  ) {
    super(message);
    this.name = 'EnvValidationError';
  }
}

// =============================================================================
// Type Definitions
// =============================================================================

/**
 * Client-side environment variables (NEXT_PUBLIC_* - exposed to browser)
 * These are bundled into the client JavaScript and visible to users.
 */
export interface ClientEnv {
  /** Sentry DSN for client-side error tracking (required in production) */
  NEXT_PUBLIC_SENTRY_DSN: string | undefined;

  /** Backend API URL for client-side requests */
  NEXT_PUBLIC_API_URL: string | undefined;

  /** Paddle vendor ID for payment processing */
  NEXT_PUBLIC_PADDLE_VENDOR_ID: string | undefined;

  /** Paddle environment (sandbox or production) */
  NEXT_PUBLIC_PADDLE_ENVIRONMENT: 'sandbox' | 'production' | undefined;
}

/**
 * Server-side environment variables (secure - never exposed to browser)
 * Only accessible in API routes, middleware, and server components.
 */
export interface ServerEnv {
  /** Sentry DSN for server-side error tracking */
  FRONTEND_SENTRY_DSN: string | undefined;

  /** Backend API URL for server-side requests (SSR, API routes) */
  API_URL: string | undefined;

  /** GitHub token for development tools (optional) */
  GITHUB_TOKEN: string | undefined;

  /** Node environment */
  NODE_ENV: 'development' | 'production' | 'test';
}

/**
 * Complete environment interface combining client and server variables
 */
export interface Env extends ClientEnv, ServerEnv {}

// =============================================================================
// Validation Helpers
// =============================================================================

/**
 * Validates that a string is a valid URL
 */
function isValidUrl(value: string | undefined): boolean {
  if (!value) return false;
  try {
    new URL(value);
    return true;
  } catch {
    return false;
  }
}

/**
 * Gets an environment variable with optional fallback
 */
function getEnvVar(key: string, fallback?: string): string | undefined {
  if (typeof window !== 'undefined') {
    // Client-side: only access NEXT_PUBLIC_* variables
    if (key.startsWith('NEXT_PUBLIC_')) {
      return process.env[key] || fallback;
    }
    return fallback;
  }
  // Server-side: access all variables
  return process.env[key] || fallback;
}

/**
 * Checks if we're running in production
 */
function checkIsProduction(): boolean {
  return process.env.NODE_ENV === 'production';
}

/**
 * Checks if we're running in development
 */
function checkIsDevelopment(): boolean {
  return process.env.NODE_ENV === 'development';
}

/**
 * Checks if we're running in test mode
 */
function checkIsTest(): boolean {
  return process.env.NODE_ENV === 'test';
}

// =============================================================================
// Validation Logic
// =============================================================================

function validateEnvironment(): Env {
  const errors: Array<{ field: string; message: string }> = [];
  const isProduction = checkIsProduction();
  const isDevelopment = checkIsDevelopment();
  const isTest = checkIsTest();

  // Skip validation if explicitly disabled (useful for build-time)
  if (process.env.SKIP_ENV_VALIDATION === '1') {
    console.warn(
      '⚠️  Environment validation skipped (SKIP_ENV_VALIDATION=1). This should only be used during builds.'
    );
    return {
      NEXT_PUBLIC_SENTRY_DSN: undefined,
      NEXT_PUBLIC_API_URL: undefined,
      NEXT_PUBLIC_PADDLE_VENDOR_ID: undefined,
      NEXT_PUBLIC_PADDLE_ENVIRONMENT: undefined,
      FRONTEND_SENTRY_DSN: undefined,
      API_URL: undefined,
      GITHUB_TOKEN: undefined,
      NODE_ENV: (process.env.NODE_ENV as 'development' | 'production' | 'test') || 'development',
    };
  }

  // =============================================================================
  // Client-Side Variables (NEXT_PUBLIC_*)
  // =============================================================================

  const NEXT_PUBLIC_SENTRY_DSN = getEnvVar('NEXT_PUBLIC_SENTRY_DSN');
  const NEXT_PUBLIC_API_URL = getEnvVar('NEXT_PUBLIC_API_URL');
  const NEXT_PUBLIC_PADDLE_VENDOR_ID = getEnvVar('NEXT_PUBLIC_PADDLE_VENDOR_ID');
  const NEXT_PUBLIC_PADDLE_ENVIRONMENT = getEnvVar('NEXT_PUBLIC_PADDLE_ENVIRONMENT');

  // Validate Sentry DSN (required in production)
  if (isProduction && !NEXT_PUBLIC_SENTRY_DSN) {
    errors.push({
      field: 'NEXT_PUBLIC_SENTRY_DSN',
      message: 'Required in production for error tracking. Get from: https://sentry.io',
    });
  }

  if (NEXT_PUBLIC_SENTRY_DSN && !isValidUrl(NEXT_PUBLIC_SENTRY_DSN)) {
    errors.push({
      field: 'NEXT_PUBLIC_SENTRY_DSN',
      message: 'Must be a valid URL (format: https://xxx@xxx.ingest.sentry.io/xxx)',
    });
  }

  // Validate API URL (optional in development with fallback to localhost)
  const apiUrl = NEXT_PUBLIC_API_URL || (isDevelopment ? 'http://localhost:8000' : undefined);
  if (!apiUrl) {
    errors.push({
      field: 'NEXT_PUBLIC_API_URL',
      message: 'Backend API URL is required. Set to your FastAPI backend URL.',
    });
  } else if (!isValidUrl(apiUrl)) {
    errors.push({
      field: 'NEXT_PUBLIC_API_URL',
      message: 'Must be a valid URL (e.g., http://localhost:8000 or https://api.example.com)',
    });
  }

  // Validate Paddle configuration (optional in development, required in production)
  if (isProduction) {
    if (!NEXT_PUBLIC_PADDLE_VENDOR_ID) {
      errors.push({
        field: 'NEXT_PUBLIC_PADDLE_VENDOR_ID',
        message: 'Required in production for payment processing. Get from Paddle dashboard.',
      });
    }

    if (!NEXT_PUBLIC_PADDLE_ENVIRONMENT) {
      errors.push({
        field: 'NEXT_PUBLIC_PADDLE_ENVIRONMENT',
        message: 'Required in production. Set to "production" or "sandbox".',
      });
    } else if (!['sandbox', 'production'].includes(NEXT_PUBLIC_PADDLE_ENVIRONMENT)) {
      errors.push({
        field: 'NEXT_PUBLIC_PADDLE_ENVIRONMENT',
        message: 'Must be either "sandbox" or "production".',
      });
    }
  }

  // =============================================================================
  // Server-Side Variables (Secure)
  // =============================================================================

  const FRONTEND_SENTRY_DSN = getEnvVar('FRONTEND_SENTRY_DSN');
  const API_URL = getEnvVar('API_URL');
  const GITHUB_TOKEN = getEnvVar('GITHUB_TOKEN');

  // Validate server-side Sentry DSN (required in production)
  if (typeof window === 'undefined') {
    // Only validate on server-side
    if (isProduction && !FRONTEND_SENTRY_DSN) {
      errors.push({
        field: 'FRONTEND_SENTRY_DSN',
        message: 'Required in production for server-side error tracking. Get from: https://sentry.io',
      });
    }

    if (FRONTEND_SENTRY_DSN && !isValidUrl(FRONTEND_SENTRY_DSN)) {
      errors.push({
        field: 'FRONTEND_SENTRY_DSN',
        message: 'Must be a valid URL (format: https://xxx@xxx.ingest.sentry.io/xxx)',
      });
    }

    // Validate server-side API URL
    const serverApiUrl = API_URL || (isDevelopment ? 'http://localhost:8000' : undefined);
    if (!serverApiUrl) {
      errors.push({
        field: 'API_URL',
        message: 'Backend API URL is required for server-side requests.',
      });
    } else if (!isValidUrl(serverApiUrl)) {
      errors.push({
        field: 'API_URL',
        message: 'Must be a valid URL (e.g., http://localhost:8000 or https://api.example.com)',
      });
    }
  }

  // =============================================================================
  // Error Reporting
  // =============================================================================

  if (errors.length > 0) {
    // In development, warn but don't throw (graceful degradation)
    if (isDevelopment || isTest) {
      console.warn('\n' + '='.repeat(80));
      console.warn('ENVIRONMENT VALIDATION WARNINGS (Development Mode)');
      console.warn('='.repeat(80));
      console.warn('\nThe following environment variables have issues:\n');

      errors.forEach(({ field, message }) => {
        console.warn(`  ⚠️  ${field}: ${message}`);
      });

      console.warn('\n' + '='.repeat(80));
      console.warn('Application will continue with default/fallback values.');
      console.warn('See frontend/.env.example for configuration guidance.');
      console.warn('='.repeat(80) + '\n');

      // Return environment with warnings but don't throw
    } else {
      // In production, throw error and prevent startup
      console.error('\n' + '='.repeat(80));
      console.error('ENVIRONMENT VALIDATION FAILED (Production Mode)');
      console.error('='.repeat(80));
      console.error('\nThe following environment variables are missing or invalid:\n');

      errors.forEach(({ field, message }) => {
        console.error(`  ✗ ${field}: ${message}`);
      });

      console.error('\n' + '='.repeat(80));
      console.error('Please check your environment variables and try again.');
      console.error('See frontend/.env.example for reference.');
      console.error('='.repeat(80) + '\n');

      throw new EnvValidationError('Environment validation failed in production', errors);
    }
  }

  // =============================================================================
  // Return Validated Environment
  // =============================================================================

  return {
    // Client-side variables
    NEXT_PUBLIC_SENTRY_DSN,
    NEXT_PUBLIC_API_URL: apiUrl,
    NEXT_PUBLIC_PADDLE_VENDOR_ID,
    NEXT_PUBLIC_PADDLE_ENVIRONMENT: NEXT_PUBLIC_PADDLE_ENVIRONMENT as 'sandbox' | 'production' | undefined,

    // Server-side variables
    FRONTEND_SENTRY_DSN,
    API_URL: API_URL || (isDevelopment ? 'http://localhost:8000' : undefined),
    GITHUB_TOKEN,
    NODE_ENV: (process.env.NODE_ENV as 'development' | 'production' | 'test') || 'development',
  };
}

// =============================================================================
// Exports
// =============================================================================

/**
 * Validated environment variables (auto-validated on import)
 *
 * Access pattern:
 * - Client-side: env.NEXT_PUBLIC_API_URL
 * - Server-side: env.API_URL or env.FRONTEND_SENTRY_DSN
 */
export const env = validateEnvironment();

/**
 * Helper: Check if running in production
 */
export const isProduction = checkIsProduction();

/**
 * Helper: Check if running in development
 */
export const isDevelopment = checkIsDevelopment();

/**
 * Helper: Check if running in test mode
 */
export const isTest = checkIsTest();

/**
 * Helper: Get current environment name
 */
export const currentEnv = env.NODE_ENV;

// =============================================================================
// Type Guards for Runtime Checks
// =============================================================================

/**
 * Type guard to check if a variable is defined (useful for optional env vars)
 */
export function isDefined<T>(value: T | undefined): value is T {
  return value !== undefined;
}

/**
 * Asserts that a required environment variable is defined
 * Throws a descriptive error if not
 */
export function requireEnv(value: string | undefined, name: string): string {
  if (!value) {
    throw new Error(
      `Required environment variable ${name} is not defined. ` +
        'Check your .env.local file and ensure all required variables are set.'
    );
  }
  return value;
}
