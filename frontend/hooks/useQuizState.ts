'use client';

import { useForm, UseFormReturn } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useState } from 'react';
import { z } from 'zod';

// Quiz data structure based on data-model.md
export interface QuizData {
  step_1: string; // 'male' | 'female'
  step_2: string; // activity level
  step_3: string[]; // Poultry
  step_4: string[]; // Fish & Seafood
  step_5: string[]; // Low-Carb Vegetables
  step_6: string[]; // Cruciferous Vegetables
  step_7: string[]; // Leafy Greens
  step_8: string[]; // Additional Vegetables
  step_9: string[]; // Additional Proteins
  step_10: string[]; // Organ Meats
  step_11: string[]; // Berries
  step_12: string[]; // Nuts & Seeds
  step_13: string[]; // Herbs & Spices
  step_14: string[]; // Fats & Oils
  step_15: string[]; // Beverages
  step_16: string[]; // Dairy & Alternatives
  step_17: string; // Dietary restrictions (text)
  step_18: string; // Meals per day
  step_19: string[]; // Behavioral patterns
  step_20: {
    age: number;
    weight_kg: number;
    height_cm: number;
    goal: string; // 'weight_loss' | 'maintenance' | 'muscle_gain'
  };
}

// Default values for quiz
const defaultQuizValues: QuizData = {
  step_1: '',
  step_2: '',
  step_3: [],
  step_4: [],
  step_5: [],
  step_6: [],
  step_7: [],
  step_8: [],
  step_9: [],
  step_10: [],
  step_11: [],
  step_12: [],
  step_13: [],
  step_14: [],
  step_15: [],
  step_16: [],
  step_17: '',
  step_18: '3_meals',
  step_19: [],
  step_20: {
    age: 0,
    weight_kg: 0,
    height_cm: 0,
    goal: '',
  },
};

// Basic validation schema (full validation in lib/validators/quiz.ts)
const quizSchema = z.object({
  step_1: z.string().optional(),
  step_2: z.string().optional(),
  step_3: z.array(z.string()).default([]),
  step_4: z.array(z.string()).default([]),
  step_5: z.array(z.string()).default([]),
  step_6: z.array(z.string()).default([]),
  step_7: z.array(z.string()).default([]),
  step_8: z.array(z.string()).default([]),
  step_9: z.array(z.string()).default([]),
  step_10: z.array(z.string()).default([]),
  step_11: z.array(z.string()).default([]),
  step_12: z.array(z.string()).default([]),
  step_13: z.array(z.string()).default([]),
  step_14: z.array(z.string()).default([]),
  step_15: z.array(z.string()).default([]),
  step_16: z.array(z.string()).default([]),
  step_17: z.string().default(''),
  step_18: z.string().default('3_meals'),
  step_19: z.array(z.string()).default([]),
  step_20: z.object({
    age: z.number().default(0),
    weight_kg: z.number().default(0),
    height_cm: z.number().default(0),
    goal: z.string().default(''),
  }),
});

const STORAGE_KEY = 'keto-quiz-data';
const STORAGE_STEP_KEY = 'keto-quiz-current-step';

interface UseQuizStateReturn {
  form: UseFormReturn<QuizData>;
  currentStep: number;
  totalSteps: number;
  goToStep: (step: number) => void;
  nextStep: () => void;
  previousStep: () => void;
  canGoBack: boolean;
  canGoForward: boolean;
  isFirstStep: boolean;
  isLastStep: boolean;
  saveToLocalStorage: () => void;
  clearQuiz: () => void;
  getTotalFoodItems: () => number;
}

/**
 * Custom hook for managing quiz state with React Hook Form and localStorage persistence
 * Follows frontend-quiz-engineer.md guidelines for state management
 */
export function useQuizState(): UseQuizStateReturn {
  const [currentStep, setCurrentStep] = useState(1);
  const totalSteps = 20;

  // Initialize React Hook Form with Zod validation
  const form = useForm<QuizData>({
    resolver: zodResolver(quizSchema) as any,
    defaultValues: defaultQuizValues,
    mode: 'onChange', // Real-time validation
    shouldUnregister: false, // Preserve unmounted step data (per guide)
  });

  // Load saved data from localStorage on mount
  useEffect(() => {
    try {
      const savedData = localStorage.getItem(STORAGE_KEY);
      const savedStep = localStorage.getItem(STORAGE_STEP_KEY);

      if (savedData) {
        const parsed = JSON.parse(savedData);
        form.reset(parsed);
      }

      if (savedStep) {
        setCurrentStep(parseInt(savedStep, 10));
      }
    } catch (error) {
      console.error('Failed to load quiz data from localStorage:', error);
    }
  }, [form]);

  // Save to localStorage whenever form data changes
  const saveToLocalStorage = () => {
    try {
      const data = form.getValues();
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      localStorage.setItem(STORAGE_STEP_KEY, currentStep.toString());
    } catch (error) {
      console.error('Failed to save quiz data to localStorage:', error);
    }
  };

  // Auto-save on step change
  useEffect(() => {
    saveToLocalStorage();
  }, [currentStep]);

  // Navigation helpers
  const goToStep = (step: number) => {
    if (step >= 1 && step <= totalSteps) {
      saveToLocalStorage();
      setCurrentStep(step);
    }
  };

  const nextStep = () => {
    if (currentStep < totalSteps) {
      goToStep(currentStep + 1);
    }
  };

  const previousStep = () => {
    if (currentStep > 1) {
      goToStep(currentStep - 1);
    }
  };

  const canGoBack = currentStep > 1;
  const canGoForward = currentStep < totalSteps;
  const isFirstStep = currentStep === 1;
  const isLastStep = currentStep === totalSteps;

  // Clear quiz data
  const clearQuiz = () => {
    try {
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(STORAGE_STEP_KEY);
      form.reset(defaultQuizValues);
      setCurrentStep(1);
    } catch (error) {
      console.error('Failed to clear quiz data:', error);
    }
  };

  // Helper: Get total food items count (FR-Q-017 validation)
  const getTotalFoodItems = (): number => {
    const data = form.getValues();
    const foodSteps = [
      data.step_3,
      data.step_4,
      data.step_5,
      data.step_6,
      data.step_7,
      data.step_8,
      data.step_9,
      data.step_10,
      data.step_11,
      data.step_12,
      data.step_13,
      data.step_14,
      data.step_15,
      data.step_16,
    ];
    return foodSteps.flat().length;
  };

  return {
    form,
    currentStep,
    totalSteps,
    goToStep,
    nextStep,
    previousStep,
    canGoBack,
    canGoForward,
    isFirstStep,
    isLastStep,
    saveToLocalStorage,
    clearQuiz,
    getTotalFoodItems,
  };
}
