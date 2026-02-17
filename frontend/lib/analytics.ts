/**
 * Analytics and performance tracking utilities for the Keto Meal Plan Generator.
 *
 * Provides client-side analytics wrappers for:
 * - Quiz completion tracking (T136)
 * - Payment success tracking (T136)
 * - Page performance monitoring via Web Vitals (T136)
 * - API latency tracking for p95 budget enforcement (T136)
 *
 * All functions are no-ops when the browser does not support the required APIs
 * or when analytics are disabled. No PII is sent to Sentry from this module.
 *
 * Implements: T136
 */

import * as Sentry from '@sentry/nextjs';

// =============================================================================
// Types
// =============================================================================

export interface QuizCompletionEvent {
  /** Total number of steps completed in the quiz */
  totalSteps: number;
  /** Duration from first step to submission in milliseconds */
  durationMs: number;
  /** Whether the user had to redo any steps */
  hadRestarts: boolean;
}

export interface PaymentSuccessEvent {
  /** Paddle product ID (non-sensitive) */
  productId?: string;
  /** Time from checkout open to success confirmation in milliseconds */
  checkoutDurationMs?: number;
}

export interface PagePerformanceEvent {
  /** Route identifier (e.g., "/quiz", "/checkout") */
  route: string;
  /** Web Vital name: LCP, FID, CLS, FCP, TTFB, INP */
  metric: string;
  /** Metric value in appropriate unit (ms for time-based, unitless for CLS) */
  value: number;
  /** Web Vitals rating: "good", "needs-improvement", "poor" */
  rating?: 'good' | 'needs-improvement' | 'poor';
}

export interface APILatencyEvent {
  /** API endpoint path (e.g., "/api/v1/quiz") */
  endpoint: string;
  /** HTTP method */
  method: string;
  /** Response time in milliseconds */
  durationMs: number;
  /** HTTP status code */
  statusCode?: number;
}

// =============================================================================
// Constants
// =============================================================================

/** p95 latency budget per API category in milliseconds */
const LATENCY_BUDGETS: Record<string, number> = {
  '/api/v1/quiz': 500,         // Quiz submission: 500ms
  '/api/v1/payment': 1000,     // Payment: 1s
  '/api/v1/delivery': 3000,    // Delivery orchestration: 3s (long-running)
  default: 800,                 // General endpoints: 800ms
};

// =============================================================================
// Internal Helpers
// =============================================================================

/**
 * Resolve the p95 latency budget for a given endpoint.
 * Falls back to the 'default' budget when no specific budget is configured.
 */
function getLatencyBudget(endpoint: string): number {
  // Match by prefix to handle parameterised paths (e.g., /api/v1/quiz/123)
  for (const [prefix, budget] of Object.entries(LATENCY_BUDGETS)) {
    if (prefix !== 'default' && endpoint.startsWith(prefix)) {
      return budget;
    }
  }
  return LATENCY_BUDGETS['default'];
}

/**
 * Safe wrapper for Sentry calls that prevents analytics errors from
 * surfacing to users.
 */
function withSentrySafe(fn: () => void): void {
  try {
    fn();
  } catch {
    // Analytics failures must never affect the user experience
  }
}

// =============================================================================
// T136: Quiz Completion Tracking
// =============================================================================

/**
 * Track when a user successfully completes and submits the quiz.
 *
 * Records a Sentry breadcrumb and custom measurement for funnel analysis.
 * No PII (name, email) is included in the event.
 *
 * @param event - Quiz completion metadata
 *
 * @example
 * // In quiz submission handler:
 * await submitQuiz(formData);
 * trackQuizCompletion({
 *   totalSteps: 8,
 *   durationMs: performance.now() - quizStartTime,
 *   hadRestarts: false,
 * });
 */
export function trackQuizCompletion(event: QuizCompletionEvent): void {
  withSentrySafe(() => {
    Sentry.addBreadcrumb({
      category: 'quiz',
      message: 'Quiz completed and submitted',
      level: 'info',
      data: {
        totalSteps: event.totalSteps,
        durationMs: Math.round(event.durationMs),
        durationSeconds: Math.round(event.durationMs / 1000),
        hadRestarts: event.hadRestarts,
      },
    });

    Sentry.metrics.distribution(
      'quiz.completion.duration_ms',
      event.durationMs,
      {
        unit: 'millisecond',
        attributes: { had_restarts: String(event.hadRestarts) },
      }
    );

    Sentry.metrics.count('quiz.completions', 1, {
      attributes: { had_restarts: String(event.hadRestarts) },
    });
  });
}

// =============================================================================
// T136: Payment Success Tracking
// =============================================================================

/**
 * Track a successful payment confirmation from Paddle.
 *
 * Fires a Sentry breadcrumb and metric increment. Payment amounts and
 * card details are never tracked here — only success/failure counts
 * and checkout duration for UX analysis.
 *
 * @param event - Payment success metadata
 *
 * @example
 * // In Paddle success callback:
 * Paddle.Checkout.open({
 *   eventCallback: (data) => {
 *     if (data.event === 'Checkout.Complete') {
 *       trackPaymentSuccess({
 *         productId: data.eventData.product.id,
 *         checkoutDurationMs: performance.now() - checkoutOpenTime,
 *       });
 *     }
 *   },
 * });
 */
