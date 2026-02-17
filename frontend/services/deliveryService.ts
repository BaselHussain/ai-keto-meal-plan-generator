/**
 * Delivery Service
 *
 * Handles triggering the meal plan delivery pipeline (dev mode bypass).
 * In production, this would be triggered by Paddle payment webhook.
 * For testing, we use the dev endpoint that bypasses payment.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface TriggerDeliveryResponse {
  success: boolean;
  message: string;
  payment_id: string;
  delivery_status: string;
}

export class DeliveryServiceError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: string
  ) {
    super(message);
    this.name = 'DeliveryServiceError';
  }
}

/**
 * Trigger meal plan delivery via the dev endpoint.
 * This bypasses payment and directly starts AI generation -> PDF -> Email.
 *
 * @param quizId - Quiz response ID from submission
 * @param email - Email address for delivery
 * @returns TriggerDeliveryResponse with status
 */
export async function triggerDevDelivery(
  quizId: string,
  email: string
): Promise<TriggerDeliveryResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/v1/dev/trigger-delivery`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        quiz_id: quizId,
        email,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        detail: 'Failed to trigger delivery',
      }));

      throw new DeliveryServiceError(
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail)
      );
    }

    const data: TriggerDeliveryResponse = await response.json();
    return data;
  } catch (error) {
    if (error instanceof DeliveryServiceError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new DeliveryServiceError(
        'Network error. Please check your internet connection and try again.',
        0,
        'network_error'
      );
    }

    throw new DeliveryServiceError(
      'An unexpected error occurred. Please try again.',
      0,
      error instanceof Error ? error.message : 'unknown_error'
    );
  }
}
