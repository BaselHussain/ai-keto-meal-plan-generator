'use client';

interface Step02ActivityProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
}

export function Step02Activity({ value, onChange, error }: Step02ActivityProps) {
  const activityLevels = [
    {
      value: 'sedentary',
      label: 'Sedentary',
      description: 'Little or no exercise, desk job',
      icon: '🪑',
      multiplier: '1.2',
    },
    {
      value: 'lightly_active',
      label: 'Lightly Active',
      description: 'Light exercise 1-3 days/week',
      icon: '🚶',
      multiplier: '1.375',
    },
    {
      value: 'moderately_active',
      label: 'Moderately Active',
      description: 'Moderate exercise 3-5 days/week',
      icon: '🏃',
      multiplier: '1.55',
    },
    {
      value: 'very_active',
      label: 'Very Active',
      description: 'Hard exercise 6-7 days/week',
      icon: '💪',
      multiplier: '1.725',
    },
    {
      value: 'super_active',
      label: 'Super Active',
      description: 'Very hard exercise, physical job or training',
      icon: '🏋️',
      multiplier: '1.9',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl md:text-3xl font-bold text-gray-900">
          What's your activity level?
        </h2>
        <p className="text-gray-600">
          This helps us calculate your daily calorie needs
        </p>
      </div>

      <div className="space-y-3 mt-8">
        {activityLevels.map((level) => (
          <button
            key={level.value}
            type="button"
            onClick={() => onChange(level.value)}
            className={`
              w-full p-4 rounded-lg border-2 transition-all duration-200 text-left
              ${
                value === level.value
                  ? 'border-green-500 bg-green-50 shadow-md'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
              }
            `}
            aria-pressed={value === level.value}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <span className="text-3xl">{level.icon}</span>
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-gray-900">
                      {level.label}
                    </span>
                    <span className="text-sm text-gray-500">
                      (×{level.multiplier})
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">
                    {level.description}
                  </p>
                </div>
              </div>
              {value === level.value && (
                <svg
                  className="w-6 h-6 text-green-500 flex-shrink-0"
                  fill="currentColor"
                  viewBox="0 0 20 20"
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
