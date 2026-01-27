/**
 * Create Account Page Tests (T101)
 *
 * Tests for account creation page with signup token validation.
 *
 * Test Coverage:
 * - Token decoding and validation
 * - Email readonly field pre-filling
 * - Password validation and confirmation
 * - Password strength indicator
 * - Form submission with API integration
 * - Error handling (invalid token, expired, network errors)
 * - Accessibility (ARIA labels, keyboard navigation)
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRouter, useSearchParams } from 'next/navigation';
import CreateAccountPage from '../page';
import * as authService from '@/services/authService';

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  useSearchParams: jest.fn(),
}));

// Mock auth service
jest.mock('@/services/authService', () => ({
  registerAccount: jest.fn(),
  decodeSignupToken: jest.fn(),
  storeAccessToken: jest.fn(),
  AuthServiceError: class AuthServiceError extends Error {
    constructor(
      message: string,
      public statusCode?: number,
      public code?: string
    ) {
      super(message);
      this.name = 'AuthServiceError';
    }
  },
}));

describe('CreateAccountPage', () => {
  const mockRouter = {
    push: jest.fn(),
  };

  const mockSearchParams = {
    get: jest.fn(),
  };

  const validToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InVzZXJAZXhhbXBsZS5jb20iLCJ0eXBlIjoic2lnbnVwIiwiZXhwIjo5OTk5OTk5OTk5LCJpYXQiOjE2MDk0NTk4MDB9.test';

  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);
  });

  describe('Token Validation', () => {
    it('should show error when token is missing', async () => {
      mockSearchParams.get.mockReturnValue(null);

      render(<CreateAccountPage />);

      await waitFor(() => {
        expect(screen.getByText('Invalid Link')).toBeInTheDocument();
        expect(
          screen.getByText(/This link is missing required information/i)
        ).toBeInTheDocument();
      });
    });

    it('should show error when token is invalid', async () => {
      mockSearchParams.get.mockReturnValue('invalid-token');
      (authService.decodeSignupToken as jest.Mock).mockReturnValue(null);

      render(<CreateAccountPage />);

      await waitFor(() => {
        expect(screen.getByText('Invalid Link')).toBeInTheDocument();
        expect(
          screen.getByText(/This account creation link is invalid/i)
        ).toBeInTheDocument();
      });
    });

    it('should show error when token is expired', async () => {
      const expiredToken = 'expired-token';
      mockSearchParams.get.mockReturnValue(expiredToken);
      (authService.decodeSignupToken as jest.Mock).mockReturnValue({
        email: 'user@example.com',
        type: 'signup',
        exp: Math.floor(Date.now() / 1000) - 3600, // Expired 1 hour ago
        iat: Math.floor(Date.now() / 1000) - 7200,
      });

      render(<CreateAccountPage />);

      await waitFor(() => {
        expect(screen.getByText('Link Expired')).toBeInTheDocument();
        expect(
          screen.getByText(/This account creation link has expired/i)
        ).toBeInTheDocument();
      });
    });

    it('should show form when token is valid', async () => {
      mockSearchParams.get.mockReturnValue(validToken);
      (authService.decodeSignupToken as jest.Mock).mockReturnValue({
        email: 'user@example.com',
        type: 'signup',
        exp: Math.floor(Date.now() / 1000) + 86400, // Expires in 24 hours
        iat: Math.floor(Date.now() / 1000),
      });

      render(<CreateAccountPage />);

      await waitFor(() => {
        expect(screen.getByText('Create Your Account')).toBeInTheDocument();
        expect(
          screen.getByText(/Get permanent access to your meal plan/i)
        ).toBeInTheDocument();
      });
    });
  });

  describe('Form Fields', () => {
    beforeEach(() => {
      mockSearchParams.get.mockReturnValue(validToken);
      (authService.decodeSignupToken as jest.Mock).mockReturnValue({
        email: 'user@example.com',
        type: 'signup',
        exp: Math.floor(Date.now() / 1000) + 86400,
        iat: Math.floor(Date.now() / 1000),
      });
    });

    it('should pre-fill email field as readonly', async () => {
      render(<CreateAccountPage />);

      await waitFor(() => {
        const emailInput = screen.getByLabelText('Email Address') as HTMLInputElement;
        expect(emailInput).toBeInTheDocument();
        expect(emailInput.value).toBe('user@example.com');
        expect(emailInput).toHaveAttribute('readonly');
        expect(emailInput).toHaveClass('cursor-not-allowed');
      });
    });

    it('should show password field with validation', async () => {
      render(<CreateAccountPage />);

      await waitFor(() => {
        const passwordInput = screen.getByLabelText('Password');
        expect(passwordInput).toBeInTheDocument();
        expect(passwordInput).toHaveAttribute('type', 'password');
      });
    });

    it('should show confirm password field', async () => {
      render(<CreateAccountPage />);

      await waitFor(() => {
        const confirmInput = screen.getByLabelText('Confirm Password');
        expect(confirmInput).toBeInTheDocument();
        expect(confirmInput).toHaveAttribute('type', 'password');
      });
    });

    it('should display password strength indicator', async () => {
      const user = userEvent.setup();
      render(<CreateAccountPage />);

      await waitFor(() => {
        expect(screen.getByLabelText('Password')).toBeInTheDocument();
      });

      const passwordInput = screen.getByLabelText('Password');
      await user.type(passwordInput, 'weak');

      await waitFor(() => {
        expect(screen.getByText('Password strength:')).toBeInTheDocument();
        expect(screen.getByText('Weak')).toBeInTheDocument();
      });

      await user.clear(passwordInput);
      await user.type(passwordInput, 'StrongP@ssw0rd!');

      await waitFor(() => {
        expect(screen.getByText('Strong')).toBeInTheDocument();
      });
    });
  });

  describe('Form Validation', () => {
    beforeEach(() => {
      mockSearchParams.get.mockReturnValue(validToken);
      (authService.decodeSignupToken as jest.Mock).mockReturnValue({
        email: 'user@example.com',
        type: 'signup',
        exp: Math.floor(Date.now() / 1000) + 86400,
        iat: Math.floor(Date.now() / 1000),
      });
    });

    it('should validate password minimum length', async () => {
      const user = userEvent.setup();
      render(<CreateAccountPage />);

      await waitFor(() => {
        expect(screen.getByLabelText('Password')).toBeInTheDocument();
      });

      const passwordInput = screen.getByLabelText('Password');
      const submitButton = screen.getByRole('button', { name: /Create Account/i });

      await user.type(passwordInput, 'short');
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText(/Password must be at least 8 characters/i)
        ).toBeInTheDocument();
      });
    });

    it('should validate password confirmation match', async () => {
      const user = userEvent.setup();
      render(<CreateAccountPage />);

      await waitFor(() => {
        expect(screen.getByLabelText('Password')).toBeInTheDocument();
      });

      const passwordInput = screen.getByLabelText('Password');
      const confirmInput = screen.getByLabelText('Confirm Password');
      const submitButton = screen.getByRole('button', { name: /Create Account/i });

      await user.type(passwordInput, 'ValidPassword123!');
      await user.type(confirmInput, 'DifferentPassword123!');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Passwords don't match/i)).toBeInTheDocument();
      });
    });
  });

  describe('Form Submission', () => {
    beforeEach(() => {
      mockSearchParams.get.mockReturnValue(validToken);
      (authService.decodeSignupToken as jest.Mock).mockReturnValue({
        email: 'user@example.com',
        type: 'signup',
        exp: Math.floor(Date.now() / 1000) + 86400,
        iat: Math.floor(Date.now() / 1000),
      });
    });

    it('should successfully create account and redirect', async () => {
      const user = userEvent.setup();
      (authService.registerAccount as jest.Mock).mockResolvedValue({
        access_token: 'test-token',
        token_type: 'bearer',
        user_id: 'user-123',
        email: 'user@example.com',
      });

      render(<CreateAccountPage />);

      await waitFor(() => {
        expect(screen.getByLabelText('Password')).toBeInTheDocument();
      });

      const passwordInput = screen.getByLabelText('Password');
      const confirmInput = screen.getByLabelText('Confirm Password');
      const submitButton = screen.getByRole('button', { name: /Create Account/i });

      await user.type(passwordInput, 'ValidPassword123!');
      await user.type(confirmInput, 'ValidPassword123!');
      await user.click(submitButton);

      await waitFor(() => {
        expect(authService.registerAccount).toHaveBeenCalledWith(
          'user@example.com',
          'ValidPassword123!',
          validToken
        );
        expect(authService.storeAccessToken).toHaveBeenCalledWith('test-token');
        expect(mockRouter.push).toHaveBeenCalledWith('/dashboard');
      });
    });

    it('should show loading state during submission', async () => {
      const user = userEvent.setup();
      (authService.registerAccount as jest.Mock).mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 1000))
      );

      render(<CreateAccountPage />);

      await waitFor(() => {
        expect(screen.getByLabelText('Password')).toBeInTheDocument();
      });

      const passwordInput = screen.getByLabelText('Password');
      const confirmInput = screen.getByLabelText('Confirm Password');
      const submitButton = screen.getByRole('button', { name: /Create Account/i });

      await user.type(passwordInput, 'ValidPassword123!');
      await user.type(confirmInput, 'ValidPassword123!');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Creating Account...')).toBeInTheDocument();
        expect(submitButton).toBeDisabled();
      });
    });

    it('should handle network error', async () => {
      const user = userEvent.setup();
      const AuthServiceError = (authService as any).AuthServiceError;
      (authService.registerAccount as jest.Mock).mockRejectedValue(
        new AuthServiceError(
          'Network error. Please check your internet connection and try again.',
          0,
          'network_error'
        )
      );

      render(<CreateAccountPage />);

      await waitFor(() => {
        expect(screen.getByLabelText('Password')).toBeInTheDocument();
      });

      const passwordInput = screen.getByLabelText('Password');
      const confirmInput = screen.getByLabelText('Confirm Password');
      const submitButton = screen.getByRole('button', { name: /Create Account/i });

      await user.type(passwordInput, 'ValidPassword123!');
      await user.type(confirmInput, 'ValidPassword123!');
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText(/Unable to connect to the server/i)
        ).toBeInTheDocument();
      });
    });

    it('should handle email already exists error', async () => {
      const user = userEvent.setup();
      const AuthServiceError = (authService as any).AuthServiceError;
      (authService.registerAccount as jest.Mock).mockRejectedValue(
        new AuthServiceError(
          'Email already exists',
          409,
          'EMAIL_ALREADY_EXISTS'
        )
      );

      render(<CreateAccountPage />);

      await waitFor(() => {
        expect(screen.getByLabelText('Password')).toBeInTheDocument();
      });

      const passwordInput = screen.getByLabelText('Password');
      const confirmInput = screen.getByLabelText('Confirm Password');
      const submitButton = screen.getByRole('button', { name: /Create Account/i });

      await user.type(passwordInput, 'ValidPassword123!');
      await user.type(confirmInput, 'ValidPassword123!');
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText(/An account with this email already exists/i)
        ).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    beforeEach(() => {
      mockSearchParams.get.mockReturnValue(validToken);
      (authService.decodeSignupToken as jest.Mock).mockReturnValue({
        email: 'user@example.com',
        type: 'signup',
        exp: Math.floor(Date.now() / 1000) + 86400,
        iat: Math.floor(Date.now() / 1000),
      });
    });

    it('should have proper ARIA labels', async () => {
      render(<CreateAccountPage />);

      await waitFor(() => {
        const emailInput = screen.getByLabelText('Email Address');
        const passwordInput = screen.getByLabelText('Password');
        const confirmInput = screen.getByLabelText('Confirm Password');

        expect(emailInput).toHaveAttribute('aria-describedby', 'email-help');
        expect(passwordInput).toHaveAttribute(
          'aria-describedby',
          expect.stringContaining('password')
        );
        expect(confirmInput).toHaveAttribute(
          'aria-describedby',
          expect.stringContaining('confirm-password')
        );
      });
    });

    it('should announce errors to screen readers', async () => {
      const user = userEvent.setup();
      render(<CreateAccountPage />);

      await waitFor(() => {
        expect(screen.getByLabelText('Password')).toBeInTheDocument();
      });

      const passwordInput = screen.getByLabelText('Password');
      const submitButton = screen.getByRole('button', { name: /Create Account/i });

      await user.type(passwordInput, 'short');
      await user.click(submitButton);

      await waitFor(() => {
        const errorMessage = screen.getByRole('alert');
        expect(errorMessage).toBeInTheDocument();
        expect(errorMessage).toHaveTextContent(/Password must be at least 8 characters/i);
      });
    });
  });
});
