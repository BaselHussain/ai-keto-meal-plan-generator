/**
 * Dashboard Service
 * Handles API communication for authenticated user dashboard
 * Following Phase 7.4 requirements: meal plan retrieval and download management
 */

// API Response Types
export interface MealPlan {
  id: string;
  created_at: string;
  pdf_available: boolean;
  expires_at: string; // 90 days from created_at
}

export interface MealPlansResponse {
  meal_plans: MealPlan[];
}

// Error Response Type
interface DashboardErrorResponse {
  detail: {
    code: string;
    message: string;
  };
}

// Custom Error Class
export class DashboardServiceError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public code?: string
  ) {
    super(message);
    this.name = 'DashboardServiceError';
  }
}

// API Base URL (uses Next.js API proxy)
const API_BASE_URL = '/api/v1';

/**
 * Get authenticated user's meal plans
 * GET /api/v1/meal-plans/me
 *
 * Requires Authentication: Bearer token
 *
 * @param accessToken JWT access token from localStorage
 * @returns MealPlansResponse with array of meal plans
 * @throws DashboardServiceError on failure (401 unauthorized, network error, etc.)
 */
export async function getMealPlans(
  accessToken: string
): Promise<MealPlansResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/meal-plans/me`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      // Handle HTTP errors
      if (response.status === 401) {
        throw new DashboardServiceError(
          'Authentication required. Please login again.',
          401,
          'UNAUTHORIZED'
        );
      }

      const errorData: DashboardErrorResponse = await response
        .json()
        .catch(() => ({
          detail: {
            code: 'unknown_error',
            message: 'Failed to fetch meal plans',
          },
        }));

      const detail = errorData.detail || {
        code: 'unknown_error',
        message: 'Unknown error',
      };

      throw new DashboardServiceError(
        detail.message || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        detail.code
      );
    }

    const data: MealPlansResponse = await response.json();
    return data;
  } catch (error) {
    // Handle network errors and other exceptions
    if (error instanceof DashboardServiceError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new DashboardServiceError(
        'Network error. Please check your internet connection and try again.',
        0,
        'network_error'
      );
    }

    // Unknown error
    throw new DashboardServiceError(
      'An unexpected error occurred. Please try again.',
      500,
      'unknown_error'
    );
  }
}

/**
 * Download meal plan PDF
 * GET /api/v1/download-pdf?meal_plan_id={id}
 *
 * Requires Authentication: Bearer token
 *
 * @param mealPlanId Meal plan ID to download
 * @param accessToken JWT access token from localStorage
 * @returns Blob containing PDF file
 * @throws DashboardServiceError on failure (401, 404, network error, etc.)
 */
export async function downloadMealPlanPDF(
  mealPlanId: string,
  accessToken: string
): Promise<Blob> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/download-pdf?meal_plan_id=${encodeURIComponent(mealPlanId)}`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      }
    );

    if (!response.ok) {
      // Handle HTTP errors
      if (response.status === 401) {
        throw new DashboardServiceError(
          'Authentication required. Please login again.',
          401,
          'UNAUTHORIZED'
        );
      }

      if (response.status === 404) {
        throw new DashboardServiceError(
          'Meal plan not found or PDF not available.',
          404,
          'NOT_FOUND'
        );
      }

      throw new DashboardServiceError(
        `Download failed: ${response.statusText}`,
        response.status,
        'DOWNLOAD_FAILED'
      );
    }

    // Get PDF blob
    const blob = await response.blob();
    return blob;
  } catch (error) {
    // Handle network errors and other exceptions
    if (error instanceof DashboardServiceError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new DashboardServiceError(
        'Network error. Please check your internet connection and try again.',
        0,
        'network_error'
      );
    }

    // Unknown error
    throw new DashboardServiceError(
      'Failed to download PDF. Please try again.',
      500,
      'unknown_error'
    );
  }
}

/**
 * Calculate days remaining until expiry
 *
 * @param expiresAt ISO timestamp when meal plan expires
 * @returns Number of days remaining (0 if expired)
 */
export function calculateDaysRemaining(expiresAt: string): number {
  try {
    const expiry = new Date(expiresAt);
    const now = new Date();
    const diffMs = expiry.getTime() - now.getTime();
    const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
    return Math.max(0, diffDays); // Return 0 if expired
  } catch {
    return 0;
  }
}

/**
 * Get retention status color based on days remaining
 *
 * @param daysRemaining Number of days until expiry
 * @returns Color class ('green' | 'yellow' | 'red')
 */
export function getRetentionStatusColor(
  daysRemaining: number
): 'green' | 'yellow' | 'red' {
  if (daysRemaining > 30) return 'green';
  if (daysRemaining >= 7) return 'yellow';
  return 'red';
}

/**
 * Format date for display
 *
 * @param dateString ISO date string
 * @returns Formatted date string (e.g., "January 26, 2026")
 */
export function formatDate(dateString: string): string {
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  } catch {
    return dateString;
  }
}
