'use client';

interface Step17RestrictionsProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
}

export function Step17Restrictions({ value, onChange, error }: Step17RestrictionsProps) {
  const maxLength = 500;
  const remainingChars = maxLength - value.length;

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <div className="text-center space-y-2">
        <h2 className="text-2xl md:text-3xl font-bold text-gray-900">
          Any dietary restrictions?
        </h2>
        <p className="text-gray-600">
          Tell us about allergies, intolerances, or foods you want to avoid
        </p>
      </div>

      {/* Privacy Warning - FR-Q-004 */}
      <div className="p-4 bg-yellow-50 border-2 border-yellow-300 rounded-lg">
        <div className="flex items-start space-x-3">
          <svg
            className="w-6 h-6 text-yellow-600 flex-shrink-0 mt-0.5"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
          <div>
            <p className="text-sm font-semibold text-yellow-900 mb-1">
              Privacy Notice
            </p>
            <p className="text-sm text-yellow-900">
              Enter only food preferences. <strong>DO NOT include medical diagnoses.</strong> This information is retained for 90 days.
            </p>
          </div>
        </div>
      </div>

      {/* Textarea */}
      <div>
        <label htmlFor="restrictions" className="block text-sm font-medium text-gray-700 mb-2">
          Dietary Restrictions (Optional)
        </label>
        <textarea
          id="restrictions"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Examples:&#10;• No dairy from cows, goat dairy OK&#10;• Allergic to shellfish&#10;• Prefer coconut-based alternatives&#10;• No nightshades"
          maxLength={maxLength}
          rows={6}
          className={`w-full px-4 py-3 border-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 resize-none ${
            error ? 'border-red-500' : 'border-gray-300'
          }`}
          aria-invalid={!!error}
          aria-describedby={error ? 'restrictions-error' : 'char-count'}
        />
        <div className="flex justify-between items-center mt-1">
          <div>
            {error && (
              <p id="restrictions-error" className="text-sm text-red-600">
                {error}
              </p>
            )}
          </div>
          <p
            id="char-count"
            className={`text-sm ${
              remainingChars < 50 ? 'text-orange-600 font-medium' : 'text-gray-500'
            }`}
          >
            {remainingChars} characters remaining
          </p>
        </div>
      </div>

      {/* Helpful Tips */}
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <h3 className="text-sm font-semibold text-blue-900 mb-2">Helpful Tips:</h3>
        <ul className="text-sm text-blue-900 space-y-1 list-disc list-inside">
          <li>Be specific about what you can't or won't eat</li>
          <li>Mention alternative preferences (e.g., "No chicken, but turkey is fine")</li>
          <li>Include both allergies and strong dislikes</li>
          <li>Leave blank if you have no restrictions</li>
        </ul>
      </div>
    </div>
  );
}
