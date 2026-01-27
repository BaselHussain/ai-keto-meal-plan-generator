'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  getMealPlans,
  downloadMealPlanPDF,
  calculateDaysRemaining,
  getRetentionStatusColor,
  formatDate,
  DashboardServiceError,
  type MealPlan,
} from '@/services/dashboardService';
import { getAccessToken, clearAccessToken } from '@/services/authService';
import { Skeleton } from '@/components/Skeleton';

/**
 * Dashboard Page Component (T103-T104)
 *
 * Protected route showing user's meal plans with download management.
 *
 * Route: /dashboard
 *
 * Features:
 * - Protected route (requires authentication)
 * - Show user's meal plan details (created date, email)
 * - PDF download button
 * - Expiry countdown (days remaining of 90-day retention)
 * - Mobile-first responsive design
 * - Loading skeleton while fetching data
 * - Error handling for API failures
 *
 * T104 - Download availability status:
 * - Show "X days remaining of 90-day retention"
 * - Visual progress bar showing retention period
 * - Warning when < 7 days remaining
 * - "Expired" state if past 90 days
 *
 * Reference:
 *   Phase 7.4 - Account Dashboard (T103-T104)
 *   specs/001-keto-meal-plan-generator/tasks.md
 */

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: 'easeOut' },
  },
};

const cardVariants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.3 },
  },
  hover: {
    y: -4,
    boxShadow: '0 20px 40px -10px rgba(0, 0, 0, 0.15)',
    transition: { duration: 0.2 },
  },
};

type PageState = 'loading' | 'success' | 'error' | 'empty';

