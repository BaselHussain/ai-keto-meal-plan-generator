#!/usr/bin/env python3
"""
Redis Connection Test Script
Tests Upstash Redis connection with TLS support.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=env_path)
    print(f"Loaded environment from: {env_path}")
except ImportError:
    print("Warning: python-dotenv not installed. Using system environment variables.")


async def test_redis_connection():
    """Test Redis connection and basic operations."""
    print("=" * 60)
    print("Redis Connection Test")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}\n")

    try:
        # Import Redis client
        print("1. Importing redis_client module...")
        from src.lib.redis_client import get_redis, redis_health_check
        print("   ✓ Import successful\n")

        # Get Redis client instance
        print("2. Getting Redis client instance...")
        redis_client = await get_redis()
        print("   ✓ Redis client initialized\n")

        # Test health check
        print("3. Testing health check (redis_health_check)...")
        health_result = await redis_health_check()
        if health_result:
            print(f"   ✓ Health check passed: {health_result}\n")
        else:
            print(f"   ✗ Health check failed: {health_result}\n")
            return False

        # Test PING command
        print("4. Testing PING command...")
        ping_result = await redis_client.ping()
        if ping_result:
            print(f"   ✓ PING successful: {ping_result}\n")
        else:
            print(f"   ✗ PING failed\n")
            return False

        # Test SET operation
        print("5. Testing SET operation...")
        test_key = "test:connection:timestamp"
        test_value = datetime.now().isoformat()
        set_result = await redis_client.set(test_key, test_value, ex=60)
        if set_result:
            print(f"   ✓ SET successful: key='{test_key}', value='{test_value}'\n")
        else:
            print(f"   ✗ SET failed\n")
            return False

        # Test GET operation
        print("6. Testing GET operation...")
        get_result = await redis_client.get(test_key)
        # With decode_responses=True, get() returns str directly
        if get_result and get_result == test_value:
            print(f"   ✓ GET successful: retrieved value matches '{test_value}'\n")
        else:
            print(f"   ✗ GET failed or value mismatch\n")
            print(f"     Expected: {test_value}")
            print(f"     Got: {get_result}\n")
            return False

        # Test DELETE operation
        print("7. Testing DELETE operation...")
        del_result = await redis_client.delete(test_key)
        if del_result:
            print(f"   ✓ DELETE successful: {del_result} key(s) deleted\n")
        else:
            print(f"   ✗ DELETE failed\n")
            return False

        # Verify deletion
        print("8. Verifying deletion...")
        verify_result = await redis_client.get(test_key)
        if verify_result is None:
            print(f"   ✓ Deletion verified: key no longer exists\n")
        else:
            print(f"   ✗ Deletion verification failed: key still exists\n")
            return False

        # Get Redis info
        print("9. Retrieving Redis server info...")
        info = await redis_client.info()
        redis_version = info.get('redis_version', 'unknown')
        uptime_seconds = info.get('uptime_in_seconds', 'unknown')
        connected_clients = info.get('connected_clients', 'unknown')
        print(f"   Redis Version: {redis_version}")
        print(f"   Uptime: {uptime_seconds} seconds")
        print(f"   Connected Clients: {connected_clients}\n")

        print("=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        print("\nRedis connection is working correctly with TLS!")
        return True

    except ImportError as e:
        print(f"\n✗ Import Error: {e}")
        print("   Make sure you're running from the backend directory")
        print("   and all dependencies are installed.\n")
        return False

    except ConnectionError as e:
        print(f"\n✗ Connection Error: {e}")
        print("   Check REDIS_URL in .env file")
        print("   Ensure it uses rediss:// protocol for TLS\n")
        return False

    except Exception as e:
        print(f"\n✗ Unexpected Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


async def main():
    """Main entry point."""
    success = await test_redis_connection()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
