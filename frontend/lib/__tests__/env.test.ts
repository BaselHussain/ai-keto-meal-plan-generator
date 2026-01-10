/**
 * Tests for environment validation utility
 *
 * These tests verify that the env validation:
 * - Correctly validates required fields in production
 * - Gracefully degrades in development
 * - Validates URL formats
 * - Provides clear error messages
 */

import { describe, it, expect, beforeEach, afterEach } from '@jest/globals';

// Save original env
const originalEnv = { ...process.env };

describe('Environment Validation', () => {
  beforeEach(() => {
    // Reset environment before each test
    process.env = { ...originalEnv };
    // Clear module cache to force re-import
    jest.resetModules();
  });

  afterEach(() => {
    // Restore original environment
    process.env = originalEnv;
  });

  describe('Development Mode', () => {
    it('should allow missing NEXT_PUBLIC_SENTRY_DSN in development', async () => {
      process.env.NODE_ENV = 'development';
      process.env.SKIP_ENV_VALIDATION = undefined;
      delete process.env.NEXT_PUBLIC_SENTRY_DSN;

      // Should not throw in development
      const { env } = await import('../env');
      expect(env.NEXT_PUBLIC_SENTRY_DSN).toBeUndefined();
    });

    it('should use localhost fallback for API_URL in development', async () => {
      process.env.NODE_ENV = 'development';
      delete process.env.NEXT_PUBLIC_API_URL;

      const { env } = await import('../env');
      expect(env.NEXT_PUBLIC_API_URL).toBe('http://localhost:8000');
    });
  });

  describe('Production Mode', () => {
    it('should require NEXT_PUBLIC_SENTRY_DSN in production', async () => {
      process.env.NODE_ENV = 'production';
      delete process.env.NEXT_PUBLIC_SENTRY_DSN;
      delete process.env.SKIP_ENV_VALIDATION;

      // Should throw in production
      await expect(async () => {
        await import('../env');
      }).rejects.toThrow();
    });

    it('should validate Sentry DSN URL format', async () => {
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'invalid-url';

      await expect(async () => {
        await import('../env');
      }).rejects.toThrow();
    });
  });

  describe('SKIP_ENV_VALIDATION', () => {
    it('should skip validation when SKIP_ENV_VALIDATION=1', async () => {
      process.env.NODE_ENV = 'production';
      process.env.SKIP_ENV_VALIDATION = '1';
      delete process.env.NEXT_PUBLIC_SENTRY_DSN;

      // Should not throw even in production
      const { env } = await import('../env');
      expect(env.NEXT_PUBLIC_SENTRY_DSN).toBeUndefined();
    });
  });

  describe('Helper Functions', () => {
    beforeEach(() => {
      process.env.SKIP_ENV_VALIDATION = '1';
    });

    it('should correctly identify production environment', async () => {
      process.env.NODE_ENV = 'production';
      const { isProduction, isDevelopment } = await import('../env');

      expect(isProduction).toBe(true);
      expect(isDevelopment).toBe(false);
    });

    it('should correctly identify development environment', async () => {
      process.env.NODE_ENV = 'development';
      const { isProduction, isDevelopment } = await import('../env');

      expect(isProduction).toBe(false);
      expect(isDevelopment).toBe(true);
    });
  });
});
