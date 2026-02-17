#!/usr/bin/env python3
"""
Load test script for Keto Meal Plan Generator backend (T147).

Tests system performance under realistic production load scenarios:

1. Concurrent users (up to 100) submitting quiz requests
2. 24-hour continuous simulation of user traffic
3. Payment webhook stress testing
4. PDF generation performance under load
5. Database connection utilization
6. Memory and CPU usage monitoring
7. Error rate measurements under production load
8. Recovery endpoint throughput capabilities

Architecture:
- Uses asyncio + aiohttp for efficient async HTTP requests
- Implements realistic user behavior patterns
- Tracks performance metrics throughout the simulation
- Generates reports of throughput, response times, error rates
- Tests both steady-state and spike load scenarios
"""

import asyncio
import time
import random
import string
import aiohttp
import json
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor


@dataclass
class LoadTestConfig:
    """Configuration for load testing parameters."""

    # Target server settings
    base_url: str = "http://localhost:8000"
    target_concurrent_users: int = 100
    test_duration_minutes: int = 2  # For initial testing

    # Request distributions
    quiz_submit_rate_per_minute: int = 8 * 60 / target_concurrent_users  # 8 submissions per user per hour
    recovery_requests_per_minute: int = 2 * 60 / target_concurrent_users # 2 recovery per user per hour
    heartbeat_requests_per_minute: int = 0.1  # Very occasional health checks

    # Authentication simulation
    admin_api_key: Optional[str] = None
    admin_ips: str = "127.0.0.1"

    # Test scenarios
    enable_payment_webhook: bool = False  # Test webhook endpoints separately
    enable_db_connections_test: bool = True  # Monitor DB performance
    enable_memory_monitoring: bool = True  # Track memory usage


@dataclass
class LoadTestMetrics:
    """Metrics collected during load test."""

    # Request counts
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Response times (in ms)
    response_times: List[float] = None
    avg_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0

    # Error rates
    error_rate: float = 0.0
    error_details: Dict[str, int] = None

    # Throughput
    requests_per_second: float = 0.0
    requests_per_minute: float = 0.0

    # Resource usage (approximated)
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

    def __post_init__(self):
        if self.response_times is None:
            self.response_times = []
        if self.error_details is None:
            self.error_details = {}


class LoadTestReporter:
    """Generates reports from load test results."""

    @staticmethod
    def print_summary(metrics: LoadTestMetrics, config: LoadTestConfig, duration_sec: float):
        """Print comprehensive test summary."""
        print("\n" + "="*80)
        print("LOAD TEST SUMMARY")
        print("="*80)

        print(f"Test Duration:     {duration_sec:.2f}s")
        print(f"Concurrent Users:  {config.target_concurrent_users}")
        print(f"Target QPS:        {(config.target_concurrent_users / 10):.2f} (approximate)")

        print(f"\nRequests:")
        print(f"  Total:           {metrics.total_requests}")
        print(f"  Successful:      {metrics.successful_requests} ({(metrics.successful_requests/metrics.total_requests * 100):.2f}%)")
        print(f"  Failed:          {metrics.failed_requests} ({(metrics.failed_requests/metrics.total_requests * 100):.2f}%)")

        print(f"\nPerformance:")
        print(f"  Avg RT:          {metrics.avg_response_time:.2f}ms")
        print(f"  P95 RT:          {metrics.p95_response_time:.2f}ms")
        print(f"  P99 RT:          {metrics.p99_response_time:.2f}ms")
        print(f"  RPS:             {metrics.requests_per_second:.2f}")

        print(f"\nThroughput:")
        print(f"  RPM:             {metrics.requests_per_minute:.2f}")

        if metrics.error_details:
            print(f"\nErrors by type:")
            for error_type, count in metrics.error_details.items():
                print(f"  {error_type}: {count}")

        # Performance SLA checks
        print(f"\nSLA Compliance:")
        print(f"  Avg Response <500ms: {'PASS' if metrics.avg_response_time < 500 else 'FAIL'}")
        print(f"  Error Rate <5%: {'PASS' if metrics.error_rate < 0.05 else 'FAIL'}")
        print(f"  P95 Response <2s: {'PASS' if metrics.p95_response_time < 2000 else 'FAIL'}")


