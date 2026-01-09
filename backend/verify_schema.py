"""
Verify Database Schema

This script verifies that all tables, indexes, and constraints were created correctly
after running the initial migration.
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


async def verify_schema():
    """Verify all tables, indexes, and constraints exist."""

    # Get database URL
    database_url = os.getenv("NEON_DATABASE_URL")
    if not database_url:
        print("ERROR: NEON_DATABASE_URL not set in .env file")
        return False

    # Convert to asyncpg format
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Create engine
    engine = create_async_engine(database_url, echo=False)

    try:
        async with engine.connect() as conn:
            print("=" * 80)
            print("DATABASE SCHEMA VERIFICATION")
            print("=" * 80)
            print()

            # Expected tables
            expected_tables = [
                "users",
                "quiz_responses",
                "meal_plans",
                "payment_transactions",
                "manual_resolution",
                "magic_link_tokens",
                "email_blacklist",
                "alembic_version",  # Alembic tracking table
            ]

            # Check tables exist
            print("1. Verifying Tables")
            print("-" * 80)
            result = await conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]

            for table in expected_tables:
                if table in tables:
                    print(f"  [OK] {table}")
                else:
                    print(f"  [MISSING] {table}")

            print()

            # Check indexes for each table
            print("2. Verifying Indexes")
            print("-" * 80)
            result = await conn.execute(text("""
                SELECT
                    tablename,
                    indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                ORDER BY tablename, indexname
            """))
            indexes = {}
            for row in result:
                table_name = row[0]
                index_name = row[1]
                if table_name not in indexes:
                    indexes[table_name] = []
                indexes[table_name].append(index_name)

            for table, table_indexes in sorted(indexes.items()):
                print(f"\n  {table}:")
                for idx in sorted(table_indexes):
                    print(f"    - {idx}")

            print()

            # Check foreign keys
            print("3. Verifying Foreign Keys")
            print("-" * 80)
            result = await conn.execute(text("""
                SELECT
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = 'public'
                ORDER BY tc.table_name, kcu.column_name
            """))

            fk_count = 0
            for row in result:
                table, column, ref_table, ref_column = row
                print(f"  [OK] {table}.{column} -> {ref_table}.{ref_column}")
                fk_count += 1

            if fk_count == 0:
                print("  No foreign keys found")

            print()

            # Check unique constraints
            print("4. Verifying Unique Constraints")
            print("-" * 80)
            result = await conn.execute(text("""
                SELECT
                    tc.table_name,
                    kcu.column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'UNIQUE'
                    AND tc.table_schema = 'public'
                ORDER BY tc.table_name, kcu.column_name
            """))

            unique_count = 0
            for row in result:
                table, column = row
                print(f"  [OK] {table}.{column}")
                unique_count += 1

            if unique_count == 0:
                print("  No unique constraints found")

            print()

            # Check current migration version
            print("5. Verifying Migration State")
            print("-" * 80)
            result = await conn.execute(text("""
                SELECT version_num FROM alembic_version
            """))
            version = result.scalar_one_or_none()
            if version:
                print(f"  Current migration version: {version}")
            else:
                print("  No migration version found!")

            print()
            print("=" * 80)
            print("VERIFICATION COMPLETE")
            print("=" * 80)

            return True

    except Exception as e:
        print(f"\nERROR during verification: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(verify_schema())
    exit(0 if success else 1)
