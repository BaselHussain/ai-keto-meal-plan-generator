"""
Phase 1 Validation Script

Tests all Phase 1.3 acceptance criteria:
1. Database connection established (Neon DB)
2. Redis ping succeeds
3. Sentry test errors logged

Also validates T013 completion:
- backend/src/lib/env.py exists and validates environment
- frontend/lib/env.ts exists and validates environment
"""

import asyncio
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Test Results Tracking
# =============================================================================
class TestResults:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def add_pass(self, test: str, message: str = ""):
        self.passed.append((test, message))
        logger.info(f"✓ {test}: {message or 'PASSED'}")

    def add_fail(self, test: str, error: str):
        self.failed.append((test, error))
        logger.error(f"✗ {test}: {error}")

    def add_warning(self, test: str, warning: str):
        self.warnings.append((test, warning))
        logger.warning(f"⚠️  {test}: {warning}")

    def print_summary(self):
        print("\n" + "=" * 80)
        print("PHASE 1 VALIDATION SUMMARY")
        print("=" * 80)

        print(f"\n✓ Passed: {len(self.passed)}")
        for test, msg in self.passed:
            print(f"  - {test}: {msg}")

        if self.warnings:
            print(f"\n⚠️  Warnings: {len(self.warnings)}")
            for test, msg in self.warnings:
                print(f"  - {test}: {msg}")

        if self.failed:
            print(f"\n✗ Failed: {len(self.failed)}")
            for test, msg in self.failed:
                print(f"  - {test}: {msg}")

        print("\n" + "=" * 80)

        if self.failed:
            print("❌ PHASE 1 VALIDATION FAILED")
            print("\nPlease fix the failed tests before proceeding to Phase 2.")
        elif self.warnings:
            print("⚠️  PHASE 1 VALIDATION PASSED WITH WARNINGS")
            print("\nConsider addressing warnings for production readiness.")
        else:
            print("✅ PHASE 1 VALIDATION PASSED")
            print("\nAll acceptance criteria met. Ready for Phase 2.")

        print("=" * 80 + "\n")


# =============================================================================
# Test 1: Environment Variables Validation
# =============================================================================
def test_env_variables(results: TestResults):
    """Test that all required environment variables are present and valid."""
    try:
        from src.lib.env import settings

        results.add_pass(
            "Environment Variables",
            f"All required variables validated (ENV={settings.env})",
        )

        # Check optional variables
        missing_optional = []
        if not settings.sentry_backend_dsn:
            missing_optional.append("SENTRY_BACKEND_DSN")
        if not settings.gemini_api_key and not settings.openai_api_key:
            missing_optional.append("GEMINI_API_KEY or OPEN_AI_API_KEY")

        if missing_optional:
            results.add_warning(
                "Optional Variables",
                f"Missing: {', '.join(missing_optional)} (OK for development)",
            )

    except Exception as e:
        results.add_fail("Environment Variables", str(e))


# =============================================================================
# Test 2: Database Connection (Neon DB)
# =============================================================================
async def test_database_connection(results: TestResults):
    """Test database connection to Neon DB."""
    try:
        from src.lib.database import init_db, health_check, close_db

        # Initialize database
        init_db()
        results.add_pass("Database Initialization", "Engine created successfully")

        # Health check
        health = await health_check()

        if health.get("status") == "healthy":
            pool_info = ""
            if "pool_size" in health:
                pool_info = f" (Pool: {health['pool_size']} connections)"
            results.add_pass("Database Connection", f"Connected to Neon DB{pool_info}")
        else:
            error = health.get("error", "Unknown error")
            results.add_fail("Database Connection", f"Health check failed: {error}")

        # Cleanup
        await close_db()

    except ValueError as e:
        # Missing environment variable
        results.add_fail("Database Connection", f"Configuration error: {e}")
    except Exception as e:
        results.add_fail("Database Connection", f"Connection failed: {e}")


