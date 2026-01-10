"""
Environment variable validation and configuration management.

This module uses Pydantic BaseSettings to provide type-safe, validated access
to environment variables. All required variables are validated on startup with
clear error messages for missing or invalid values.

Usage:
    from src.lib.env import settings

    # Access validated settings
    db_url = settings.neon_database_url
    api_key = settings.openai_api_key
"""

import os
from typing import Literal, Optional

from pydantic import Field, field_validator, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings are validated on instantiation. Missing required variables
    or invalid formats will raise clear ValidationError exceptions.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # =============================================================================
    # Environment Settings
    # =============================================================================
    env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment",
    )

    app_url: str = Field(
        default="http://localhost:3000",
        description="Frontend application URL for CORS and redirects",
    )

    # =============================================================================
    # Error Tracking (Sentry)
    # =============================================================================
    sentry_backend_dsn: Optional[str] = Field(
        default=None,
        alias="SENTRY_BACKEND_DSN",
        description="Sentry DSN for error tracking (optional in development)",
    )

    sentry_release: Optional[str] = Field(
        default=None,
        alias="SENTRY_RELEASE",
        description="Release version for Sentry error grouping",
    )

    # =============================================================================
    # Database Configuration (Neon PostgreSQL)
    # =============================================================================
    neon_database_url: str = Field(
        ...,
        alias="NEON_DATABASE_URL",
        description="Neon PostgreSQL connection string (required)",
    )

    @field_validator("neon_database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate PostgreSQL connection string format."""
        if not v:
            raise ValueError(
                "NEON_DATABASE_URL is required. "
                "Get it from https://console.neon.tech/app/projects"
            )
        if not v.startswith(("postgresql://", "postgres://")):
            raise ValueError(
                "NEON_DATABASE_URL must start with postgresql:// or postgres://"
            )
        return v

    # =============================================================================
    # Redis Cache & Rate Limiting
    # =============================================================================
    redis_url: str = Field(
        ...,
        alias="REDIS_URL",
        description="Redis connection URL for caching and rate limiting (required)",
    )

    upstash_redis_rest_url: Optional[str] = Field(
        default=None,
        alias="UPSTASH_REDIS_REST_URL",
        description="Upstash Redis REST API URL (alternative for serverless)",
    )

    upstash_redis_rest_token: Optional[str] = Field(
        default=None,
        alias="UPSTASH_REDIS_REST_TOKEN",
        description="Upstash Redis REST API token",
    )

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis connection string format."""
        if not v:
            raise ValueError(
                "REDIS_URL is required. "
                "Use redis://localhost:6379/0 for local development or "
                "get a managed Redis URL from providers like Upstash or Redis Cloud."
            )
        if not v.startswith("redis://") and not v.startswith("rediss://"):
            raise ValueError(
                "REDIS_URL must start with redis:// or rediss:// (for SSL)"
            )
        return v

    # =============================================================================
    # AI Service API Keys
    # =============================================================================
    gemini_api_key: Optional[str] = Field(
        default=None,
        alias="GEMINI_API_KEY",
        description="Google Gemini API key for AI meal plan generation",
    )

    openai_api_key: Optional[str] = Field(
        default=None,
        alias="OPEN_AI_API_KEY",
        description="OpenAI API key (alternative for AI generation)",
    )

    @field_validator("gemini_api_key")
    @classmethod
    def validate_ai_keys(cls, v: Optional[str], info) -> Optional[str]:
        """Ensure at least one AI API key is provided."""
        # Check if we have either Gemini or OpenAI key
        openai_key = info.data.get("openai_api_key")

        if not v and not openai_key:
            raise ValueError(
                "At least one AI API key is required: "
                "GEMINI_API_KEY (https://makersuite.google.com/app/apikey) or "
                "OPEN_AI_API_KEY (https://platform.openai.com/api-keys)"
            )

        return v

    # =============================================================================
    # Payment Processing (Paddle)
    # =============================================================================
    paddle_api_key: str = Field(
        ...,
        alias="PADDLE_API_KEY",
        description="Paddle API key for payment processing (required)",
    )

    paddle_webhook_secret: str = Field(
        ...,
        alias="PADDLE_WEBHOOK_SECRET",
        description="Paddle webhook secret for signature verification (required)",
    )

    @field_validator("paddle_api_key")
    @classmethod
    def validate_paddle_api_key(cls, v: str) -> str:
        """Validate Paddle API key is present."""
        if not v:
            raise ValueError(
                "PADDLE_API_KEY is required. "
                "Get it from https://vendors.paddle.com/authentication-v2"
            )
        return v

    @field_validator("paddle_webhook_secret")
    @classmethod
    def validate_paddle_webhook_secret(cls, v: str) -> str:
        """Validate Paddle webhook secret is present."""
        if not v:
            raise ValueError(
                "PADDLE_WEBHOOK_SECRET is required. "
                "Get it from https://vendors.paddle.com/alerts-webhooks "
                "and ensure it matches your Paddle dashboard configuration."
            )
        return v

    # =============================================================================
    # Email Service (Resend)
    # =============================================================================
    resend_api_key: str = Field(
        ...,
        alias="RESEND_API_KEY",
        description="Resend API key for email delivery (required)",
    )

    @field_validator("resend_api_key")
    @classmethod
    def validate_resend_api_key(cls, v: str) -> str:
        """Validate Resend API key is present."""
        if not v:
            raise ValueError(
                "RESEND_API_KEY is required. "
                "Get it from https://resend.com/api-keys"
            )
        return v

    # =============================================================================
    # Blob Storage (Vercel Blob)
    # =============================================================================
    blob_read_write_token: str = Field(
        ...,
        alias="BLOB_READ_WRITE_TOKEN",
        description="Vercel Blob storage token for PDF storage (required)",
    )

    @field_validator("blob_read_write_token")
    @classmethod
    def validate_blob_token(cls, v: str) -> str:
        """Validate Vercel Blob token is present."""
        if not v:
            raise ValueError(
                "BLOB_READ_WRITE_TOKEN is required. "
                "Get it from https://vercel.com/dashboard/stores"
            )
        return v

    # =============================================================================
    # Admin Access Control
    # =============================================================================
    admin_api_key: str = Field(
        ...,
        alias="ADMIN_API_KEY",
        description="Admin API key for privileged operations (required)",
    )

    admin_ip_whitelist: str = Field(
        default="127.0.0.1,::1",
        alias="ADMIN_IP_WHITELIST",
        description="Comma-separated list of IP addresses allowed for admin access",
    )

    @field_validator("admin_api_key")
    @classmethod
    def validate_admin_api_key(cls, v: str) -> str:
        """Validate admin API key is present and sufficiently strong."""
        if not v:
            raise ValueError(
                "ADMIN_API_KEY is required. "
                "Generate a strong random key (minimum 32 characters) for admin access."
            )
        if len(v) < 32:
            raise ValueError(
                "ADMIN_API_KEY must be at least 32 characters long for security. "
                "Use a cryptographically secure random string."
            )
        return v

    @field_validator("admin_ip_whitelist")
    @classmethod
    def validate_admin_ip_whitelist(cls, v: str) -> str:
        """Validate IP whitelist format."""
        if not v:
            return "127.0.0.1,::1"  # Default to localhost only

        # Basic validation - split and trim
        ips = [ip.strip() for ip in v.split(",")]
        if not ips:
            raise ValueError(
                "ADMIN_IP_WHITELIST must contain at least one IP address"
            )

        return v

    # =============================================================================
    # Computed Properties
    # =============================================================================
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.env == "development"

    @property
    def admin_ips(self) -> list[str]:
        """Get list of whitelisted admin IPs."""
        return [ip.strip() for ip in self.admin_ip_whitelist.split(",")]


def validate_env() -> Settings:
    """
    Validate environment variables and return settings instance.

    This function should be called on application startup to ensure all
    required environment variables are present and valid.

    Returns:
        Settings: Validated settings instance

    Raises:
        ValidationError: If any required variables are missing or invalid,
            with detailed error messages for each validation failure.

    Example:
        >>> from src.lib.env import validate_env
        >>> try:
        ...     settings = validate_env()
        ...     print(f"✓ Environment validated for {settings.env}")
        ... except ValidationError as e:
        ...     print(f"✗ Environment validation failed:")
        ...     for error in e.errors():
        ...         print(f"  - {error['loc'][0]}: {error['msg']}")
        ...     raise
    """
    try:
        settings_instance = Settings()

        # Additional runtime validations
        if settings_instance.is_production:
            # In production, Sentry DSN should be configured
            if not settings_instance.sentry_backend_dsn:
                raise ValueError(
                    "SENTRY_BACKEND_DSN is required in production environment"
                )

        return settings_instance

    except ValidationError as e:
        # Re-format validation errors for better readability
        print("\n" + "=" * 80)
        print("ENVIRONMENT VALIDATION FAILED")
        print("=" * 80)
        print("\nThe following environment variables are missing or invalid:\n")

        for error in e.errors():
            field_name = error["loc"][0] if error["loc"] else "unknown"
            error_msg = error["msg"]
            print(f"  ✗ {field_name.upper()}: {error_msg}")

        print("\n" + "=" * 80)
        print("Please check your .env file and ensure all required variables are set.")
        print("See backend/.env.example for reference.")
        print("=" * 80 + "\n")

        raise


# =============================================================================
# Global Settings Instance
# =============================================================================
# This will be initialized on first import. If validation fails, the import
# will fail with clear error messages.
#
# For testing or delayed validation, import validate_env() instead and call
# it explicitly.
settings: Settings


def _initialize_settings() -> Settings:
    """Initialize settings on module import (if not in test mode)."""
    # Allow skipping validation in test environments
    if os.getenv("SKIP_ENV_VALIDATION") == "1":
        # Return a mock settings instance for testing
        return Settings(
            neon_database_url="postgresql://test:test@localhost/test",
            redis_url="redis://localhost:6379/0",
            paddle_api_key="test_paddle_key",
            paddle_webhook_secret="test_paddle_secret",
            resend_api_key="test_resend_key",
            blob_read_write_token="test_blob_token",
            admin_api_key="test_admin_key_with_sufficient_length_32chars",
            gemini_api_key="test_gemini_key",
        )

    return validate_env()


# Initialize settings on import (unless in test mode)
try:
    settings = _initialize_settings()
except ValidationError:
    # If validation fails on import, re-raise with context
    # This will prevent the application from starting with invalid config
    raise RuntimeError(
        "Failed to initialize application settings. "
        "Please check environment variables and try again."
    )
