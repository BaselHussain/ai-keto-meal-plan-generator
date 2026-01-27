/**
 * Download Page Tests (T097)
 *
 * Tests for the PDF download page functionality including:
 * - Token verification on mount
 * - Loading state display
 * - Success state with meal plan details
 * - Error states (expired, used, invalid, missing token)
 * - Download button functionality
 */

import { render, screen, waitFor } from '@testing-library/react';
import { useSearchParams } from 'next/navigation';
import DownloadPage from './page';
import * as recoveryService from '@/services/recoveryService';

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useSearchParams: jest.fn(),
}));

// Mock recovery service
jest.mock('@/services/recoveryService', () => ({
  verifyMagicLink: jest.fn(),
  RecoveryServiceError: class RecoveryServiceError extends Error {
    constructor(message: string, public statusCode?: number, public code?: string) {
      super(message);
      this.name = 'RecoveryServiceError';
    }
  },
}));

// Mock framer-motion to avoid animation issues in tests
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h1: ({ children, ...props }: any) => <h1 {...props}>{children}</h1>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
    li: ({ children, ...props }: any) => <li {...props}>{children}</li>,
    svg: ({ children, ...props }: any) => <svg {...props}>{children}</svg>,
    path: ({ children, ...props }: any) => <path {...props}>{children}</path>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