export default function DashboardPage() {
  const router = useRouter();
  const [pageState, setPageState] = useState<PageState>('loading');
  const [mealPlans, setMealPlans] = useState<MealPlan[]>([]);
  const [error, setError] = useState<string>('');
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  useEffect(() => {
    // Check authentication
    const token = getAccessToken();
    if (!token) {
      // Redirect to login if not authenticated
      router.push('/create-account?redirect=/dashboard');
      return;
    }

    // Fetch meal plans
    async function fetchMealPlans() {
      try {
        const token = getAccessToken();
        if (!token) {
          throw new DashboardServiceError('No access token', 401, 'UNAUTHORIZED');
        }

        const data = await getMealPlans(token);

        if (!data.meal_plans || data.meal_plans.length === 0) {
          setPageState('empty');
        } else {
          setMealPlans(data.meal_plans);
          setPageState('success');
        }
      } catch (err) {
        setPageState('error');

        if (err instanceof DashboardServiceError) {
          if (err.code === 'UNAUTHORIZED') {
            // Clear token and redirect to login
            clearAccessToken();
            router.push('/create-account?redirect=/dashboard');
            return;
          }
          setError(err.message);
        } else {
          setError('Failed to load meal plans. Please try again.');
        }
      }
    }

    fetchMealPlans();
  }, [router]);

  // Handle logout
  const handleLogout = () => {
    clearAccessToken();
    router.push('/');
  };

  // Handle download
  const handleDownload = async (mealPlan: MealPlan) => {
    const token = getAccessToken();
    if (!token) {
      router.push('/create-account?redirect=/dashboard');
      return;
    }

    setDownloadingId(mealPlan.id);

    try {
      const blob = await downloadMealPlanPDF(mealPlan.id, token);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `keto-meal-plan-${mealPlan.id.substring(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();

      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      if (err instanceof DashboardServiceError) {
        if (err.code === 'UNAUTHORIZED') {
          clearAccessToken();
          router.push('/create-account?redirect=/dashboard');
          return;
        }
        alert(err.message);
      } else {
        alert('Failed to download PDF. Please try again.');
      }
    } finally {
      setDownloadingId(null);
    }
  };

  // Render meal plan card
  const renderMealPlanCard = (mealPlan: MealPlan) => {
    const daysRemaining = calculateDaysRemaining(mealPlan.expires_at);
    const statusColor = getRetentionStatusColor(daysRemaining);
    const isExpired = daysRemaining === 0;
    const isDownloading = downloadingId === mealPlan.id;

    // Calculate retention progress (0-100%)
    const totalDays = 90;
    const progress = ((totalDays - daysRemaining) / totalDays) * 100;

    return (
      <motion.div
        key={mealPlan.id}
        variants={cardVariants}
        initial="hidden"
        animate="visible"
        whileHover="hover"
        className="bg-white rounded-xl shadow-lg overflow-hidden border border-gray-100"
      >
        <div className="p-6">
          {/* Header: Created date and status badge */}
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">
                Keto Meal Plan
              </h3>
              <p className="text-sm text-gray-600">
                Created {formatDate(mealPlan.created_at)}
              </p>
            </div>
            <div
              className={`px-3 py-1 rounded-full text-xs font-medium ${
                statusColor === 'green'
                  ? 'bg-green-100 text-green-700'
                  : statusColor === 'yellow'
                  ? 'bg-yellow-100 text-yellow-700'
                  : 'bg-red-100 text-red-700'
              }`}
            >
              {isExpired ? 'Expired' : `${daysRemaining} days left`}
            </div>
          </div>

          {/* Retention progress bar (T104) */}
          <div className="mb-4">
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="text-gray-600">Retention Period</span>
              <span className="font-medium text-gray-900">
                {isExpired ? 'Expired' : `${daysRemaining} / 90 days`}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 1, ease: 'easeOut', delay: 0.3 }}
                className={`h-full rounded-full ${
                  statusColor === 'green'
                    ? 'bg-green-500'
                    : statusColor === 'yellow'
                    ? 'bg-yellow-500'
                    : 'bg-red-500'
                }`}
              />
            </div>
          </div>

          {/* Warning message for expiring plans */}
          {!isExpired && daysRemaining < 7 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mb-4 bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800"
            >
              <div className="flex items-start gap-2">
                <svg
                  className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
                <div>
                  <p className="font-medium">Expiring Soon</p>
                  <p className="mt-0.5">
                    Download your meal plan before it expires in {daysRemaining} day
                    {daysRemaining === 1 ? '' : 's'}.
                  </p>
                </div>
              </div>
            </motion.div>
          )}

          {/* Expired message */}
          {isExpired && (
            <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-800">
              <p className="font-medium">Plan Expired</p>
              <p className="mt-0.5">
                This meal plan has expired. Plans are available for 90 days.
              </p>
            </div>
          )}

          {/* Plan details */}
          <div className="bg-gray-50 rounded-lg p-4 mb-4">
            <h4 className="font-medium text-gray-900 mb-3">What's Included</h4>
            <ul className="space-y-2 text-sm text-gray-600">
              <li className="flex items-center gap-2">
                <svg
                  className="w-4 h-4 text-green-500 flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                30 days of keto meals
              </li>
              <li className="flex items-center gap-2">
                <svg
                  className="w-4 h-4 text-green-500 flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                90 recipes (breakfast, lunch, dinner)
              </li>
              <li className="flex items-center gap-2">
                <svg
                  className="w-4 h-4 text-green-500 flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                4 weekly shopping lists
              </li>
              <li className="flex items-center gap-2">
                <svg
                  className="w-4 h-4 text-green-500 flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                Complete macro breakdown
              </li>
            </ul>
          </div>

          {/* Download button */}
          {mealPlan.pdf_available && !isExpired ? (
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => handleDownload(mealPlan)}
              disabled={isDownloading}
              className="w-full bg-gradient-to-r from-green-500 to-green-600 text-white font-semibold py-3 px-6 rounded-lg hover:from-green-600 hover:to-green-700 transition-colors duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isDownloading ? (
                <>
                  <svg
                    className="animate-spin h-5 w-5"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  <span>Downloading...</span>
                </>
              ) : (
                <>
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                    />
                  </svg>
                  <span>Download PDF</span>
                </>
              )}
            </motion.button>
          ) : (
            <button
              disabled
              className="w-full bg-gray-300 text-gray-500 font-semibold py-3 px-6 rounded-lg cursor-not-allowed"
            >
              {isExpired ? 'Plan Expired' : 'PDF Not Available'}
            </button>
          )}
        </div>
      </motion.div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">My Dashboard</h1>
              <p className="text-sm text-gray-600 mt-1">
                Manage your keto meal plans
              </p>
            </div>
            <button
              onClick={handleLogout}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <AnimatePresence mode="wait">
          {/* Loading State */}
          {pageState === 'loading' && (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
            >
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="bg-white rounded-xl shadow-lg p-6 space-y-4"
                >
                  <div className="flex items-start justify-between">
                    <div className="space-y-2 flex-1">
                      <Skeleton width="w-3/4" height="h-5" />
                      <Skeleton width="w-1/2" height="h-4" />
                    </div>
                    <Skeleton width="w-20" height="h-6" rounded="full" />
                  </div>
                  <div className="space-y-2">
                    <Skeleton width="w-full" height="h-4" />
                    <Skeleton width="w-full" height="h-2" />
                  </div>
                  <div className="space-y-2">
                    {[1, 2, 3, 4].map((j) => (
                      <Skeleton key={j} width="w-full" height="h-4" />
                    ))}
                  </div>
                  <Skeleton width="w-full" height="h-12" rounded="lg" />
                </div>
              ))}
            </motion.div>
          )}

          {/* Success State */}
          {pageState === 'success' && (
            <motion.div
              key="success"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
            >
              {mealPlans.map((mealPlan) => renderMealPlanCard(mealPlan))}
            </motion.div>
          )}

          {/* Empty State */}
          {pageState === 'empty' && (
            <motion.div
              key="empty"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="max-w-md mx-auto bg-white rounded-2xl shadow-xl p-8 text-center"
            >
              <div className="w-24 h-24 mx-auto mb-6 bg-gray-100 rounded-full flex items-center justify-center">
                <svg
                  className="w-12 h-12 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                No Meal Plans Yet
              </h2>
              <p className="text-gray-600 mb-6">
                You haven't created any meal plans yet. Take our quiz to generate
                your personalized keto meal plan.
              </p>
              <a
                href="/"
                className="inline-block bg-gradient-to-r from-green-500 to-green-600 text-white font-semibold py-3 px-6 rounded-lg hover:from-green-600 hover:to-green-700 transition-colors"
              >
                Start Quiz
              </a>
            </motion.div>
          )}

          {/* Error State */}
          {pageState === 'error' && (
            <motion.div
              key="error"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="max-w-md mx-auto bg-white rounded-2xl shadow-xl p-8 text-center"
            >
              <div className="w-24 h-24 mx-auto mb-6 bg-red-100 rounded-full flex items-center justify-center">
                <svg
                  className="w-12 h-12 text-red-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Failed to Load
              </h2>
              <p className="text-gray-600 mb-6">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="bg-gradient-to-r from-green-500 to-green-600 text-white font-semibold py-3 px-6 rounded-lg hover:from-green-600 hover:to-green-700 transition-colors"
              >
                Try Again
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
