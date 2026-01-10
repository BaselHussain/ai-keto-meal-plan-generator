#!/usr/bin/env python3
"""
Phase 1 Acceptance Criteria Verification Script

Tests:
1. Database connection (Neon DB via SQLAlchemy)
2. Redis connection
3. Sentry integration
4. Environment validation utilities
"""

import sys
import os
import asyncio
from typing import Dict, List, Tuple
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv

# Get the backend directory path
backend_dir = Path(__file__).parent
env_path = backend_dir / ".env"

# Load .env file
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"Loaded environment from: {env_path}")
else:
    print(f"WARNING: .env file not found at {env_path}")


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def print_result(test_name: str, passed: bool, message: str = "") -> None:
    """Print a test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if message:
        print(f"         {message}")


async def test_database_connection() -> Tuple[bool, str]:
    """Test database connection to Neon DB."""
    try:
        from src.lib.database import init_db, get_db, close_db, get_engine
        from sqlalchemy import text

        # Initialize database
        init_db()

        # Get engine
        engine = get_engine()
        if engine is None:
            return False, "Database engine not initialized"

        # Test connection using get_db dependency
        async for session in get_db():
            # Execute simple query
            result = await session.execute(text("SELECT 1 as test"))
            row = result.first()

            if row is None or row.test != 1:
                await close_db()
                return False, "Query did not return expected result"

            # Session cleanup handled by get_db
            break

        await close_db()
        return True, "Database connection successful"
    except Exception as e:
        return False, f"Error: {str(e)}"


async def test_redis_connection() -> Tuple[bool, str]:
    """Test Redis connection."""
    try:
        from src.lib.redis_client import get_redis, redis_health_check, close_redis

        # Test health check
        is_healthy = await redis_health_check()
        if not is_healthy:
            return False, "Redis health check failed"

        # Get Redis client
        redis = await get_redis()

        # Test set/get
        test_key = "phase1:test"
        test_value = "verification"

        await redis.set(test_key, test_value, ex=60)
        retrieved = await redis.get(test_key)

        if retrieved is None:
            await close_redis()
            return False, "Failed to retrieve test value from Redis"

        if retrieved != test_value:
            await close_redis()
            return False, f"Retrieved value mismatch: {retrieved}"

        # Cleanup
        await redis.delete(test_key)
        await close_redis()

        return True, "Redis connection and operations successful"
    except Exception as e:
        return False, f"Error: {str(e)}"


async def test_sentry_integration() -> Tuple[bool, str]:
    """Test Sentry integration by capturing a test error."""
    try:
        import sentry_sdk
        from src.lib.env import settings

        if not settings.sentry_backend_dsn:
            return False, "SENTRY_BACKEND_DSN not configured in environment"

        # Initialize Sentry for this test
        sentry_sdk.init(
            dsn=settings.sentry_backend_dsn,
            environment=settings.env,
            release=settings.sentry_release,
            traces_sample_rate=0.0,  # Disable performance monitoring for test
        )

        # Check if Sentry is initialized
        client = sentry_sdk.Hub.current.client
        if client is None:
            return False, "Sentry client not initialized"

        # Capture a test message
        event_id = sentry_sdk.capture_message(
            "Phase 1 Verification Test - This is a test message",
            level="info"
        )

        # Flush to ensure the message is sent
        sentry_sdk.flush(timeout=2.0)

        if event_id:
            return True, f"Test message sent to Sentry (Event ID: {event_id})"
        else:
            return False, "Failed to capture test message"
    except Exception as e:
        return False, f"Error: {str(e)}"


async def test_env_validation_files() -> Tuple[bool, str]:
    """Test that environment validation utilities exist."""
    import os

    backend_env_path = "/mnt/f/saas projects/ai-based-meal-plan/backend/src/lib/env.py"
    frontend_env_path = "/mnt/f/saas projects/ai-based-meal-plan/frontend/lib/env.ts"

    missing_files: List[str] = []

    if not os.path.exists(backend_env_path):
        missing_files.append("backend/src/lib/env.py")

    if not os.path.exists(frontend_env_path):
        missing_files.append("frontend/lib/env.ts")

    if missing_files:
        return False, f"Missing files: {', '.join(missing_files)}"

    return True, "All environment validation files exist"


async def test_env_settings_validation() -> Tuple[bool, str]:
    """Test that environment settings are properly validated."""
    try:
        from src.lib.env import settings

        # Just check if settings object was created successfully
        # The fact that we got here means validation passed
        if settings:
            return True, "Environment settings validated successfully"
        else:
            return False, "Settings object is None"
    except Exception as e:
        return False, f"Error: {str(e)}"


async def main() -> int:
    """Run all verification tests."""
    print_header("Phase 1 Acceptance Criteria Verification")

    tests: Dict[str, Tuple[bool, str]] = {}

    # Run all tests
    print("Running tests...\n")

    tests["Database Connection (Neon DB)"] = await test_database_connection()
    tests["Redis Connection"] = await test_redis_connection()
    tests["Sentry Integration"] = await test_sentry_integration()
    tests["Environment Validation Files"] = await test_env_validation_files()
    tests["Environment Settings Validation"] = await test_env_settings_validation()

    # Print results
    print_header("Test Results")

    passed_count = 0
    failed_count = 0

    for test_name, (passed, message) in tests.items():
        print_result(test_name, passed, message)
        if passed:
            passed_count += 1
        else:
            failed_count += 1

    # Summary
    print_header("Summary")
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {failed_count}")

    if failed_count == 0:
        print("\n🎉 All Phase 1 acceptance criteria verified successfully!")
        return 0
    else:
        print(f"\n⚠️  {failed_count} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
