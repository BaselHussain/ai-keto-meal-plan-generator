'use client';

import { useState } from 'react';

interface BiometricsData {
  age: number | '';
  weight_kg: number | '';
  height_cm: number | '';
  goal: string;
}

interface Step20BiometricsProps {
  value: BiometricsData;
  onChange: (value: BiometricsData) => void;
  errors?: {
    age?: string;
    weight_kg?: string;
    height_cm?: string;
    goal?: string;
  };
}

export function Step20Biometrics({ value, onChange, errors = {} }: Step20BiometricsProps) {
  const [unit, setUnit] = useState<'metric' | 'imperial'>('metric');

  const goals = [
    { value: 'weight_loss', label: 'Weight Loss', icon: '⬇️', description: '-400 kcal deficit' },
    { value: 'maintenance', label: 'Maintenance', icon: '⚖️', description: 'Maintain current weight' },
    { value: 'muscle_gain', label: 'Muscle Gain', icon: '⬆️', description: '+250 kcal surplus' },
  ];

  const handleInputChange = (field: keyof BiometricsData, inputValue: string) => {
    if (field === 'goal') {
      onChange({ ...value, [field]: inputValue });
    } else {
      const numValue = inputValue === '' ? '' : Number(inputValue);
      onChange({ ...value, [field]: numValue });
    }
  };

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <div className="text-center space-y-2">
        <h2 className="text-2xl md:text-3xl font-bold text-gray-900">
          Tell us about yourself
        </h2>
        <p className="text-gray-600">
          This information helps us calculate your personalized calorie target
        </p>
      </div>

      {/* Privacy Badge */}
      <div className="flex items-center justify-center space-x-2 p-3 bg-green-50 border border-green-200 rounded-lg">
        <svg
          className="w-5 h-5 text-green-600"
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path
            fillRule="evenodd"
            d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
            clipRule="evenodd"
          />
        </svg>
        <span className="text-sm font-medium text-green-800">
          100% Private & Confidential
        </span>
      </div>

      {/* Privacy Notice */}
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-900">
          <strong>Privacy Notice:</strong> Your health data will be used only to generate your meal plan and will be automatically deleted after 24 hours. We never share or sell your information.
        </p>
      </div>

      {/* Unit Toggle */}
      <div className="flex justify-center space-x-2 bg-gray-100 p-1 rounded-lg w-fit mx-auto">
        <button
          type="button"
          onClick={() => setUnit('metric')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            unit === 'metric'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Metric (kg/cm)
        </button>
        <button
          type="button"
          onClick={() => setUnit('imperial')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            unit === 'imperial'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Imperial (lb/in)
        </button>
      </div>

      {/* Input Fields */}
      <div className="space-y-4">
        <div>
          <label htmlFor="age" className="block text-sm font-medium text-gray-700 mb-1">
            Age (years)
          </label>
          <input
            type="number"
            id="age"
            value={value.age}
            onChange={(e) => handleInputChange('age', e.target.value)}
            placeholder="e.g., 35"
            min="18"
            max="100"
            className={`w-full px-4 py-3 border-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 ${
              errors.age ? 'border-red-500' : 'border-gray-300'
            }`}
            aria-invalid={!!errors.age}
            aria-describedby={errors.age ? 'age-error' : undefined}
          />
          {errors.age && (
            <p id="age-error" className="mt-1 text-sm text-red-600">
              {errors.age}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="weight" className="block text-sm font-medium text-gray-700 mb-1">
            Weight ({unit === 'metric' ? 'kg' : 'lbs'})
          </label>
          <input
            type="number"
            id="weight"
            value={value.weight_kg}
            onChange={(e) => handleInputChange('weight_kg', e.target.value)}
            placeholder={unit === 'metric' ? 'e.g., 70' : 'e.g., 154'}
            min="30"
            max="300"
            step="0.1"
            className={`w-full px-4 py-3 border-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 ${
              errors.weight_kg ? 'border-red-500' : 'border-gray-300'
            }`}
            aria-invalid={!!errors.weight_kg}
            aria-describedby={errors.weight_kg ? 'weight-error' : undefined}
          />
          {errors.weight_kg && (
            <p id="weight-error" className="mt-1 text-sm text-red-600">
              {errors.weight_kg}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="height" className="block text-sm font-medium text-gray-700 mb-1">
            Height ({unit === 'metric' ? 'cm' : 'inches'})
          </label>
          <input
            type="number"
            id="height"
            value={value.height_cm}
            onChange={(e) => handleInputChange('height_cm', e.target.value)}
            placeholder={unit === 'metric' ? 'e.g., 170' : 'e.g., 67'}
            min={unit === 'metric' ? '122' : '48'}
            max={unit === 'metric' ? '229' : '90'}
            step="0.1"
            className={`w-full px-4 py-3 border-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 ${
              errors.height_cm ? 'border-red-500' : 'border-gray-300'
            }`}
            aria-invalid={!!errors.height_cm}
            aria-describedby={errors.height_cm ? 'height-error' : undefined}
          />
          {errors.height_cm && (
            <p id="height-error" className="mt-1 text-sm text-red-600">
              {errors.height_cm}
            </p>
          )}
        </div>
      </div>

      {/* Goal Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">
          What's your goal?
        </label>
        <div className="space-y-3">
          {goals.map((goal) => (
            <button
              key={goal.value}
              type="button"
              onClick={() => handleInputChange('goal', goal.value)}
              className={`w-full p-4 rounded-lg border-2 transition-all duration-200 text-left ${
                value.goal === goal.value
                  ? 'border-green-500 bg-green-50 shadow-md'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
              }`}
              aria-pressed={value.goal === goal.value}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <span className="text-2xl">{goal.icon}</span>
                  <div>
                    <div className="font-semibold text-gray-900">{goal.label}</div>
                    <div className="text-sm text-gray-600">{goal.description}</div>
                  </div>
                </div>
                {value.goal === goal.value && (
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
                )}
              </div>
            </button>
          ))}
        </div>
        {errors.goal && (
          <p className="mt-2 text-sm text-red-600">{errors.goal}</p>
        )}
      </div>
    </div>
  );
}