export function trackPaymentSuccess(event: PaymentSuccessEvent): void {
  withSentrySafe(() => {
    Sentry.addBreadcrumb({
      category: 'payment',
      message: 'Payment completed successfully',
      level: 'info',
      data: {
        productId: event.productId,
        checkoutDurationMs: event.checkoutDurationMs != null
          ? Math.round(event.checkoutDurationMs)
          : undefined,
      },
    });

    Sentry.metrics.count('payment.success', 1, {
      attributes: { product_id: event.productId || 'unknown' },
    });

    if (event.checkoutDurationMs != null) {
      Sentry.metrics.distribution(
        'payment.checkout.duration_ms',
        event.checkoutDurationMs,
        { unit: 'millisecond' }
      );
    }
  });
}

// =============================================================================
// T136: Page Performance Monitoring
// =============================================================================

/**
 * Track a Web Vital measurement for a page route.
 *
 * Designed to be used as the `reportWebVitals` callback in Next.js
 * or called directly after measuring with the `web-vitals` package.
 *
 * @param event - Page performance metric
 *
 * @example
 * // In pages/_app.tsx or app/layout.tsx:
 * export function reportWebVitals(metric: NextWebVitalsMetric) {
 *   trackPagePerformance({
 *     route: window.location.pathname,
 *     metric: metric.name,
 *     value: metric.value,
 *     rating: metric.rating,
 *   });
 * }
 */
export function trackPagePerformance(event: PagePerformanceEvent): void {
  withSentrySafe(() => {
    const { route, metric, value, rating } = event;

    Sentry.addBreadcrumb({
      category: 'performance',
      message: `Web Vital: ${metric}`,
      level: rating === 'poor' ? 'warning' : 'info',
      data: {
        route,
        metric,
        value: Math.round(value * 100) / 100,
        rating,
      },
    });

    // Route metric name to the right Sentry measurement type
    const metricName = `web_vital.${metric.toLowerCase()}.${route.replace(/\//g, '_').replace(/^_/, '')}`;

    Sentry.metrics.distribution(
      metricName,
      value,
      {
        unit: metric === 'CLS' ? 'none' : 'millisecond',
        attributes: {
          route,
          metric,
          rating: rating || 'unknown',
        },
      }
    );

    // Log poor vitals as Sentry events for easy alerting
    if (rating === 'poor') {
      Sentry.captureMessage(
        `Poor Web Vital: ${metric} = ${Math.round(value)} on ${route}`,
        'warning'
      );
    }
  });
}

// =============================================================================
// T136: API Latency Tracking
// =============================================================================

/**
 * Track API response latency against the p95 budget for the endpoint.
 *
 * When latency exceeds the configured budget, a Sentry 'warning' is captured
 * to alert on SLO breaches before they impact users at scale.
 *
 * @param event - API latency measurement
 *
 * @example
 * const start = performance.now();
 * const response = await fetch('/api/v1/quiz', { method: 'POST', body });
 * trackAPILatency({
 *   endpoint: '/api/v1/quiz',
 *   method: 'POST',
 *   durationMs: performance.now() - start,
 *   statusCode: response.status,
 * });
 */
export function trackAPILatency(event: APILatencyEvent): void {
  withSentrySafe(() => {
    const { endpoint, method, durationMs, statusCode } = event;
    const budget = getLatencyBudget(endpoint);
    const exceededBudget = durationMs > budget;

    Sentry.addBreadcrumb({
      category: 'api',
      message: `${method} ${endpoint} — ${Math.round(durationMs)}ms`,
      level: exceededBudget ? 'warning' : 'info',
      data: {
        endpoint,
        method,
        durationMs: Math.round(durationMs),
        statusCode,
        budget,
        exceededBudget,
      },
    });

    Sentry.metrics.distribution(
      'api.latency_ms',
      durationMs,
      {
        unit: 'millisecond',
        attributes: {
          endpoint,
          method,
          status_code: String(statusCode || 'unknown'),
          exceeded_budget: String(exceededBudget),
        },
      }
    );

    if (exceededBudget) {
      Sentry.captureMessage(
        `API latency budget exceeded: ${method} ${endpoint} took ${Math.round(durationMs)}ms (budget: ${budget}ms)`,
        'warning'
      );
    }
  });
}

// =============================================================================
// Convenience: Timing Wrapper
// =============================================================================

/**
 * Wrap an async API call with automatic latency tracking.
 *
 * Returns the original response unchanged while side-effecting the
 * analytics event.
 *
 * @param fn - Async function that returns a Response
 * @param endpoint - Endpoint path for latency budget lookup
 * @param method - HTTP method string
 * @returns The original Response from fn
 *
 * @example
 * const response = await withLatencyTracking(
 *   () => fetch('/api/v1/quiz', { method: 'POST', body }),
 *   '/api/v1/quiz',
 *   'POST',
 * );
 */
export async function withLatencyTracking(
  fn: () => Promise<Response>,
  endpoint: string,
  method: string
): Promise<Response> {
  const start = performance.now();
  let statusCode: number | undefined;

  try {
    const response = await fn();
    statusCode = response.status;
    return response;
  } finally {
    const durationMs = performance.now() - start;
    trackAPILatency({ endpoint, method, durationMs, statusCode });
  }
}
