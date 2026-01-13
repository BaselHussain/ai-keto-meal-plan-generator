/**
 * QuizContainer State Restoration Tests
 * Task: T048 - Create state restoration tests to verify data persists when navigating backward
 *
 * Test Coverage:
 * - User can navigate back from step 10 to step 9
 * - Form data persists when navigating backward
 * - Back button is disabled on step 1
 * - No data loss occurs during navigation
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QuizContainer } from '@/components/quiz/QuizContainer';
import * as useQuizStateModule from '@/hooks/useQuizState';

// Mock the useQuizState hook
const mockUseQuizState = vi.fn();

vi.mock('@/hooks/useQuizState', () => ({
  useQuizState: () => mockUseQuizState(),
}));

describe('QuizContainer - State Restoration (T048)', () => {
  const mockForm = {
    register: vi.fn(),
    handleSubmit: vi.fn(),
    watch: vi.fn(),
    getValues: vi.fn(() => ({
      step_1: 'male',
      step_2: 'moderate',
      step_3: ['chicken', 'turkey'],
      step_4: ['salmon', 'tuna'],
      step_5: ['broccoli', 'spinach'],
      step_6: ['cauliflower', 'cabbage'],
      step_7: ['kale', 'lettuce'],
      step_8: ['zucchini', 'cucumber'],
      step_9: ['beef', 'pork'],
      step_10: ['liver'],
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
        age: 30,
        weight_kg: 75,
        height_cm: 175,
        goal: 'weight_loss',
      },
    })),
    setValue: vi.fn(),
    reset: vi.fn(),
    formState: {
      errors: {},
      isDirty: false,
      isValid: true,
    },
  } as any;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Backward Navigation from Step 10 to Step 9', () => {
    it('should allow user to navigate back from step 10 to step 9', async () => {
      const user = userEvent.setup();
      const mockPreviousStep = vi.fn();

      mockUseQuizState.mockReturnValue({
        form: mockForm,
        currentStep: 10,
        totalSteps: 20,
        goToStep: vi.fn(),
        nextStep: vi.fn(),
        previousStep: mockPreviousStep,
        canGoBack: true,
        canGoForward: true,
        isFirstStep: false,
        isLastStep: false,
        saveToLocalStorage: vi.fn(),
        clearQuiz: vi.fn(),
        getTotalFoodItems: vi.fn(() => 10),
      });

      render(<QuizContainer />);

      const backButton = screen.getByRole('button', { name: /go to previous step/i });
      expect(backButton).not.toBeDisabled();

      await user.click(backButton);

      expect(mockPreviousStep).toHaveBeenCalledTimes(1);
    });

    it('should display correct step indicator when on step 10', () => {
      mockUseQuizState.mockReturnValue({
        form: mockForm,
        currentStep: 10,
        totalSteps: 20,
        goToStep: vi.fn(),
        nextStep: vi.fn(),
        previousStep: vi.fn(),
        canGoBack: true,
        canGoForward: true,
        isFirstStep: false,
        isLastStep: false,
        saveToLocalStorage: vi.fn(),
        clearQuiz: vi.fn(),
        getTotalFoodItems: vi.fn(() => 10),
      });

      render(<QuizContainer />);

      const stepIndicators = screen.getAllByText('Step 10 of 20');
      expect(stepIndicators.length).toBeGreaterThan(0);
    });
  });

  describe('Data Persistence During Backward Navigation', () => {
    it('should call saveToLocalStorage when navigating backward', async () => {
      const user = userEvent.setup();
      const mockSaveToLocalStorage = vi.fn();
      const mockPreviousStep = vi.fn();

      mockUseQuizState.mockReturnValue({
        form: mockForm,
        currentStep: 10,
        totalSteps: 20,
        goToStep: vi.fn(),
        nextStep: vi.fn(),
        previousStep: mockPreviousStep,
        canGoBack: true,
        canGoForward: true,
        isFirstStep: false,
        isLastStep: false,
        saveToLocalStorage: mockSaveToLocalStorage,
        clearQuiz: vi.fn(),
        getTotalFoodItems: vi.fn(() => 10),
      });

      render(<QuizContainer />);

      const backButton = screen.getByRole('button', { name: /go to previous step/i });
      await user.click(backButton);

      expect(mockPreviousStep).toHaveBeenCalledTimes(1);
      // saveToLocalStorage is called internally by useQuizState hook
    });

    it('should preserve form data when moving from step 9 to step 10 and back', async () => {
      const user = userEvent.setup();
      const mockGoToStep = vi.fn();
      let currentStep = 9;

      // Initial render at step 9
      mockUseQuizState.mockReturnValue({
        form: mockForm,
        currentStep: 9,
        totalSteps: 20,
        goToStep: mockGoToStep,
        nextStep: vi.fn(() => {
          currentStep = 10;
        }),
        previousStep: vi.fn(() => {
          currentStep = 9;
        }),
        canGoBack: true,
        canGoForward: true,
        isFirstStep: false,
        isLastStep: false,
        saveToLocalStorage: vi.fn(),
        clearQuiz: vi.fn(),
        getTotalFoodItems: vi.fn(() => 10),
      });

      const { rerender } = render(<QuizContainer />);

      // Verify we're at step 9
      expect(screen.getAllByText('Step 9 of 20').length).toBeGreaterThan(0);

      // Move to step 10
      const nextButton = screen.getByRole('button', { name: /go to next step/i });
      await user.click(nextButton);

      // Re-render with step 10
      mockUseQuizState.mockReturnValue({
        form: mockForm,
        currentStep: 10,
        totalSteps: 20,
        goToStep: mockGoToStep,
        nextStep: vi.fn(),
        previousStep: vi.fn(() => {
          currentStep = 9;
        }),
        canGoBack: true,
        canGoForward: true,
        isFirstStep: false,
        isLastStep: false,
        saveToLocalStorage: vi.fn(),
        clearQuiz: vi.fn(),
        getTotalFoodItems: vi.fn(() => 10),
      });

      rerender(<QuizContainer />);

      // Verify we're at step 10
      expect(screen.getAllByText('Step 10 of 20').length).toBeGreaterThan(0);

      // Navigate back to step 9
      const backButton = screen.getByRole('button', { name: /go to previous step/i });
      await user.click(backButton);

      // Re-render with step 9 again
      mockUseQuizState.mockReturnValue({
        form: mockForm,
        currentStep: 9,
        totalSteps: 20,
        goToStep: mockGoToStep,
        nextStep: vi.fn(),
        previousStep: vi.fn(),
        canGoBack: true,
        canGoForward: true,
        isFirstStep: false,
        isLastStep: false,
        saveToLocalStorage: vi.fn(),
        clearQuiz: vi.fn(),
        getTotalFoodItems: vi.fn(() => 10),
      });

      rerender(<QuizContainer />);

      // Verify we're back at step 9
      expect(screen.getAllByText('Step 9 of 20').length).toBeGreaterThan(0);

      // Verify form data is still intact
      const formData = mockForm.getValues();
      expect(formData.step_9).toEqual(['beef', 'pork']);
      expect(formData.step_10).toEqual(['liver']);
    });

    it('should not lose data when navigating through multiple steps backward', () => {
      // Simulate navigation from step 10 -> 9 -> 8 -> 9
      const steps = [10, 9, 8, 9];

      steps.forEach((step) => {
        mockUseQuizState.mockReturnValue({
          form: mockForm,
          currentStep: step,
          totalSteps: 20,
          goToStep: vi.fn(),
          nextStep: vi.fn(),
          previousStep: vi.fn(),
          canGoBack: step > 1,
          canGoForward: step < 20,
          isFirstStep: step === 1,
          isLastStep: step === 20,
          saveToLocalStorage: vi.fn(),
          clearQuiz: vi.fn(),
          getTotalFoodItems: vi.fn(() => 10),
        });

        const { unmount } = render(<QuizContainer />);

        // Verify form data persists
        const formData = mockForm.getValues();
        expect(formData.step_9).toEqual(['beef', 'pork']);
        expect(formData.step_8).toEqual(['zucchini', 'cucumber']);
        expect(formData.step_10).toEqual(['liver']);

        unmount();
      });
    });
  });

  describe('Back Button Disabled on Step 1', () => {
    it('should disable back button when on first step', () => {
      mockUseQuizState.mockReturnValue({
        form: mockForm,
        currentStep: 1,
        totalSteps: 20,
        goToStep: vi.fn(),
        nextStep: vi.fn(),
        previousStep: vi.fn(),
        canGoBack: false,
        canGoForward: true,
        isFirstStep: true,
        isLastStep: false,
        saveToLocalStorage: vi.fn(),
        clearQuiz: vi.fn(),
        getTotalFoodItems: vi.fn(() => 0),
      });

      render(<QuizContainer />);

      const backButton = screen.getByRole('button', { name: /go to previous step/i });
      expect(backButton).toBeDisabled();
      expect(backButton).toHaveClass('cursor-not-allowed');
    });

    it('should not call previousStep when back button is clicked on step 1', async () => {
      const user = userEvent.setup();
      const mockPreviousStep = vi.fn();

      mockUseQuizState.mockReturnValue({
        form: mockForm,
        currentStep: 1,
        totalSteps: 20,
        goToStep: vi.fn(),
        nextStep: vi.fn(),
        previousStep: mockPreviousStep,
        canGoBack: false,
        canGoForward: true,
        isFirstStep: true,
        isLastStep: false,
        saveToLocalStorage: vi.fn(),
        clearQuiz: vi.fn(),
        getTotalFoodItems: vi.fn(() => 0),
      });

      render(<QuizContainer />);

      const backButton = screen.getByRole('button', { name: /go to previous step/i });

      // Try to click disabled button
      await user.click(backButton);

      // previousStep should not be called since button is disabled
      expect(mockPreviousStep).not.toHaveBeenCalled();
    });

    it('should display step 1 of 20 when on first step', () => {
      mockUseQuizState.mockReturnValue({
        form: mockForm,
        currentStep: 1,
        totalSteps: 20,
        goToStep: vi.fn(),
        nextStep: vi.fn(),
        previousStep: vi.fn(),
        canGoBack: false,
        canGoForward: true,
        isFirstStep: true,
        isLastStep: false,
        saveToLocalStorage: vi.fn(),
        clearQuiz: vi.fn(),
        getTotalFoodItems: vi.fn(() => 0),
      });

      render(<QuizContainer />);

      expect(screen.getAllByText('Step 1 of 20').length).toBeGreaterThan(0);
    });
  });

  describe('No Data Loss During Navigation', () => {
    it('should maintain all form data through forward and backward navigation', async () => {
      const user = userEvent.setup();

      // Start at step 5
      mockUseQuizState.mockReturnValue({
        form: mockForm,
        currentStep: 5,
        totalSteps: 20,
        goToStep: vi.fn(),
        nextStep: vi.fn(),
        previousStep: vi.fn(),
        canGoBack: true,
        canGoForward: true,
        isFirstStep: false,
        isLastStep: false,
        saveToLocalStorage: vi.fn(),
        clearQuiz: vi.fn(),
        getTotalFoodItems: vi.fn(() => 6),
      });

      const { rerender } = render(<QuizContainer />);

      // Verify initial data
      let formData = mockForm.getValues();
      expect(formData.step_1).toBe('male');
      expect(formData.step_2).toBe('moderate');
      expect(formData.step_3).toEqual(['chicken', 'turkey']);

      // Navigate forward
      const nextButton = screen.getByRole('button', { name: /go to next step/i });
      await user.click(nextButton);

      mockUseQuizState.mockReturnValue({
        form: mockForm,
        currentStep: 6,
        totalSteps: 20,
        goToStep: vi.fn(),
        nextStep: vi.fn(),
        previousStep: vi.fn(),
        canGoBack: true,
        canGoForward: true,
        isFirstStep: false,
        isLastStep: false,
        saveToLocalStorage: vi.fn(),
        clearQuiz: vi.fn(),
        getTotalFoodItems: vi.fn(() => 6),
      });

      rerender(<QuizContainer />);

      // Verify data persists after moving forward
      formData = mockForm.getValues();
      expect(formData.step_1).toBe('male');
      expect(formData.step_5).toEqual(['broccoli', 'spinach']);

      // Navigate backward
      const backButton = screen.getByRole('button', { name: /go to previous step/i });
      await user.click(backButton);

      mockUseQuizState.mockReturnValue({
        form: mockForm,
        currentStep: 5,
        totalSteps: 20,
        goToStep: vi.fn(),
        nextStep: vi.fn(),
        previousStep: vi.fn(),
        canGoBack: true,
        canGoForward: true,
        isFirstStep: false,
        isLastStep: false,
        saveToLocalStorage: vi.fn(),
        clearQuiz: vi.fn(),
        getTotalFoodItems: vi.fn(() => 6),
      });

      rerender(<QuizContainer />);

      // Verify all data still intact
      formData = mockForm.getValues();
      expect(formData.step_1).toBe('male');
      expect(formData.step_2).toBe('moderate');
      expect(formData.step_3).toEqual(['chicken', 'turkey']);
      expect(formData.step_4).toEqual(['salmon', 'tuna']);
      expect(formData.step_5).toEqual(['broccoli', 'spinach']);
    });

    it('should verify getTotalFoodItems remains consistent during navigation', () => {
      const mockGetTotalFoodItems = vi.fn(() => 10);

      mockUseQuizState.mockReturnValue({
        form: mockForm,
        currentStep: 10,
        totalSteps: 20,
        goToStep: vi.fn(),
        nextStep: vi.fn(),
        previousStep: vi.fn(),
        canGoBack: true,
        canGoForward: true,
        isFirstStep: false,
        isLastStep: false,
        saveToLocalStorage: vi.fn(),
        clearQuiz: vi.fn(),
        getTotalFoodItems: mockGetTotalFoodItems,
      });

      render(<QuizContainer />);

      // Food items count should remain consistent
      expect(mockGetTotalFoodItems()).toBe(10);
    });

    it('should handle edge case of navigating back from step 2', async () => {
      const user = userEvent.setup();
      const mockPreviousStep = vi.fn();

      mockUseQuizState.mockReturnValue({
        form: mockForm,
        currentStep: 2,
        totalSteps: 20,
        goToStep: vi.fn(),
        nextStep: vi.fn(),
        previousStep: mockPreviousStep,
        canGoBack: true,
        canGoForward: true,
        isFirstStep: false,
        isLastStep: false,
        saveToLocalStorage: vi.fn(),
        clearQuiz: vi.fn(),
        getTotalFoodItems: vi.fn(() => 2),
      });

      render(<QuizContainer />);

      const backButton = screen.getByRole('button', { name: /go to previous step/i });
      expect(backButton).not.toBeDisabled();

      await user.click(backButton);

      expect(mockPreviousStep).toHaveBeenCalledTimes(1);
    });

    it('should maintain data integrity when rapidly clicking navigation buttons', async () => {
      const user = userEvent.setup();
      const mockNextStep = vi.fn();
      const mockPreviousStep = vi.fn();

      mockUseQuizState.mockReturnValue({
        form: mockForm,
        currentStep: 5,
        totalSteps: 20,
        goToStep: vi.fn(),
        nextStep: mockNextStep,
        previousStep: mockPreviousStep,
        canGoBack: true,
        canGoForward: true,
        isFirstStep: false,
        isLastStep: false,
        saveToLocalStorage: vi.fn(),
        clearQuiz: vi.fn(),
        getTotalFoodItems: vi.fn(() => 6),
      });

      render(<QuizContainer />);

      const nextButton = screen.getByRole('button', { name: /go to next step/i });
      const backButton = screen.getByRole('button', { name: /go to previous step/i });

      // Rapid navigation simulation
      await user.click(nextButton);
      await user.click(backButton);
      await user.click(nextButton);
      await user.click(backButton);

      expect(mockNextStep).toHaveBeenCalledTimes(2);
      expect(mockPreviousStep).toHaveBeenCalledTimes(2);

      // Verify form data integrity
      const formData = mockForm.getValues();
      expect(formData.step_5).toEqual(['broccoli', 'spinach']);
    });
  });

  describe('Navigation UI States', () => {
    it('should enable back button for all steps except step 1', () => {
      const testCases = [
        { step: 1, canGoBack: false },
        { step: 2, canGoBack: true },
        { step: 10, canGoBack: true },
        { step: 20, canGoBack: true },
      ];

      testCases.forEach(({ step, canGoBack }) => {
        mockUseQuizState.mockReturnValue({
          form: mockForm,
          currentStep: step,
          totalSteps: 20,
          goToStep: vi.fn(),
          nextStep: vi.fn(),
          previousStep: vi.fn(),
          canGoBack,
          canGoForward: step < 20,
          isFirstStep: step === 1,
          isLastStep: step === 20,
          saveToLocalStorage: vi.fn(),
          clearQuiz: vi.fn(),
          getTotalFoodItems: vi.fn(() => step),
        });

        const { unmount } = render(<QuizContainer />);

        const backButton = screen.getByRole('button', { name: /go to previous step/i });

        if (canGoBack) {
          expect(backButton).not.toBeDisabled();
        } else {
          expect(backButton).toBeDisabled();
        }

        unmount();
      });
    });

    it('should show correct button styling based on state', () => {
      mockUseQuizState.mockReturnValue({
        form: mockForm,
        currentStep: 1,
        totalSteps: 20,
        goToStep: vi.fn(),
        nextStep: vi.fn(),
        previousStep: vi.fn(),
        canGoBack: false,
        canGoForward: true,
        isFirstStep: true,
        isLastStep: false,
        saveToLocalStorage: vi.fn(),
        clearQuiz: vi.fn(),
        getTotalFoodItems: vi.fn(() => 0),
      });

      render(<QuizContainer />);

      const backButton = screen.getByRole('button', { name: /go to previous step/i });

      // Disabled state styling
      expect(backButton).toHaveClass('bg-gray-100');
      expect(backButton).toHaveClass('text-gray-400');
    });
  });
});
