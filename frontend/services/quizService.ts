import { CompleteQuizData } from '../lib/validations/quiz/steps';
import { QuizData } from '../hooks/useQuizState';
import { getAccessToken } from './authService';

/**
 * Quiz submission service
 * Handles API communication for quiz data submission and progress saving
 * Following frontend-quiz-engineer.md guidelines for error handling
 *
 * Features:
 * - Quiz submission (unauthenticated and authenticated)
 * - Incremental quiz progress saves (T113 - authenticated users only)
 * - Cross-device resume (T114 - load saved progress on login)
 */

interface QuizSubmissionResponse {
  success: boolean;
  quiz_id: string;
  calorie_target: number;
  message?: string;
}

interface QuizSubmissionError {
  error: string;
  details?: string;
  field?: string;
}

class QuizServiceError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: string
  ) {
    super(message);
    this.name = 'QuizServiceError';
  }
}

/**
 * Submit quiz data to backend
 * POST /api/quiz/submit
 */
export async function submitQuiz(
  quizData: CompleteQuizData,
  email: string
): Promise<QuizSubmissionResponse> {
  try {
    const response = await fetch('/api/quiz/submit', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        quiz_data: quizData,
      }),
    });

    if (!response.ok) {
      // Handle HTTP errors
      const errorData: QuizSubmissionError = await response.json().catch(() => ({
        error: 'Failed to submit quiz',
      }));

      throw new QuizServiceError(
        errorData.error || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        errorData.details
      );
    }

    const data: QuizSubmissionResponse = await response.json();
    return data;
  } catch (error) {
    // Handle network errors and other exceptions
    if (error instanceof QuizServiceError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new QuizServiceError(
        'Network error. Please check your internet connection and try again.',
        0,
        'fetch_failed'
      );
    }

    throw new QuizServiceError(
      'An unexpected error occurred. Please try again.',
      0,
      error instanceof Error ? error.message : 'unknown_error'
    );
  }
}

/**
 * Submit quiz with retry logic (for network resilience)
 * Retries up to 2 times with exponential backoff
 */
export async function submitQuizWithRetry(
  quizData: CompleteQuizData,
  email: string,
  maxRetries: number = 2
): Promise<QuizSubmissionResponse> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await submitQuiz(quizData, email);
    } catch (error) {
      lastError = error as Error;

      // Don't retry on client errors (400-499)
      if (
        error instanceof QuizServiceError &&
        error.statusCode &&
        error.statusCode >= 400 &&
        error.statusCode < 500
      ) {
        throw error;
      }

      // Don't retry on last attempt
      if (attempt === maxRetries) {
        break;
      }

      // Exponential backoff: 1s, 2s
      const delayMs = Math.pow(2, attempt) * 1000;
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }

  throw lastError || new QuizServiceError('Failed to submit quiz after multiple attempts');
}

/**
 * Validate quiz data before submission (client-side pre-check)
 */
