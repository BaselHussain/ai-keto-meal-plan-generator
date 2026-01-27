'use client';

interface Step19PersonalTraitsProps {
  value: string[];
  onChange: (value: string[]) => void;
  error?: string;
}

export function Step19PersonalTraits({
  value,
  onChange,
  error,
}: Step19PersonalTraitsProps) {
  const traits = [
    {
      value: 'tired_waking_up',
      label: 'I often feel tired when waking up',
      icon: '😴',
    },
    {
      value: 'frequent_cravings',
      label: 'I experience frequent food cravings',
      icon: '🍫',
    },
    {
      value: 'prefer_salty',
      label: 'I prefer salty foods',
      icon: '🧂',
    },
    {
      value: 'prefer_sweet',
      label: 'I prefer sweet foods',
      icon: '🍰',
    },
    {
      value: 'struggle_appetite_control',
      label: 'I struggle with appetite control',
      icon: '🍽️',
    },
  ];

  const toggleTrait = (traitValue: string) => {
    const isSelected = value.includes(traitValue);

    if (isSelected) {
      onChange(value.filter((v) => v !== traitValue));
    } else {
      onChange([...value, traitValue]);
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl md:text-3xl font-bold text-gray-900">
          Personal Preferences
        </h2>
        <p className="text-gray-600">
          Help us personalize your meal plan (optional)
        </p>
        <p className="text-sm text-gray-500">
          Select any that apply
        </p>
      </div>

      <div className="space-y-3 mt-8">
        {traits.map((trait) => {
          const isSelected = value.includes(trait.value);

          return (
            <button
              key={trait.value}
              type="button"
              onClick={() => toggleTrait(trait.value)}
              className={`
                w-full p-4 rounded-lg border-2 transition-all duration-200 text-left
                ${
                  isSelected
                    ? 'border-green-500 bg-green-50 shadow-md'
                    : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
                }
              `}
              aria-pressed={isSelected}
              aria-label={`Toggle ${trait.label}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <span className="text-3xl" aria-hidden="true">
                    {trait.icon}
                  </span>
                  <span className="font-medium text-gray-900 text-base md:text-lg">
                    {trait.label}
                  </span>
                </div>
                {isSelected && (
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
          );
        })}
      </div>

      {value.length > 0 && (
        <div className="mt-4 text-center">
          <p className="text-sm font-medium text-green-600">
            {value.length} preference{value.length !== 1 ? 's' : ''} selected
          </p>
        </div>
      )}

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}
    </div>
  );
}
