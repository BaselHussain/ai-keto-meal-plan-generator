'use client';

import { ReactNode } from 'react';

export interface FoodItem {
  value: string;
  label: string;
  icon: ReactNode;
}

interface FoodSelectionGridProps {
  title: string;
  subtitle?: string;
  items: FoodItem[];
  selectedItems: string[];
  onChange: (selectedItems: string[]) => void;
  minItems?: number;
  maxItems?: number;
  error?: string;
}

export function FoodSelectionGrid({
  title,
  subtitle,
  items,
  selectedItems,
  onChange,
  minItems = 0,
  maxItems,
  error,
}: FoodSelectionGridProps) {
  const toggleItem = (itemValue: string) => {
    const isSelected = selectedItems.includes(itemValue);

    if (isSelected) {
      // Deselect
      onChange(selectedItems.filter((v) => v !== itemValue));
    } else {
      // Select (check max limit)
      if (maxItems && selectedItems.length >= maxItems) {
        return; // Don't add if max reached
      }
      onChange([...selectedItems, itemValue]);
    }
  };

  const getSelectionHint = () => {
    if (minItems > 0 && maxItems) {
      return `Select ${minItems}-${maxItems} items`;
    } else if (minItems > 0) {
      return `Select at least ${minItems} items`;
    } else if (maxItems) {
      return `Select up to ${maxItems} items`;
    }
    return 'Select any items that apply';
  };

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl md:text-3xl font-bold text-gray-900">
          {title}
        </h2>
        {subtitle && <p className="text-gray-600">{subtitle}</p>}
        <p className="text-sm text-gray-500">{getSelectionHint()}</p>
        {selectedItems.length > 0 && (
          <p className="text-sm font-medium text-green-600">
            {selectedItems.length} selected
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 mt-8">
        {items.map((item) => {
          const isSelected = selectedItems.includes(item.value);
          const isDisabled = !isSelected && maxItems && selectedItems.length >= maxItems;

          return (
            <button
              key={item.value}
              type="button"
              onClick={() => toggleItem(item.value)}
              disabled={isDisabled}
              className={`
                relative p-4 rounded-lg border-2 transition-all duration-200
                flex flex-col items-center space-y-2
                ${
                  isSelected
                    ? 'border-green-500 bg-green-50 shadow-md'
                    : isDisabled
                    ? 'border-gray-200 bg-gray-100 opacity-50 cursor-not-allowed'
                    : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
                }
              `}
              aria-pressed={isSelected}
              aria-disabled={isDisabled}
            >
              <div className="w-16 h-16 flex items-center justify-center text-4xl">
                {item.icon}
              </div>
              <span className="text-sm font-medium text-gray-900 text-center leading-tight">
                {item.label}
              </span>
              {isSelected && (
                <div className="absolute top-2 right-2">
                  <svg
                    className="w-5 h-5 text-green-500"
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
          );
        })}
      </div>

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}
    </div>
  );
}