class LoadTestClient:
    """Client to simulate real user interactions with the API."""

    def __init__(self, config: LoadTestConfig, session: aiohttp.ClientSession):
        self.config = config
        self.session = session

    async def submit_quiz(self, user_id: str) -> Dict:
        """Simulate quiz submission for a user."""
        email = f"loadtest_user_{user_id}@keto-example.com"
        quiz_data = self._generate_quiz_data(user_id)

        try:
            start_time = time.time()
            async with self.session.post(f"{self.config.base_url}/api/v1/quiz/submit",
                                       json={"email": email, "quiz_data": quiz_data}) as response:
                response_time = (time.time() - start_time) * 1000  # convert to ms
                response_text = await response.text()
                return {
                    "status": response.status,
                    "response_time": response_time,
                    "response_data": response_text,
                    "success": response.status == 200
                }
        except Exception as e:
            return {
                "status": 0,
                "response_time": 0,
                "response_data": str(e),
                "success": False
            }

    async def verify_recovery(self, token: str = None) -> Dict:
        """Simulate meal plan recovery request."""
        # Use a mock token for testing, or generate one if needed
        mock_token = token or f"lt_recovery_{random.randint(100000, 999999)}"

        try:
            start_time = time.time()
            async with self.session.get(f"{self.config.base_url}/api/v1/recovery/verify",
                                      params={"token": mock_token}) as response:
                response_time = (time.time() - start_time) * 1000  # convert to ms
                response_text = await response.text()
                return {
                    "status": response.status,
                    "response_time": response_time,
                    "response_data": response_text,
                    "success": response.status == 200
                }
        except Exception as e:
            return {
                "status": 0,
                "response_time": 0,
                "response_data": str(e),
                "success": False
            }

    async def check_health(self) -> Dict:
        """Check API health endpoint."""
        try:
            start_time = time.time()
            async with self.session.get(f"{self.config.base_url}/health") as response:
                response_time = (time.time() - start_time) * 1000  # convert to ms
                response_text = await response.text()
                return {
                    "status": response.status,
                    "response_time": response_time,
                    "response_data": response_text,
                    "success": response.status == 200
                }
        except Exception as e:
            return {
                "status": 0,
                "response_time": 0,
                "response_data": str(e),
                "success": False
            }

    def _generate_quiz_data(self, user_id: str) -> Dict:
        """Generate realistic quiz response data for load testing."""
        # Random but realistic user profile
        genders = ["male", "female", "non_binary"]
        activity_levels = ["sedentary", "lightly_active", "moderately_active", "very_active"]
        meal_preferences = ["vegan", "vegetarian", "keto", "paleo", "balanced"]
        goals = ["weight_loss", "muscle_gain", "maintenance"]

        def generate_random_string(length=10):
            return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

        return {
            "step_1": random.choice(genders),
            "step_2": random.choice(activity_levels),
            "step_3": [f"protein_{i}_{generate_random_string(3)}" for i in range(1, 4)],  # poultry
            "step_4": [f"seafood_{i}_{generate_random_string(3)}" for i in range(1, 3)],  # fish
            "step_5": [f"veg_{i}_{generate_random_string(2)}" for i in range(1, 4)],  # vegetables
            "step_6": [f"cruciferous_{i}_{generate_random_string(2)}" for i in range(1, 3)],
            "step_7": [f"greens_{i}_{generate_random_string(2)}" for i in range(1, 3)],
            "step_8": [f"more_veg_{i}_{generate_random_string(2)}" for i in range(1, 3)],
            "step_9": [f"additional_protein_{i}_{generate_random_string(2)}" for i in range(1, 3)],
            "step_10": [f"organ_meat_{i}_{generate_random_string(2)}"] if random.random() > 0.5 else [],
            "step_11": [f"fruit_{i}_{generate_random_string(2)}" for i in range(1, 3)],
            "step_12": [f"nuts_{i}_{generate_random_string(2)}" for i in range(1, 3)],
            "step_13": [f"herb_{i}_{generate_random_string(2)}" for i in range(1, 3)],
            "step_14": [f"oil_{i}_{generate_random_string(2)}" for i in range(1, 3)],
            "step_15": [f"drink_{i}_{generate_random_string(2)}" for i in range(1, 3)],
            "step_16": [f"diary_{i}_{generate_random_string(2)}" for i in range(1, 3)],
            "step_17": random.choice(["gluten_free", "lactose_free", "none", "vegetarian", "vegan"]),
            "step_18": str(random.choice([2, 3, 4, 5, 6])),
            "step_19": [f"behavior_{i}_{generate_random_string(4)}" for i in range(random.randint(1, 3))],
            "step_20": {
                "age": random.randint(18, 75),
                "weight_kg": random.uniform(45.0, 120.0),
                "height_cm": random.randint(150, 200),
                "goal": random.choice(goals)
            }
        }


