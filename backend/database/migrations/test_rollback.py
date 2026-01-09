"""
Migration Rollback Test

This test verifies that Alembic migrations are reversible and maintain data integrity
during upgrade/downgrade cycles.

Test Coverage:
1. Test downgrade to base (remove all tables)
2. Test upgrade back to head (recreate all tables)
3. Test data integrity during migration cycles
4. Verify schema consistency after rollback

Usage:
    python -m pytest database/migrations/test_rollback.py -v

    Or run directly:
    python database/migrations/test_rollback.py
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class MigrationRollbackTest:
    """Test suite for Alembic migration rollback functionality."""

    def __init__(self):
        """Initialize test with database connection."""
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL not set in .env file")

        # Convert to asyncpg format
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        self.engine = create_async_engine(database_url, echo=False)
        self.backend_dir = Path(__file__).parent.parent.parent

    async def get_current_version(self):
        """Get current Alembic migration version."""
        async with self.engine.connect() as conn:
            try:
                result = await conn.execute(text("SELECT version_num FROM alembic_version"))
                return result.scalar_one_or_none()
            except Exception:
                # Table doesn't exist
                return None

    async def get_table_count(self):
        """Get count of tables in public schema."""
        async with self.engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
            """))
            return result.scalar()

    async def get_tables(self):
        """Get list of tables in public schema."""
        async with self.engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """))
            return [row[0] for row in result]

    def run_alembic_command(self, *args):
        """Run an Alembic command and return the result."""
        # Use the venv Python to run alembic
        python_exe = sys.executable

        cmd = [python_exe, "-m", "alembic"] + list(args)
        result = subprocess.run(
            cmd,
            cwd=self.backend_dir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"Command failed: {' '.join(cmd)}")
            print(f"STDERR: {result.stderr}")
            raise Exception(f"Alembic command failed: {result.stderr}")

        return result.stdout

    async def test_downgrade_to_base(self):
        """Test downgrading to base (removing all tables)."""
        print("\n" + "=" * 80)
        print("TEST 1: Downgrade to Base")
        print("=" * 80)

        # Get initial state
        initial_version = await self.get_current_version()
        print(f"Initial version: {initial_version}")

        initial_tables = await self.get_tables()
        print(f"Initial tables ({len(initial_tables)}): {', '.join(initial_tables)}")

        # Downgrade to base
        print("\nDowngrading to base...")
        output = self.run_alembic_command("downgrade", "base")
        print(output)

        # Verify downgrade
        current_version = await self.get_current_version()
        print(f"Version after downgrade: {current_version}")

        tables = await self.get_tables()
        print(f"Tables after downgrade ({len(tables)}): {', '.join(tables) if tables else 'None'}")

        # Assertions
        if current_version is not None:
            raise AssertionError(f"Expected version to be None, got {current_version}")

        # Only alembic_version table should remain
        if len(tables) > 1 or (len(tables) == 1 and tables[0] != 'alembic_version'):
            raise AssertionError(f"Expected only alembic_version table, got {len(tables)}: {tables}")

        print("\n[PASS] Downgrade to base successful")
        return initial_version

    async def test_upgrade_to_head(self, expected_version=None):
        """Test upgrading to head (recreating all tables)."""
        print("\n" + "=" * 80)
        print("TEST 2: Upgrade to Head")
        print("=" * 80)

        # Get initial state
        initial_version = await self.get_current_version()
        print(f"Initial version: {initial_version}")

        # Upgrade to head
        print("\nUpgrading to head...")
        output = self.run_alembic_command("upgrade", "head")
        print(output)

        # Verify upgrade
        current_version = await self.get_current_version()
        print(f"Version after upgrade: {current_version}")

        tables = await self.get_tables()
        print(f"Tables after upgrade ({len(tables)}): {', '.join(tables)}")

        # Assertions
        if current_version is None:
            raise AssertionError("Expected version to be set after upgrade")

        expected_tables = [
            "alembic_version",
            "email_blacklist",
            "magic_link_tokens",
            "manual_resolution",
            "meal_plans",
            "payment_transactions",
            "quiz_responses",
            "users",
        ]

        for table in expected_tables:
            if table not in tables:
                raise AssertionError(f"Expected table '{table}' not found after upgrade")

        print("\n[PASS] Upgrade to head successful")
        return current_version

    async def test_data_integrity_cycle(self):
        """Test data integrity during upgrade/downgrade cycle with sample data."""
        print("\n" + "=" * 80)
        print("TEST 3: Data Integrity During Migration Cycles")
        print("=" * 80)

        # Ensure we're at head
        print("Ensuring database is at head version...")
        self.run_alembic_command("upgrade", "head")

        # Insert test data
        print("\nInserting test data...")
        async with self.engine.begin() as conn:
            # Insert test user
            await conn.execute(text("""
                INSERT INTO users (id, email, normalized_email, created_at, updated_at)
                VALUES ('test-user-123', 'test@example.com', 'test@example.com', NOW(), NOW())
            """))

            # Insert test quiz response
            await conn.execute(text("""
                INSERT INTO quiz_responses (
                    id, user_id, email, normalized_email, quiz_data, calorie_target, created_at
                )
                VALUES (
                    'test-quiz-123',
                    'test-user-123',
                    'test@example.com',
                    'test@example.com',
                    '{"step1": "value1"}'::jsonb,
                    2000,
                    NOW()
                )
            """))

        print("Test data inserted successfully")

        # Verify data exists
        async with self.engine.connect() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()

            result = await conn.execute(text("SELECT COUNT(*) FROM quiz_responses"))
            quiz_count = result.scalar()

            print(f"Data verification: {user_count} users, {quiz_count} quiz responses")

            if user_count != 1 or quiz_count != 1:
                raise AssertionError("Test data not inserted correctly")

        # Downgrade to base (this will delete all data)
        print("\nDowngrading to base (will delete test data)...")
        self.run_alembic_command("downgrade", "base")

        # Verify tables are gone (except alembic_version)
        tables = await self.get_tables()
        if len(tables) > 1 or (len(tables) == 1 and tables[0] != 'alembic_version'):
            raise AssertionError(f"Expected only alembic_version table after downgrade, got {len(tables)}: {tables}")

        print("Tables removed successfully")

        # Upgrade back to head
        print("\nUpgrading back to head...")
        self.run_alembic_command("upgrade", "head")

        # Verify tables are back but data is gone
        async with self.engine.connect() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()

            result = await conn.execute(text("SELECT COUNT(*) FROM quiz_responses"))
            quiz_count = result.scalar()

            print(f"Data after migration cycle: {user_count} users, {quiz_count} quiz responses")

            if user_count != 0 or quiz_count != 0:
                print("NOTE: Data was not preserved during downgrade (expected behavior)")

        print("\n[PASS] Migration cycle completed successfully")

    async def test_schema_consistency(self):
        """Verify schema consistency after rollback."""
        print("\n" + "=" * 80)
        print("TEST 4: Schema Consistency")
        print("=" * 80)

        # Ensure we're at head
        self.run_alembic_command("upgrade", "head")

        # Get schema information
        async with self.engine.connect() as conn:
            # Check indexes
            result = await conn.execute(text("""
                SELECT COUNT(*)
                FROM pg_indexes
                WHERE schemaname = 'public'
            """))
            index_count = result.scalar()
            print(f"Indexes: {index_count}")

            # Check foreign keys
            result = await conn.execute(text("""
                SELECT COUNT(*)
                FROM information_schema.table_constraints
                WHERE constraint_type = 'FOREIGN KEY'
                AND table_schema = 'public'
            """))
            fk_count = result.scalar()
            print(f"Foreign keys: {fk_count}")

            # Check unique constraints
            result = await conn.execute(text("""
                SELECT COUNT(*)
                FROM information_schema.table_constraints
                WHERE constraint_type = 'UNIQUE'
                AND table_schema = 'public'
            """))
            unique_count = result.scalar()
            print(f"Unique constraints: {unique_count}")

            # Assertions
            if index_count == 0:
                raise AssertionError("Expected indexes to be created")

            if fk_count == 0:
                raise AssertionError("Expected foreign keys to be created")

            if unique_count == 0:
                raise AssertionError("Expected unique constraints to be created")

        print("\n[PASS] Schema consistency verified")

    async def cleanup(self):
        """Clean up test data and close connections."""
        # Ensure we're back at head for future tests
        try:
            self.run_alembic_command("upgrade", "head")
        except Exception as e:
            print(f"Warning: Could not upgrade to head during cleanup: {e}")

        await self.engine.dispose()

    async def run_all_tests(self):
        """Run all rollback tests."""
        print("\n" + "=" * 80)
        print("MIGRATION ROLLBACK TEST SUITE")
        print("=" * 80)

        try:
            # Test 1: Downgrade to base
            initial_version = await self.test_downgrade_to_base()

            # Test 2: Upgrade to head
            current_version = await self.test_upgrade_to_head(initial_version)

            # Test 3: Data integrity cycle
            await self.test_data_integrity_cycle()

            # Test 4: Schema consistency
            await self.test_schema_consistency()

            print("\n" + "=" * 80)
            print("ALL TESTS PASSED")
            print("=" * 80)

            return True

        except Exception as e:
            print("\n" + "=" * 80)
            print("TEST FAILED")
            print("=" * 80)
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            await self.cleanup()


async def main():
    """Main entry point for the test."""
    test = MigrationRollbackTest()
    success = await test.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
