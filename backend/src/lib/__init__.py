"""
Library Module

Utilities and helper functions for the backend application.

Modules:
- database.py: Async SQLAlchemy session management and Neon DB connection
- redis_client.py: Redis connection and distributed lock utilities
- email_utils.py: Email normalization and validation
- env.py: Environment variable validation
- ai_client.py: OpenAI Agents SDK client configuration
"""

from src.lib.ai_client import (
    setup_ai_client,
    get_ai_client,
    get_model_name,
    get_model_instance,
    reset_ai_client,
)

__all__ = [
    "setup_ai_client",
    "get_ai_client",
    "get_model_name",
    "get_model_instance",
    "reset_ai_client",
]
