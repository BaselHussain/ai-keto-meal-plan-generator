'use client';

import { MdRestaurant, MdFastfood, MdDinnerDining } from 'react-icons/md';

interface Step18MealFrequencyProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
}

export function Step18MealFrequency({
  value,
  onChange,
  error,
}: Step18MealFrequencyProps) {
  const frequencies = [
    {
      value: '2_meals',
      label: '2 Meals Per Day',
      description: 'Intermittent fasting style',
      icon: <MdRestaurant className="text-green-600" />,
    },
    {
      value: '3_meals',
      label: '3 Meals Per Day',
      description: 'Traditional eating pattern',
      icon: <MdFastfood className="text-green-600" />,
    },
    {
      value: '4_meals',
      label: '4 Meals Per Day',
      description: 'Frequent smaller meals',
      icon: <MdDinnerDining className="text-green-600" />,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl md:text-3xl font-bold text-gray-900">
          How many meals per day?
        </h2>
        <p className="text-gray-600">
          Choose your preferred eating frequency
        </p>
      </div>

      <div className="space-y-3 mt-8">
        {frequencies.map((frequency) => (
          <button
            key={frequency.value}
            type="button"
            onClick={() => onChange(frequency.value)}
            className={`
              w-full p-5 rounded-lg border-2 transition-all duration-200 text-left
              ${
                value === frequency.value
                  ? 'border-green-500 bg-green-50 shadow-md'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
              }
            `}
            aria-pressed={value === frequency.value}
            aria-label={`Select ${frequency.label}`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="text-4xl">{frequency.icon}</div>
                <div className="flex-1">
                  <div className="font-semibold text-gray-900 text-lg">
                    {frequency.label}
                  </div>
                  <p className="text-sm text-gray-600 mt-1">
                    {frequency.description}
                  </p>
                </div>
              </div>
              {value === frequency.value && (
                <svg
                  className="w-6 h-6 text-green-500 flex-shrink-0"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  aria-hidden="true"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </div>
          </button>
        ))}
      </div>

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}
    </div>
  );
}
