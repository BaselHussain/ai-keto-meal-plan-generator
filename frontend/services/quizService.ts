import { CompleteQuizData } from '../lib/validations/quiz/steps';

/**
 * Quiz submission service
 * Handles API communication for quiz data submission
 * Following frontend-quiz-engineer.md guidelines for error handling
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