describe('DownloadPage', () => {
  const mockSearchParams = useSearchParams as jest.Mock;
  const mockVerifyMagicLink = recoveryService.verifyMagicLink as jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Loading State', () => {
    it('should display loading state while verifying token', () => {
      mockSearchParams.mockReturnValue({
        get: jest.fn().mockReturnValue('valid-token-123'),
      });

      mockVerifyMagicLink.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 1000))
      );

      render(<DownloadPage />);

      expect(screen.getByText('Verifying Link')).toBeInTheDocument();
      expect(screen.getByText(/Please wait while we verify your magic link/i)).toBeInTheDocument();
    });
  });

  describe('Success State', () => {
    it('should display meal plan details when token is valid', async () => {
      mockSearchParams.mockReturnValue({
        get: jest.fn().mockReturnValue('valid-token-123'),
      });

      const mockMealPlan = {
        meal_plan_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        email: 'user@example.com',
        created_at: '2024-01-15T14:30:00Z',
        pdf_available: true,
      };

      mockVerifyMagicLink.mockResolvedValue(mockMealPlan);

      render(<DownloadPage />);

      await waitFor(() => {
        expect(screen.getByText('Your Meal Plan is Ready')).toBeInTheDocument();
      });

      expect(screen.getByText('user@example.com')).toBeInTheDocument();
      expect(screen.getByText('Download Your Meal Plan')).toBeInTheDocument();
      expect(screen.getByText('Available')).toBeInTheDocument();
    });

    it('should show unavailable status when PDF is not ready', async () => {
      mockSearchParams.mockReturnValue({
        get: jest.fn().mockReturnValue('valid-token-123'),
      });

      const mockMealPlan = {
        meal_plan_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        email: 'user@example.com',
        created_at: '2024-01-15T14:30:00Z',
        pdf_available: false,
      };

      mockVerifyMagicLink.mockResolvedValue(mockMealPlan);

      render(<DownloadPage />);

      await waitFor(() => {
        expect(screen.getByText('Not Available')).toBeInTheDocument();
      });

      expect(screen.getByText(/Your meal plan is still being generated/i)).toBeInTheDocument();
    });
  });

  describe('Error States', () => {
    it('should display error when token is missing', async () => {
      mockSearchParams.mockReturnValue({
        get: jest.fn().mockReturnValue(null),
      });

      render(<DownloadPage />);

      await waitFor(() => {
        expect(screen.getByText('Invalid Link')).toBeInTheDocument();
      });

      expect(screen.getByText(/This link is missing required information/i)).toBeInTheDocument();
    });

    it('should display error when token is expired', async () => {
      mockSearchParams.mockReturnValue({
        get: jest.fn().mockReturnValue('expired-token'),
      });

      mockVerifyMagicLink.mockRejectedValue(
        new recoveryService.RecoveryServiceError(
          'Token expired',
          400,
          'TOKEN_EXPIRED'
        )
      );

      render(<DownloadPage />);

      await waitFor(() => {
        expect(screen.getByText('Link Expired')).toBeInTheDocument();
      });

      expect(screen.getByText(/This magic link has expired/i)).toBeInTheDocument();
      expect(screen.getByText('Request New Magic Link')).toBeInTheDocument();
    });

    it('should display error when token is already used', async () => {
      mockSearchParams.mockReturnValue({
        get: jest.fn().mockReturnValue('used-token'),
      });

      mockVerifyMagicLink.mockRejectedValue(
        new recoveryService.RecoveryServiceError(
          'Token already used',
          400,
          'TOKEN_ALREADY_USED'
        )
      );

      render(<DownloadPage />);

      await waitFor(() => {
        expect(screen.getByText('Link Already Used')).toBeInTheDocument();
      });

      expect(screen.getByText(/This magic link has already been used/i)).toBeInTheDocument();
    });

    it('should display error when token is invalid', async () => {
      mockSearchParams.mockReturnValue({
        get: jest.fn().mockReturnValue('invalid-token'),
      });

      mockVerifyMagicLink.mockRejectedValue(
        new recoveryService.RecoveryServiceError(
          'Token invalid',
          400,
          'TOKEN_INVALID'
        )
      );

      render(<DownloadPage />);

      await waitFor(() => {
        expect(screen.getByText('Invalid Link')).toBeInTheDocument();
      });

      expect(screen.getByText(/This magic link is invalid/i)).toBeInTheDocument();
    });

    it('should display error when no meal plans found', async () => {
      mockSearchParams.mockReturnValue({
        get: jest.fn().mockReturnValue('valid-token-no-plans'),
      });

      mockVerifyMagicLink.mockRejectedValue(
        new recoveryService.RecoveryServiceError(
          'No meal plans found',
          404,
          'NO_MEAL_PLANS'
        )
      );

      render(<DownloadPage />);

      await waitFor(() => {
        expect(screen.getByText('No Meal Plans Found')).toBeInTheDocument();
      });

      expect(screen.getByText(/No meal plans were found for this account/i)).toBeInTheDocument();
      expect(screen.getByText('Start Quiz')).toBeInTheDocument();
    });

    it('should display network error message', async () => {
      mockSearchParams.mockReturnValue({
        get: jest.fn().mockReturnValue('valid-token'),
      });

      mockVerifyMagicLink.mockRejectedValue(
        new recoveryService.RecoveryServiceError(
          'Network error',
          0,
          'network_error'
        )
      );

      render(<DownloadPage />);

      await waitFor(() => {
        expect(screen.getByText('Connection Error')).toBeInTheDocument();
      });

      expect(screen.getByText(/Unable to connect to the server/i)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper heading hierarchy', async () => {
      mockSearchParams.mockReturnValue({
        get: jest.fn().mockReturnValue('valid-token-123'),
      });

      const mockMealPlan = {
        meal_plan_id: 'a1b2c3d4',
        email: 'user@example.com',
        created_at: '2024-01-15T14:30:00Z',
        pdf_available: true,
      };

      mockVerifyMagicLink.mockResolvedValue(mockMealPlan);

      render(<DownloadPage />);

      await waitFor(() => {
        const heading = screen.getByRole('heading', { name: /Your Meal Plan is Ready/i });
        expect(heading).toBeInTheDocument();
      });
    });

    it('should have accessible download button', async () => {
      mockSearchParams.mockReturnValue({
        get: jest.fn().mockReturnValue('valid-token-123'),
      });

      const mockMealPlan = {
        meal_plan_id: 'a1b2c3d4',
        email: 'user@example.com',
        created_at: '2024-01-15T14:30:00Z',
        pdf_available: true,
      };

      mockVerifyMagicLink.mockResolvedValue(mockMealPlan);

      render(<DownloadPage />);

      await waitFor(() => {
        const button = screen.getByRole('button', { name: /Download Your Meal Plan/i });
        expect(button).toBeInTheDocument();
        expect(button).not.toBeDisabled();
      });
    });
  });
});
