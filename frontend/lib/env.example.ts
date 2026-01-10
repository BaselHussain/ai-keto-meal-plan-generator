/**
 * Example usage patterns for the environment validation utility
 *
 * This file demonstrates best practices for accessing environment variables
 * in different Next.js contexts (client components, server components, API routes).
 *
 * DO NOT import this file in production code - it's for reference only.
 */

import { env, isProduction, isDevelopment, requireEnv, isDefined } from './env';

// =============================================================================
// Client Component Usage (Browser)
// =============================================================================

/**
 * Example: Initializing Sentry in a client component
 */
export function initializeClientSentry() {
  // Client-side variables are safe to access in browser
  const sentryDsn = env.NEXT_PUBLIC_SENTRY_DSN;

  if (sentryDsn && isProduction) {
    // Initialize Sentry with validated DSN
    console.log('Initializing Sentry with DSN:', sentryDsn);
  } else if (isDevelopment) {
    console.log('Skipping Sentry initialization in development');
  }
}

/**
 * Example: Making API calls from client components
 */
export async function fetchUserData(userId: string) {
  // Use validated API URL
  const apiUrl = requireEnv(env.NEXT_PUBLIC_API_URL, 'NEXT_PUBLIC_API_URL');

  const response = await fetch(`${apiUrl}/api/users/${userId}`);
  return response.json();
}

/**
 * Example: Initializing Paddle payment widget
 */
export function initializePaddleCheckout() {
  const vendorId = env.NEXT_PUBLIC_PADDLE_VENDOR_ID;
  const environment = env.NEXT_PUBLIC_PADDLE_ENVIRONMENT;

  if (!vendorId || !environment) {
    console.warn('Paddle not configured - payment features disabled');
    return null;
  }

  return {
    vendorId,
    environment,
  };
}

// =============================================================================
// Server Component / API Route Usage (Node.js)
// =============================================================================

/**
 * Example: Server-side API call with error tracking
 *
 * Use this pattern in:
 * - Server Components (app/page.tsx with no 'use client')
 * - API Routes (app/api/[route]/route.ts)
 * - Server Actions
 */
export async function fetchMealPlanServerSide(planId: string) {
  // Server-side: use secure API_URL (not exposed to browser)
  const apiUrl = requireEnv(env.API_URL, 'API_URL');

  try {
    const response = await fetch(`${apiUrl}/api/meal-plans/${planId}`, {
      headers: {
        'Content-Type': 'application/json',
        // Add authentication headers here if needed
      },
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    // Log to server-side Sentry if configured
    if (isDefined(env.FRONTEND_SENTRY_DSN)) {
      console.error('Server error:', error);
      // Sentry.captureException(error);
    }
    throw error;
  }
}

// =============================================================================
// Environment-Specific Configuration
// =============================================================================

/**
 * Example: Feature flags based on environment
 */
export const featureFlags = {
  enableAnalytics: isProduction,
  enableDebugMode: isDevelopment,
  enablePaymentProcessing: isDefined(env.NEXT_PUBLIC_PADDLE_VENDOR_ID),
  enableErrorTracking: isDefined(env.NEXT_PUBLIC_SENTRY_DSN),
};

/**
 * Example: API configuration object
 */
export const apiConfig = {
  baseUrl: requireEnv(
    typeof window !== 'undefined' ? env.NEXT_PUBLIC_API_URL : env.API_URL,
    'API_URL'
  ),
  timeout: isProduction ? 30000 : 60000, // 30s prod, 60s dev
  retryAttempts: isProduction ? 3 : 1,
};

// =============================================================================
// Type-Safe Optional Variable Handling
// =============================================================================

/**
 * Example: Safely accessing optional GitHub token
 */
export function getGitHubConfig() {
  const token = env.GITHUB_TOKEN;

  if (!isDefined(token)) {
    console.log('GitHub token not configured - using anonymous access');
    return { token: null, rateLimited: true };
  }

  return { token, rateLimited: false };
}

// =============================================================================
// Build-Time vs Runtime Validation
// =============================================================================

/**
 * NOTE: Next.js inlines NEXT_PUBLIC_* variables at BUILD TIME.
 *
 * This means:
 * 1. NEXT_PUBLIC_* vars must be set during `npm run build`
 * 2. Changing them after build requires rebuilding
 * 3. Use SKIP_ENV_VALIDATION=1 only during CI/CD builds if needed
 *
 * Server-side variables can be changed at runtime without rebuild.
 */
