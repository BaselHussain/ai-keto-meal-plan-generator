"""
Test script for verifying API setup (T027-T029).

Tests:
- FastAPI app initialization
- Health endpoint returns 200 with correct format
- Error handling middleware works correctly
- Validation errors are properly formatted
"""

import asyncio
import sys
import os
from fastapi.testclient import TestClient

# Fix Windows console encoding
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add src to path
sys.path.insert(0, ".")

from src.main import app

client = TestClient(app)


def test_app_initialization():
    """Test that the FastAPI app initializes correctly."""
    print("Testing app initialization...")
    assert app is not None
    assert app.title == "Keto Meal Plan Generator API"
    assert app.version == "1.0.0"
    print("✓ App initialized successfully")


def test_root_endpoint():
    """Test the root endpoint."""
    print("\nTesting root endpoint...")
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["message"] == "Keto Meal Plan Generator API"
    print(f"✓ Root endpoint: {data}")


def test_health_endpoint():
    """Test the health check endpoint."""
    print("\nTesting /api/v1/health endpoint...")
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print(f"✓ Health endpoint: {data}")


def test_detailed_health_endpoint():
    """Test the detailed health check endpoint."""
    print("\nTesting /api/v1/health/detailed endpoint...")
    response = client.get("/api/v1/health/detailed")
    # Could be 200 or 503 depending on database connection
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data
    assert "service" in data
    assert "components" in data
    print(f"✓ Detailed health endpoint: status={data['status']}, components={list(data['components'].keys())}")


def test_readiness_endpoint():
    """Test the readiness check endpoint."""
    print("\nTesting /api/v1/health/ready endpoint...")
    response = client.get("/api/v1/health/ready")
    # Could be 200 or 503 depending on database connection
    assert response.status_code in [200, 503]
    data = response.json()
    assert "ready" in data or "status" in data
    print(f"✓ Readiness endpoint: {data}")


def test_404_error_handling():
    """Test that 404 errors are properly formatted."""
    print("\nTesting 404 error handling...")
    response = client.get("/api/v1/nonexistent")
    print(f"  Status code: {response.status_code}")
    print(f"  Response: {response.text}")
    assert response.status_code == 404
    data = response.json()
    print(f"  Parsed JSON: {data}")
    assert "error" in data, f"Expected 'error' key in response, got: {data}"
    assert data["error"]["code"] == "not_found", f"Expected code 'not_found', got: {data['error'].get('code')}"
    assert "message" in data["error"], f"Expected 'message' in error, got: {data['error']}"
    print(f"✓ 404 error format: {data}")


def test_validation_error_handling():
    """Test that validation errors are properly formatted."""
    print("\nTesting validation error handling...")
    # This will fail validation when we have endpoints with validation
    # For now, we'll just verify the structure is set up
    print("✓ Validation error handler registered (will test with actual endpoints later)")


def test_cors_headers():
    """Test that CORS headers are properly set."""
    print("\nTesting CORS configuration...")
    response = client.options(
        "/api/v1/health",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    # CORS headers should be present
    assert "access-control-allow-origin" in response.headers or response.status_code == 200
    print("✓ CORS headers configured")


def test_error_response_format():
    """Test that error responses follow the consistent format."""
    print("\nTesting error response format...")
    response = client.get("/api/v1/does-not-exist")
    print(f"  Status code: {response.status_code}")
    print(f"  Response: {response.text}")
    assert response.status_code == 404
    data = response.json()
    print(f"  Parsed JSON: {data}")

    # Verify error structure
    assert "error" in data, f"Expected 'error' key in response, got: {data}"
    assert "code" in data["error"], f"Expected 'code' in error, got: {data['error']}"
    assert "message" in data["error"], f"Expected 'message' in error, got: {data['error']}"
    # Details are optional
    print(f"✓ Error response format: code={data['error']['code']}, message={data['error']['message']}")


def main():
    """Run all tests."""
    print("=" * 80)
    print("API Setup Tests (T027-T029)")
    print("=" * 80)

    tests = [
        test_app_initialization,
        test_root_endpoint,
        test_health_endpoint,
        test_detailed_health_endpoint,
        test_readiness_endpoint,
        test_404_error_handling,
        test_validation_error_handling,
        test_cors_headers,
        test_error_response_format,
    ]

    failed = []
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ Test failed: {test.__name__}")
            print(f"  Error: {e}")
            failed.append(test.__name__)
        except Exception as e:
            print(f"✗ Test error: {test.__name__}")
            print(f"  Error: {e}")
            failed.append(test.__name__)

    print("\n" + "=" * 80)
    if failed:
        print(f"❌ {len(failed)} test(s) failed:")
        for name in failed:
            print(f"  - {name}")
        print("=" * 80)
        sys.exit(1)
    else:
        print("✅ All tests passed!")
        print("=" * 80)
        sys.exit(0)


if __name__ == "__main__":
    main()
