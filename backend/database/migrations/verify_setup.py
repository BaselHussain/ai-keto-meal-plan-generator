#!/usr/bin/env python3
"""
Verification script for Alembic migration setup.

This script validates that the Alembic configuration is correct and ready for use.
Run this script to ensure the migration environment is properly configured.

Usage:
    python database/migrations/verify_setup.py
"""

import os
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


def check_env_file() -> bool:
    """Check if .env file exists and contains NEON_DATABASE_URL."""
    env_path = backend_dir / ".env"
    if not env_path.exists():
        print("❌ .env file not found at:", env_path)
        return False

    with open(env_path) as f:
        content = f.read()
        if "NEON_DATABASE_URL" not in content:
            print("❌ NEON_DATABASE_URL not found in .env file")
            return False

    print("✅ .env file exists with NEON_DATABASE_URL")
    return True


def check_database_url() -> bool:
    """Check if NEON_DATABASE_URL environment variable is set."""
    from dotenv import load_dotenv

    env_path = backend_dir / ".env"
    load_dotenv(dotenv_path=env_path)

    db_url = os.getenv("NEON_DATABASE_URL")
    if not db_url:
        print("❌ NEON_DATABASE_URL environment variable not set")
        return False

    if not db_url.startswith("postgresql://"):
        print("❌ NEON_DATABASE_URL does not start with postgresql://")
        return False

    print("✅ NEON_DATABASE_URL is properly configured")
    return True


def check_directory_structure() -> bool:
    """Check if required directories exist."""
    required_dirs = [
        backend_dir / "database",
        backend_dir / "database" / "migrations",
        backend_dir / "database" / "migrations" / "versions",
    ]

    for directory in required_dirs:
        if not directory.exists():
            print(f"❌ Required directory not found: {directory}")
            return False

    print("✅ All required directories exist")
    return True


def check_required_files() -> bool:
    """Check if required configuration files exist."""
    required_files = [
        backend_dir / "alembic.ini",
        backend_dir / "database" / "migrations" / "env.py",
        backend_dir / "database" / "migrations" / "script.py.mako",
    ]

    for file_path in required_files:
        if not file_path.exists():
            print(f"❌ Required file not found: {file_path}")
            return False

    print("✅ All required configuration files exist")
    return True


def check_alembic_config() -> bool:
    """Check if alembic.ini is properly configured."""
    alembic_ini = backend_dir / "alembic.ini"

    with open(alembic_ini) as f:
        content = f.read()

        if "script_location = %(here)s/database/migrations" not in content:
            print("❌ alembic.ini script_location is not configured correctly")
            return False

    print("✅ alembic.ini is properly configured")
    return True


def check_alembic_import() -> bool:
    """Check if Alembic can be imported."""
    try:
        import alembic
        print(f"✅ Alembic is installed (version: {alembic.__version__})")
        return True
    except ImportError:
        print("❌ Alembic is not installed")
        return False


def check_sqlalchemy_import() -> bool:
    """Check if SQLAlchemy can be imported."""
    try:
        import sqlalchemy
        print(f"✅ SQLAlchemy is installed (version: {sqlalchemy.__version__})")
        return True
    except ImportError:
        print("❌ SQLAlchemy is not installed")
        return False


def check_asyncpg_import() -> bool:
    """Check if asyncpg can be imported."""
    try:
        import asyncpg
        print(f"✅ asyncpg is installed (version: {asyncpg.__version__})")
        return True
    except ImportError:
        print("❌ asyncpg is not installed")
        return False


def main() -> int:
    """Run all verification checks."""
    print("=" * 60)
    print("Alembic Migration Setup Verification")
    print("=" * 60)
    print()

    checks = [
        ("Environment File", check_env_file),
        ("Database URL", check_database_url),
        ("Directory Structure", check_directory_structure),
        ("Configuration Files", check_required_files),
        ("Alembic Configuration", check_alembic_config),
        ("Alembic Package", check_alembic_import),
        ("SQLAlchemy Package", check_sqlalchemy_import),
        ("asyncpg Package", check_asyncpg_import),
    ]

    results = []
    for check_name, check_func in checks:
        print(f"\nChecking: {check_name}")
        print("-" * 40)
        results.append(check_func())
        print()

    print("=" * 60)
    print("Verification Summary")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✅ All checks passed ({passed}/{total})")
        print("\n✨ Alembic migration setup is ready!")
        print("\nNext steps:")
        print("  1. Create SQLAlchemy models in database/models/")
        print("  2. Import Base metadata in database/migrations/env.py")
        print("  3. Generate initial migration: alembic revision --autogenerate -m 'Initial schema'")
        print("  4. Review and apply migration: alembic upgrade head")
        return 0
    else:
        print(f"❌ {total - passed} check(s) failed ({passed}/{total} passed)")
        print("\n⚠️  Please fix the issues above before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