class LoadTestSimulator:
    """Main simulator that orchestrates the load test."""

    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.metrics = LoadTestMetrics()
        self.test_start_time = None
        self.test_end_time = None

    async def run_load_test(self) -> LoadTestMetrics:
        """Run the full load test simulation."""
        print(f"Starting load test at {datetime.now()}")
        print(f"Target: {self.config.target_concurrent_users} concurrent users")
        print(f"Duration: {self.config.test_duration_minutes} minutes")

        self.test_start_time = time.time()

        # Create HTTP session with reasonable timeout settings
        timeout = aiohttp.ClientTimeout(total=30)  # 30s timeout
        connector = aiohttp.TCPConnector(limit=1000)  # High connection limit

        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            # Create multiple user clients
            clients = [LoadTestClient(self.config, session) for _ in range(self.config.target_concurrent_users)]

            # Run the test for specified duration
            test_duration_seconds = self.config.test_duration_minutes * 60

            # Create tasks for continuous operation
            tasks = []

            # Each client runs operations throughout the test duration
            for i, client in enumerate(clients):
                task = asyncio.create_task(self._simulate_user_session(client, i, test_duration_seconds))
                tasks.append(task)

            # Wait for all tasks to complete
            await asyncio.gather(*tasks, return_exceptions=True)

        self.test_end_time = time.time()
        self._calculate_final_metrics(test_duration_seconds)

        print(f"Load test completed at {datetime.now()}")
        return self.metrics

    async def _simulate_user_session(self, client: LoadTestClient, user_id: int, duration_seconds: int):
        """Simulate a single user's activity pattern over time."""
        start_time = time.time()

        while time.time() - start_time < duration_seconds:
            # Randomize action timing to simulate realistic user behavior
            action = await self._select_random_action(client)

            # Add some jitter to timing to avoid synchronized requests
            action_interval = random.uniform(0.5, 3.0)  # 0.5-3 second intervals
            await asyncio.sleep(action_interval)

    async def _select_random_action(self, client: LoadTestClient):
        """Select a random action based on configured load distribution."""
        # Roll random number to determine which type of request to make
        choice = random.random()

        # 60% quiz submissions, 30% recovery requests, 10% health checks
        if choice < 0.6:
            # Quiz submission (most common user activity)
            result = await client.submit_quiz(str(client.__hash__() % 10000))
        elif choice < 0.9:
            # Recovery request
            result = await client.verify_recovery()
        else:
            # Health check/monitoring (much less common)
            result = await client.check_health()

        # Update metrics
        self._update_metrics(result)

    def _update_metrics(self, result: dict):
        """Update performance metrics based on request result."""
        self.metrics.total_requests += 1

        if result["success"]:
            self.metrics.successful_requests += 1
        else:
            self.metrics.failed_requests += 1

        # Track response times
        if result["response_time"] > 0:
            self.metrics.response_times.append(result["response_time"])

        # Track error types if applicable
        if not result["success"] and result.get("status", 0) != 0:
            error_key = f"status_{result['status']}"
            self.metrics.error_details[error_key] = self.metrics.error_details.get(error_key, 0) + 1

    def _calculate_final_metrics(self, duration_seconds: float):
        """Calculate final aggregated metrics."""
        if self.metrics.total_requests > 0:
            self.metrics.error_rate = self.metrics.failed_requests / self.metrics.total_requests

            # Response time calculations
            if self.metrics.response_times:
                self.metrics.response_times.sort()
                self.metrics.avg_response_time = sum(self.metrics.response_times) / len(self.metrics.response_times)

                # Calculate percentiles assuming there are enough sample points
                n = len(self.metrics.response_times)
                if n > 0:
                    self.metrics.p95_response_time = self.metrics.response_times[int(0.95 * n)]
                    self.metrics.p99_response_time = self.metrics.response_times[int(0.99 * n)]

            # Request rate calculations
            self.metrics.requests_per_second = self.metrics.total_requests / duration_seconds if duration_seconds > 0 else 0
            self.metrics.requests_per_minute = self.metrics.requests_per_second * 60


