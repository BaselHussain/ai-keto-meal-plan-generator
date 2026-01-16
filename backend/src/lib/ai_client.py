"""
AI Client Configuration for OpenAI Agents SDK

This module provides environment-based configuration for the AI client:
- Development: Uses Gemini API via OpenAI-compatible endpoint
- Production: Uses OpenAI API directly

Following research.md lines 67-80 for environment-based model selection.
"""

import os
import logging
from typing import Optional

from agents import set_default_openai_client, set_default_openai_key, set_default_openai_api, OpenAIChatCompletionsModel
from openai import AsyncOpenAI

# Configure logging
logger = logging.getLogger(__name__)

# Global client instance (singleton pattern)
_ai_client: Optional[AsyncOpenAI] = None


def setup_ai_client() -> AsyncOpenAI:
    """
    Configure AsyncOpenAI client based on environment.

    Environment Selection:
    - Production (ENV=production): OpenAI API with OPENAI_API_KEY
    - Development (default): Gemini API via OpenAI-compatible endpoint with GEMINI_API_KEY

    Returns:
        AsyncOpenAI: Configured AI client

    Raises:
        ValueError: If required API key is missing

    Examples:
        >>> client = setup_ai_client()
        >>> # Client is now ready for Agent SDK usage
    """
    global _ai_client

    # Return existing client if already configured (singleton)
    if _ai_client is not None:
        logger.debug("Returning existing AI client")
        return _ai_client

    env = os.getenv("ENV", "development").lower()

    if env == "production":
        # Production: OpenAI API
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            error_msg = "OPENAI_API_KEY environment variable not set for production"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info("Configuring OpenAI client for production")
        _ai_client = AsyncOpenAI(api_key=api_key)

        # Set as default with tracing enabled for OpenAI
        set_default_openai_client(_ai_client, use_for_tracing=True)

    else:
        # Development: Gemini API via OpenAI-compatible endpoint
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            error_msg = "GEMINI_API_KEY environment variable not set for development"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info("Configuring Gemini client for development")
        _ai_client = AsyncOpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=api_key
        )

        # Set as default WITHOUT tracing (Gemini doesn't support OpenAI tracing API)
        set_default_openai_client(_ai_client, use_for_tracing=False)

    logger.info(f"AI client configured successfully for {env} environment")
    return _ai_client


def get_ai_client() -> AsyncOpenAI:
    """
    Get the configured AI client instance.

    Returns:
        AsyncOpenAI: The configured AI client

    Raises:
        RuntimeError: If client is not yet configured

    Examples:
        >>> client = get_ai_client()
        >>> # Use client for AI operations
    """
    if _ai_client is None:
        raise RuntimeError(
            "AI client not configured. Call setup_ai_client() first."
        )
    return _ai_client


def get_model_name() -> str:
    """
    Get the appropriate model name based on environment.

    Returns:
        str: Model name to use (gpt-4o for production, gemini-2.5-flash for development)

    Examples:
        >>> model = get_model_name()
        >>> print(model)
        'gemini-2.5-flash'  # In development
    """
    env = os.getenv("ENV", "development").lower()

    if env == "production":
        return "gpt-4o"
    else:
        return "gemini-2.5-flash"


def get_model_instance():
    """
    Get the appropriate model instance for Agent SDK usage.

    For OpenAI (production): Returns model name string (supports Responses API)
    For Gemini (development): Returns OpenAIChatCompletionsModel instance (Responses API not supported)

    Returns:
        str | OpenAIChatCompletionsModel: Model instance to use with Agent

    Raises:
        RuntimeError: If client is not yet configured

    Examples:
        >>> model = get_model_instance()
        >>> agent = Agent(name="...", instructions="...", model=model)
    """
    env = os.getenv("ENV", "development").lower()

    if env == "production":
        # OpenAI supports Responses API - use model name string
        return get_model_name()
    else:
        # Gemini doesn't support Responses API - use ChatCompletionsModel
        client = get_ai_client()  # Ensure client is configured
        return OpenAIChatCompletionsModel(
            model=get_model_name(),
            openai_client=client
        )


def reset_ai_client() -> None:
    """
    Reset the AI client singleton (useful for testing).

    Examples:
        >>> reset_ai_client()
        >>> # Client will be reconfigured on next setup_ai_client() call
    """
    global _ai_client
    _ai_client = None
    logger.debug("AI client reset")