# =============================================================================
# Test 3: Redis Connection
# =============================================================================
async def test_redis_connection(results: TestResults):
    """Test Redis connection and PING command."""
    try:
        from src.lib.redis_client import redis_health_check, close_redis

        # Health check (includes PING)
        is_healthy = await redis_health_check()

        if is_healthy:
            results.add_pass("Redis Connection", "PING succeeded")
        else:
            results.add_fail("Redis Connection", "PING failed or connection unavailable")

        # Cleanup
        await close_redis()

    except ValueError as e:
        # Missing environment variable
        results.add_fail("Redis Connection", f"Configuration error: {e}")
    except Exception as e:
        results.add_fail("Redis Connection", f"Connection failed: {e}")


# =============================================================================
# Test 4: Sentry Integration
# =============================================================================
def test_sentry_integration(results: TestResults):
    """Test Sentry error tracking integration."""
    try:
        import sentry_sdk
        from src.lib.env import settings

        if not settings.sentry_backend_dsn:
            results.add_warning(
                "Sentry Integration",
                "SENTRY_BACKEND_DSN not configured (OK for development)",
            )
            return

        # Initialize Sentry
        sentry_sdk.init(
            dsn=settings.sentry_backend_dsn,
            traces_sample_rate=0.0,  # Disable performance monitoring for test
            environment=settings.env,
            release=settings.sentry_release or "unknown",
        )

        # Send test error
        try:
            # Capture a test exception without raising it
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("test", "phase1_validation")
                scope.set_context("validation", {
                    "phase": "1",
                    "test": "sentry_integration",
                })
                sentry_sdk.capture_message(
                    "Phase 1 Validation Test: Sentry integration working",
                    level="info",
                )

            results.add_pass("Sentry Integration", "Test event sent successfully")

        except Exception as e:
            results.add_fail("Sentry Integration", f"Failed to send test event: {e}")

    except Exception as e:
        results.add_fail("Sentry Integration", f"Initialization failed: {e}")


# =============================================================================
# Test 5: T013 - Environment Module Existence
# =============================================================================
def test_t013_completion(results: TestResults):
    """Test that T013 environment validation modules exist."""
    backend_env_path = Path(__file__).parent / "src" / "lib" / "env.py"
    frontend_env_path = Path(__file__).parent.parent / "frontend" / "lib" / "env.ts"

    # Check backend env.py
    if backend_env_path.exists():
        results.add_pass("T013 Backend", "src/lib/env.py exists")
    else:
        results.add_fail("T013 Backend", "src/lib/env.py not found")

    # Check frontend env.ts
    if frontend_env_path.exists():
        results.add_pass("T013 Frontend", "frontend/lib/env.ts exists")
    else:
        results.add_fail("T013 Frontend", "frontend/lib/env.ts not found")


# =============================================================================
# Main Validation Runner
# =============================================================================
async def main():
    """Run all Phase 1 validation tests."""
    print("\n" + "=" * 80)
    print("PHASE 1 VALIDATION - STARTING")
    print("=" * 80 + "\n")

    results = TestResults()

    # Test 1: Environment variables
    print("Test 1: Environment Variables Validation")
    print("-" * 80)
    test_env_variables(results)
    print()

    # Test 2: Database connection
    print("Test 2: Database Connection (Neon DB)")
    print("-" * 80)
    await test_database_connection(results)
    print()

    # Test 3: Redis connection
    print("Test 3: Redis Connection")
    print("-" * 80)
    await test_redis_connection(results)
    print()

    # Test 4: Sentry integration
    print("Test 4: Sentry Integration")
    print("-" * 80)
    test_sentry_integration(results)
    print()

    # Test 5: T013 completion
    print("Test 5: T013 - Environment Module Existence")
    print("-" * 80)
    test_t013_completion(results)
    print()

    # Print summary
    results.print_summary()

    # Exit with appropriate code
    sys.exit(0 if not results.failed else 1)


if __name__ == "__main__":
    asyncio.run(main())