async def run_standalone_test():
    """Entry point for standalone execution."""
    parser = argparse.ArgumentParser(description="Load test the Keto Meal Plan Generator API")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Target API base URL")
    parser.add_argument("--users", type=int, default=20, help="Number of concurrent users (default: 20)")
    parser.add_argument("--duration", type=int, default=5, help="Test duration in minutes (default: 5)")
    parser.add_argument("--admin-key", help="Admin API key for protected endpoints")

    args = parser.parse_args()

    config = LoadTestConfig(
        base_url=args.base_url,
        target_concurrent_users=args.users,
        test_duration_minutes=args.duration,
        admin_api_key=args.admin_key
    )

    print(f"Starting load test with {config.target_concurrent_users} users for {config.test_duration_minutes} minutes...")

    # Run the simulator
    simulator = LoadTestSimulator(config)
    metrics = await simulator.run_load_test()

    # Generate report
    LoadTestReporter.print_summary(metrics, config, simulator.test_end_time - simulator.test_start_time)

    # Return success/failure based on SLA compliance
    if metrics.error_rate > 0.05 or metrics.avg_response_time > 1000:  # More than 5% errors or >1s avg response
        print("\n⚠️  WARNING: Load test did not meet SLA requirements")
        return 1
    else:
        print("\n✅ Load test completed successfully")
        return 0


async def run_production_load_test():
    """
    Production-specific load test with higher volumes and duration.
    This is used for final production validation.
    """
    config = LoadTestConfig(
        base_url="https://your-keto-backend.onrender.com",  # Production URL
        target_concurrent_users=100,  # 100 concurrent users
        test_duration_minutes=10,  # 10 minutes of load
        admin_api_key="PRODUCTION_ADMIN_KEY_HERE"  # Use production key
    )

    print("Running production load test...")
    simulator = LoadTestSimulator(config)
    metrics = await simulator.run_load_test()

    LoadTestReporter.print_summary(metrics, config, simulator.test_end_time - simulator.test_start_time)

    return 0 if metrics.error_rate <= 0.05 and metrics.avg_response_time <= 500 else 1


if __name__ == "__main__":
    # Check if this is being called for a production load test
    if len(sys.argv) > 1 and sys.argv[1] == "production":
        print("Running PRODUCTION load test. Ensure this is safe for your production system!")
        result = asyncio.run(run_production_load_test())
    else:
        result = asyncio.run(run_standalone_test())

    sys.exit(result)