export function validateQuizBeforeSubmission(quizData: CompleteQuizData): {
  valid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  // Check required fields
  if (!quizData.step_1) {
    errors.push('Gender is required');
  }

  if (!quizData.step_2) {
    errors.push('Activity level is required');
  }

  if (!quizData.step_20 || !quizData.step_20.goal) {
    errors.push('Fitness goal is required');
  }

  if (!quizData.step_20 || quizData.step_20.age === 0) {
    errors.push('Age is required');
  }

  if (!quizData.step_20 || quizData.step_20.weight_kg === 0) {
    errors.push('Weight is required');
  }

  if (!quizData.step_20 || quizData.step_20.height_cm === 0) {
    errors.push('Height is required');
  }

  // Check food items minimum (FR-Q-017)
  const totalFoodItems = [
    ...quizData.step_3,
    ...quizData.step_4,
    ...quizData.step_5,
    ...quizData.step_6,
    ...quizData.step_7,
    ...quizData.step_8,
    ...quizData.step_9,
    ...quizData.step_10,
    ...quizData.step_11,
    ...quizData.step_12,
    ...quizData.step_13,
    ...quizData.step_14,
    ...quizData.step_15,
    ...quizData.step_16,
  ].length;

  if (totalFoodItems < 10) {
    errors.push(`Please select at least 10 food items (currently: ${totalFoodItems})`);
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * Get user-friendly error message from QuizServiceError
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof QuizServiceError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'An unexpected error occurred. Please try again.';
}

export { QuizServiceError };

/**
 * =============================================================================
 * QUIZ PROGRESS SAVING (T113, T114)
 * =============================================================================
 */

// Save Progress Response
export interface SaveProgressResponse {
  success: boolean;
  saved_at: string;
  current_step: number;
}

// Load Progress Response
export interface LoadProgressResponse {
  quiz_data: Partial<QuizData>;
  current_step: number;
  saved_at: string;
}

/**
 * Save quiz progress to backend for authenticated users (T113).
 *
 * This enables cross-device sync and recovery. Only works for authenticated users
 * with valid access token. Unauthenticated users continue using localStorage.
 *
 * @param currentStep - Current quiz step (1-20)
 * @param quizData - Partial or complete quiz data to save
 * @returns SaveProgressResponse with success status and timestamp
 * @throws QuizServiceError on failure (network, auth, validation)
 *
 * Example:
 *   const result = await saveQuizProgress(10, {
 *     step_1: 'female',
 *     step_2: 'moderately_active',
 *     step_3: ['chicken', 'turkey'],
 *     // ... partial data up to step 10
 *   });
 *   console.log(`Saved at ${result.saved_at}`);
 */
export async function saveQuizProgress(
  currentStep: number,
  quizData: Partial<QuizData>
): Promise<SaveProgressResponse> {
  // Get access token from localStorage
  const accessToken = getAccessToken();

  if (!accessToken) {
    throw new QuizServiceError(
      'Not authenticated. Please log in to save progress.',
      401,
      'not_authenticated'
    );
  }

  try {
    const response = await fetch('/api/v1/quiz/save-progress', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        current_step: currentStep,
        quiz_data: quizData,
      }),
    });

    if (!response.ok) {
      // Handle HTTP errors
      const errorData: QuizSubmissionError = await response
        .json()
        .catch(() => ({
          error: 'Failed to save quiz progress',
        }));

      // Special handling for authentication errors
      if (response.status === 401) {
        throw new QuizServiceError(
          'Your session has expired. Please log in again.',
          401,
          'session_expired'
        );
      }

      throw new QuizServiceError(
        errorData.error || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        errorData.details
      );
    }

    const data: SaveProgressResponse = await response.json();
    return data;
  } catch (error) {
    // Handle network errors and other exceptions
    if (error instanceof QuizServiceError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new QuizServiceError(
        'Network error. Please check your internet connection and try again.',
        0,
        'network_error'
      );
    }

    // Unknown error
    throw new QuizServiceError(
      'An unexpected error occurred while saving progress. Please try again.',
      500,
      'unknown_error'
    );
  }
}

/**
 * Load saved quiz progress from backend for authenticated users (T114).
 *
 * Enables cross-device resume. Called on authenticated user login to restore
 * their last saved quiz state.
 *
 * @returns LoadProgressResponse with quiz data and current step, or null if no saved progress
 * @throws QuizServiceError on failure (network, auth)
 *
 * Example:
 *   const savedProgress = await loadQuizProgress();
 *   if (savedProgress) {
 *     form.reset(savedProgress.quiz_data);
 *     setCurrentStep(savedProgress.current_step);
 *   }
 */
export async function loadQuizProgress(): Promise<LoadProgressResponse | null> {
  // Get access token from localStorage
  const accessToken = getAccessToken();

  if (!accessToken) {
    throw new QuizServiceError(
      'Not authenticated. Please log in to load progress.',
      401,
      'not_authenticated'
    );
  }

  try {
    const response = await fetch('/api/v1/quiz/load-progress', {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    // 404 means no saved progress (this is expected, not an error)
    if (response.status === 404) {
      return null;
    }

    if (!response.ok) {
      // Handle HTTP errors
      const errorData: QuizSubmissionError = await response
        .json()
        .catch(() => ({
          error: 'Failed to load quiz progress',
        }));

      // Special handling for authentication errors
      if (response.status === 401) {
        throw new QuizServiceError(
          'Your session has expired. Please log in again.',
          401,
          'session_expired'
        );
      }

      throw new QuizServiceError(
        errorData.error || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        errorData.details
      );
    }

    const data: LoadProgressResponse = await response.json();
    return data;
  } catch (error) {
    // Handle network errors and other exceptions
    if (error instanceof QuizServiceError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new QuizServiceError(
        'Network error. Please check your internet connection and try again.',
        0,
        'network_error'
      );
    }

    // Unknown error
    throw new QuizServiceError(
      'An unexpected error occurred while loading progress. Please try again.',
      500,
      'unknown_error'
    );
  }
}
