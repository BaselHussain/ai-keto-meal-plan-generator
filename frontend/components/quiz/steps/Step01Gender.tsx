'use client';

interface Step01GenderProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
}

export function Step01Gender({ value, onChange, error }: Step01GenderProps) {
  const options = [
    { value: 'male', label: 'Male', icon: '♂️' },
    { value: 'female', label: 'Female', icon: '♀️' },
  ];

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl md:text-3xl font-bold text-gray-900">
          What's your gender?
        </h2>
        <p className="text-gray-600">
          This helps us calculate your daily calorie needs
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-8">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={`
              relative p-6 rounded-xl border-2 transition-all duration-200
              ${
                value === option.value
                  ? 'border-green-500 bg-green-50 shadow-md'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
              }
            `}
            aria-pressed={value === option.value}
          >
            <div className="flex flex-col items-center space-y-3">
              <span className="text-4xl">{option.icon}</span>
              <span className="text-lg font-semibold text-gray-900">
                {option.label}
              </span>
            </div>
            {value === option.value && (
              <div className="absolute top-3 right-3">
                <svg
                  className="w-6 h-6 text-green-500"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
            )}
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
