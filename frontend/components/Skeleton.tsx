'use client';

import { motion } from 'framer-motion';

/**
 * Skeleton Components (T111)
 *
 * Reusable skeleton loader components for displaying loading states
 * while fetching meal plan data in the dashboard.
 *
 * Features:
 * - Shimmer animation effect
 * - Various prebuilt skeleton variants
 * - Composable for custom layouts
 */

interface SkeletonProps {
  /** Width of the skeleton (CSS value or Tailwind class) */
  width?: string;
  /** Height of the skeleton (CSS value or Tailwind class) */
  height?: string;
  /** Border radius (rounded-*) */
  rounded?: 'none' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
  /** Additional CSS classes */
  className?: string;
}

// Shimmer animation
const shimmerVariants = {
  animate: {
    backgroundPosition: ['200% 0', '-200% 0'],
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: 'linear' as const,
    },
  },
};

/**
 * Base Skeleton component with shimmer animation
 */
export function Skeleton({
  width = 'w-full',
  height = 'h-4',
  rounded = 'md',
  className = '',
}: SkeletonProps) {
  const roundedClass = rounded === 'none' ? '' : `rounded-${rounded}`;

  return (
    <motion.div
      variants={shimmerVariants}
      animate="animate"
      className={`bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 bg-[length:200%_100%] ${width} ${height} ${roundedClass} ${className}`}
      style={{
        backgroundSize: '200% 100%',
      }}
    />
  );
}

/**
 * Skeleton for text lines
 */
export function SkeletonText({
  lines = 3,
  className = '',
}: {
  lines?: number;
  className?: string;
}) {
  return (
    <div className={`space-y-3 ${className}`}>
      {[...Array(lines)].map((_, i) => (
        <Skeleton
          key={i}
          width={i === lines - 1 ? 'w-3/4' : 'w-full'}
          height="h-4"
        />
      ))}
    </div>
  );
}

/**
 * Skeleton for circular avatars
 */
export function SkeletonAvatar({
  size = 'md',
}: {
  size?: 'sm' | 'md' | 'lg' | 'xl';
}) {
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-16 h-16',
    xl: 'w-24 h-24',
  };

  return <Skeleton width={sizeClasses[size]} height="" rounded="full" />;
}

/**
 * Skeleton for card components
 */
export function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div
      className={`bg-white rounded-xl shadow-md p-6 space-y-4 ${className}`}
    >
      <div className="flex items-center gap-4">
        <SkeletonAvatar size="md" />
        <div className="flex-1 space-y-2">
          <Skeleton width="w-1/2" height="h-4" />
          <Skeleton width="w-1/3" height="h-3" />
        </div>
      </div>
      <SkeletonText lines={2} />
    </div>
  );
}

/**
 * Skeleton for meal plan day card
 */
export function SkeletonMealDay({ className = '' }: { className?: string }) {
  return (
    <div
      className={`bg-white rounded-xl shadow-md overflow-hidden ${className}`}
    >
      {/* Day header */}
      <div className="bg-gray-50 px-4 py-3 border-b border-gray-100">
        <Skeleton width="w-24" height="h-5" />
      </div>

      {/* Meals */}
      <div className="p-4 space-y-4">
        {['Breakfast', 'Lunch', 'Dinner'].map((meal) => (
          <div key={meal} className="space-y-2">
            <div className="flex items-center justify-between">
              <Skeleton width="w-20" height="h-4" />
              <Skeleton width="w-16" height="h-3" />
            </div>
            <Skeleton width="w-full" height="h-4" />
            <div className="flex gap-4">
              <Skeleton width="w-16" height="h-3" />
              <Skeleton width="w-16" height="h-3" />
              <Skeleton width="w-16" height="h-3" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Skeleton for shopping list
 */
export function SkeletonShoppingList({
  className = '',
}: {
  className?: string;
}) {
  return (
    <div
      className={`bg-white rounded-xl shadow-md p-6 space-y-4 ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <Skeleton width="w-32" height="h-6" />
        <Skeleton width="w-20" height="h-4" />
      </div>

      {/* Categories */}
      {[...Array(3)].map((_, i) => (
        <div key={i} className="space-y-2">
          <Skeleton width="w-24" height="h-4" />
          <div className="pl-4 space-y-2">
            {[...Array(4)].map((_, j) => (
              <div key={j} className="flex items-center gap-3">
                <Skeleton width="w-5" height="h-5" rounded="sm" />
                <Skeleton width="w-full" height="h-4" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Skeleton for macro nutrition display
 */
export function SkeletonMacros({ className = '' }: { className?: string }) {
  return (
    <div className={`flex gap-6 ${className}`}>
      {['Calories', 'Protein', 'Carbs', 'Fat'].map((macro) => (
        <div key={macro} className="text-center space-y-2">
          <Skeleton width="w-16" height="h-16" rounded="full" className="mx-auto" />
          <Skeleton width="w-12" height="h-3" className="mx-auto" />
          <Skeleton width="w-16" height="h-4" className="mx-auto" />
        </div>
      ))}
    </div>
  );
}

/**
 * Dashboard skeleton - full page loading state
 */
export function SkeletonDashboard() {
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton width="w-48" height="h-8" />
            <Skeleton width="w-32" height="h-4" />
          </div>
          <Skeleton width="w-32" height="h-10" rounded="lg" />
        </div>

        {/* Macros overview */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <Skeleton width="w-40" height="h-6" className="mb-6" />
          <SkeletonMacros />
        </div>

        {/* Week overview grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <SkeletonMealDay key={i} />
          ))}
        </div>

        {/* Shopping list */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonShoppingList />
          <SkeletonShoppingList />
        </div>
      </div>
    </div>
  );
}

/**
 * Inline skeleton for buttons/badges
 */
export function SkeletonButton({
  width = 'w-24',
  className = '',
}: {
  width?: string;
  className?: string;
}) {
  return <Skeleton width={width} height="h-10" rounded="lg" className={className} />;
}

/**
 * Table row skeleton
 */
export function SkeletonTableRow({ columns = 4 }: { columns?: number }) {
  return (
    <div className="flex items-center gap-4 py-3 border-b border-gray-100">
      {[...Array(columns)].map((_, i) => (
        <Skeleton
          key={i}
          width={i === 0 ? 'w-1/4' : 'flex-1'}
          height="h-4"
        />
      ))}
    </div>
  );
}

/**
 * Table skeleton
 */
export function SkeletonTable({
  rows = 5,
  columns = 4,
  className = '',
}: {
  rows?: number;
  columns?: number;
  className?: string;
}) {
  return (
    <div className={`bg-white rounded-xl shadow-md p-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center gap-4 pb-3 border-b-2 border-gray-200">
        {[...Array(columns)].map((_, i) => (
          <Skeleton
            key={i}
            width={i === 0 ? 'w-1/4' : 'flex-1'}
            height="h-5"
          />
        ))}
      </div>
      {/* Rows */}
      {[...Array(rows)].map((_, i) => (
        <SkeletonTableRow key={i} columns={columns} />
      ))}
    </div>
  );
}
