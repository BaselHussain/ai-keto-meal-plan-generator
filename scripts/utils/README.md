# Utility Scripts and Shared Libraries

Common utilities, helpers, and templates used across all maintenance scripts.

## Overview

This directory contains reusable code for:
1. **Database Connections**: Connection pooling, transaction management
2. **Redis Locks**: Distributed locking for preventing concurrent execution
3. **Logging**: Structured logging with correlation IDs
4. **Metrics**: Metrics emission to observability platforms
5. **Error Handling**: Retry logic, circuit breakers, exponential backoff
6. **Script Templates**: Boilerplate for new cleanup/monitoring scripts

## Utilities

### db_utils.py

**Purpose**: Database connection management with Neon DB best practices

**Features**:
- Connection pooling (configurable size)
- Automatic retry on transient failures
- Transaction context managers
- Query timeout enforcement
- Connection health checks

**Usage**:
```python
from scripts.utils.db_utils import get_db_connection, transaction

# Get connection from pool
with get_db_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()

# Transaction context (auto-commit on success, rollback on error)
with transaction() as tx:
    tx.execute("DELETE FROM quiz_responses WHERE id = %s", (quiz_id,))
    tx.execute("INSERT INTO audit_log (...) VALUES (...)")
    # Commits automatically if no exception raised
```

**Configuration**:
```python
# Environment variables
DATABASE_URL=postgresql://...
DB_POOL_SIZE=10              # Max connections in pool
DB_MAX_OVERFLOW=20           # Max overflow connections
DB_POOL_TIMEOUT=30           # Seconds to wait for connection
DB_QUERY_TIMEOUT=60          # Seconds before query timeout
```

**Connection Pooling**:
```python
from sqlalchemy import create_engine, pool

engine = create_engine(
    DATABASE_URL,
    poolclass=pool.QueuePool,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=3600,          # Recycle connections after 1 hour
    pool_pre_ping=True,         # Health check before use
)
```

### redis_lock.py

**Purpose**: Distributed locking via Redis to prevent concurrent script execution

**Features**:
- Atomic lock acquisition with timeout
- Automatic lock renewal for long-running jobs
- Graceful lock release on exit
- Deadlock detection (stale lock cleanup)

**Usage**:
```python
from scripts.utils.redis_lock import acquire_lock, release_lock, RedisLockContext

# Context manager (recommended)
with RedisLockContext("cleanup:quiz_responses", timeout=300) as lock:
    if lock.acquired:
        # Your cleanup logic here
        cleanup_quiz_responses()
    else:
        logger.warning("Failed to acquire lock, another instance running")

# Manual lock management
lock_id = acquire_lock("cleanup:pdfs", timeout=600)
if lock_id:
    try:
        cleanup_pdfs()
    finally:
        release_lock("cleanup:pdfs", lock_id)
```

**Lock Implementation**:
```python
import redis
import uuid

def acquire_lock(lock_name, timeout=300):
    """Acquire distributed lock with timeout."""
    redis_client = redis.from_url(REDIS_URL)
    lock_key = f"lock:{lock_name}"
    lock_value = str(uuid.uuid4())  # Unique lock ID

    # SET with NX (only if not exists) and EX (expiry)
    acquired = redis_client.set(
        lock_key,
        lock_value,
        nx=True,
        ex=timeout
    )

    return lock_value if acquired else None

def release_lock(lock_name, lock_id):
    """Release lock only if we own it."""
    redis_client = redis.from_url(REDIS_URL)
    lock_key = f"lock:{lock_name}"

    # Lua script for atomic check-and-delete
    lua_script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """

    released = redis_client.eval(lua_script, 1, lock_key, lock_id)
    return released == 1
```

**Stale Lock Cleanup**:
```python
def cleanup_stale_locks(max_age_hours=24):
    """Remove locks older than max_age (zombie locks)."""
    redis_client = redis.from_url(REDIS_URL)

    for key in redis_client.scan_iter("lock:*"):
        ttl = redis_client.ttl(key)
        if ttl == -1:  # No expiry set (shouldn't happen, but defensive)
            redis_client.delete(key)
            logger.warning(f"Deleted zombie lock: {key}")
```

### logging_utils.py

**Purpose**: Structured logging with correlation IDs for traceability

**Features**:
- JSON-formatted logs for machine parsing
- Correlation IDs for request tracing
- Context propagation (script name, user, etc.)
- Integration with Sentry for error tracking

**Usage**:
```python
from scripts.utils.logging_utils import get_logger, log_context

logger = get_logger(__name__)

# Basic logging
logger.info("Starting cleanup", extra={"records_to_delete": 1234})

# Context manager (adds context to all logs within scope)
with log_context(correlation_id="cleanup-20260103", script="cleanup_quiz_responses"):
    logger.info("Batch 1 started")
    # ... cleanup logic ...
    logger.info("Batch 1 completed", extra={"records_deleted": 1000})
```

**Log Format**:
```json
{
  "timestamp": "2026-01-03T15:30:00.123Z",
  "level": "INFO",
  "logger": "scripts.cleanup.cleanup_quiz_responses",
  "message": "Batch 1 completed",
  "correlation_id": "cleanup-20260103",
  "script": "cleanup_quiz_responses",
  "records_deleted": 1000,
  "duration_seconds": 1.2
}
```

**Sentry Integration**:
```python
import sentry_sdk

sentry_sdk.init(
    dsn=SENTRY_DSN,
    environment=ENVIRONMENT,
    traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
)

# Errors automatically sent to Sentry
try:
    cleanup_quiz_responses()
except Exception as e:
    logger.error("Cleanup failed", exc_info=True)
    sentry_sdk.capture_exception(e)
```

### metrics_utils.py

**Purpose**: Emit metrics to observability platforms (Prometheus, Datadog, etc.)

**Features**:
- Counter, gauge, histogram metrics
- Custom labels/tags
- Batch metric emission
- Integration with monitoring backends

**Usage**:
```python
from scripts.utils.metrics_utils import emit_metric, emit_counter, emit_gauge, emit_histogram

# Counter (monotonically increasing)
emit_counter("cleanup.records_deleted", 1234, tags={"script": "quiz_responses"})

# Gauge (point-in-time value)
emit_gauge("cleanup.duration_seconds", 45.2, tags={"script": "quiz_responses"})

# Histogram (distribution)
emit_histogram("cleanup.batch_duration", 1.2, tags={"script": "quiz_responses", "batch": "1"})

# Custom metric
emit_metric(
    name="cleanup.sla_utilization",
    value=34.3,
    metric_type="gauge",
    tags={"script": "quiz_responses", "status": "within_sla"}
)
```

**Metric Backend Configuration**:
```python
# Environment variables
METRICS_BACKEND=statsd           # Options: statsd, datadog, prometheus
STATSD_HOST=localhost
STATSD_PORT=8125
```

### retry_utils.py

**Purpose**: Retry logic with exponential backoff for transient failures

**Features**:
- Configurable retry count and backoff
- Exponential backoff with jitter
- Predicate-based retry (only retry on specific errors)
- Circuit breaker pattern

**Usage**:
```python
from scripts.utils.retry_utils import retry, exponential_backoff

# Decorator with default config (3 retries, exponential backoff)
@retry(max_attempts=3, backoff_multiplier=2, base_delay=1)
def call_external_api():
    response = requests.delete(pdf_url)
    response.raise_for_status()
    return response

# Manual retry
for attempt in range(3):
    try:
        call_external_api()
        break
    except requests.exceptions.RequestException as e:
        if attempt < 2:
            delay = exponential_backoff(attempt, base=1, multiplier=2)
            logger.warning(f"Retry {attempt+1}/3 after {delay}s", exc_info=True)
            time.sleep(delay)
        else:
            logger.error("All retries exhausted", exc_info=True)
            raise
```

**Exponential Backoff**:
```python
import random

def exponential_backoff(attempt, base=1, multiplier=2, max_delay=60):
    """Calculate backoff delay with jitter."""
    delay = min(base * (multiplier ** attempt), max_delay)
    jitter = random.uniform(0, delay * 0.1)  # 10% jitter
    return delay + jitter
```

**Circuit Breaker**:
```python
from scripts.utils.retry_utils import CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=5,      # Open circuit after 5 failures
    recovery_timeout=60,      # Try again after 60 seconds
    expected_exception=Exception
)

@breaker
def call_unreliable_service():
    # If service fails 5 times, circuit opens
    # Requests fail-fast for 60 seconds
    # Then circuit half-opens to test recovery
    response = requests.get("https://unreliable-service.com")
    response.raise_for_status()
    return response
```

### script_template.py

**Purpose**: Boilerplate template for new cleanup/monitoring scripts

**Template Structure**:
```python
#!/usr/bin/env python3
"""
Script: cleanup_example.py
Purpose: [Brief description]
Schedule: [Cron expression]
SLA: [Time budget]
"""

import sys
from scripts.utils.db_utils import get_db_connection, transaction
from scripts.utils.redis_lock import RedisLockContext
from scripts.utils.logging_utils import get_logger, log_context
from scripts.utils.metrics_utils import emit_counter, emit_gauge
from scripts.utils.retry_utils import retry

logger = get_logger(__name__)

# Configuration
DRY_RUN = os.getenv("CLEANUP_DRY_RUN", "false").lower() == "true"
BATCH_SIZE = int(os.getenv("CLEANUP_BATCH_SIZE", "1000"))
MAX_DURATION = int(os.getenv("CLEANUP_MAX_DURATION_SECONDS", "3600"))
LOCK_NAME = "cleanup:example"

def main():
    """Main entry point."""
    correlation_id = f"cleanup-example-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    with log_context(correlation_id=correlation_id, script="cleanup_example"):
        logger.info("Starting cleanup script")

        # Acquire distributed lock
        with RedisLockContext(LOCK_NAME, timeout=MAX_DURATION) as lock:
            if not lock.acquired:
                logger.warning("Failed to acquire lock, another instance running")
                return 1

            try:
                records_deleted = run_cleanup()
                logger.info(f"Cleanup completed: {records_deleted} records deleted")
                emit_counter("cleanup.records_deleted", records_deleted)
                return 0

            except Exception as e:
                logger.error("Cleanup failed", exc_info=True)
                emit_counter("cleanup.errors", 1)
                return 1

def run_cleanup():
    """Execute cleanup logic."""
    start_time = time.time()
    total_deleted = 0

    with get_db_connection() as conn:
        # Query records to delete
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id FROM example_table
                WHERE created_at < NOW() - INTERVAL '24 hours'
                LIMIT %s
            """, (BATCH_SIZE,))

            records = cursor.fetchall()

        # Delete in batches
        for batch_num, batch in enumerate(chunk_list(records, BATCH_SIZE), 1):
            if time.time() - start_time > MAX_DURATION:
                logger.warning("Max duration exceeded, aborting")
                break

            batch_deleted = delete_batch(batch, batch_num)
            total_deleted += batch_deleted

            emit_gauge("cleanup.duration_seconds", time.time() - start_time)

    return total_deleted

def delete_batch(batch, batch_num):
    """Delete a batch of records."""
    logger.info(f"Processing batch {batch_num}: {len(batch)} records")

    if DRY_RUN:
        logger.info(f"[DRY-RUN] Would delete {len(batch)} records")
        return len(batch)

    with transaction() as tx:
        # Log to audit table
        for record_id in batch:
            tx.execute("""
                INSERT INTO audit_log (actor, action, resource_type, resource_id, reason)
                VALUES ('system:cleanup_example', 'DELETE', 'example', %s, 'retention_policy_24h')
            """, (record_id,))

        # Delete records
        tx.execute("""
            DELETE FROM example_table
            WHERE id = ANY(%s)
        """, (batch,))

    logger.info(f"Batch {batch_num} completed: {len(batch)} records deleted")
    return len(batch)

if __name__ == "__main__":
    sys.exit(main())
```

**Usage**:
```bash
# Copy template for new script
cp scripts/utils/script_template.py scripts/cleanup/cleanup_new_feature.py

# Customize script (update constants, cleanup logic)
vim scripts/cleanup/cleanup_new_feature.py

# Test with dry-run
CLEANUP_DRY_RUN=true python scripts/cleanup/cleanup_new_feature.py

# Deploy to production
# (Configure in Render cron jobs)
```

## Testing Utilities

### test_helpers.py

**Purpose**: Test fixtures and mocks for unit testing scripts

**Features**:
- Mock database connections
- Mock Redis locks
- Mock external APIs (Vercel Blob)
- Test data factories

**Usage**:
```python
from scripts.utils.test_helpers import (
    mock_db_connection,
    mock_redis_lock,
    create_quiz_response,
    create_meal_plan
)

def test_cleanup_deletes_old_records(mock_db_connection):
    """Test that cleanup deletes records older than 24h."""
    # Create test data
    old_quiz = create_quiz_response(created_at=datetime.now() - timedelta(hours=25))
    new_quiz = create_quiz_response(created_at=datetime.now() - timedelta(hours=1))

    # Run cleanup
    with mock_redis_lock("cleanup:quiz_responses"):
        records_deleted = run_cleanup()

    # Verify
    assert records_deleted == 1
    assert quiz_exists(old_quiz.id) is False
    assert quiz_exists(new_quiz.id) is True
```

## Best Practices

When using utilities:

1. **Always use connection pooling**: Never create raw connections
2. **Always acquire Redis locks**: Prevents concurrent execution
3. **Always use structured logging**: Machine-parsable logs
4. **Always emit metrics**: Observability is critical
5. **Always handle errors gracefully**: Log, retry, then escalate
6. **Always test with dry-run**: Validate logic before production
7. **Always use transactions**: Atomic operations or rollback

## Configuration

Shared environment variables (all scripts):

```bash
# Database
DATABASE_URL=postgresql://...
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_QUERY_TIMEOUT=60

# Redis
REDIS_URL=redis://...
REDIS_CONNECT_TIMEOUT=5
REDIS_LOCK_TIMEOUT=300

# Logging
LOG_LEVEL=INFO                    # DEBUG, INFO, WARN, ERROR
LOG_FORMAT=json                   # json, text

# Metrics
METRICS_BACKEND=statsd
STATSD_HOST=localhost
STATSD_PORT=8125

# Sentry
SENTRY_DSN=...
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1

# Script Execution
CLEANUP_DRY_RUN=false
CLEANUP_BATCH_SIZE=1000
CLEANUP_MAX_DURATION_SECONDS=3600
```

## Troubleshooting

### Issue: Connection Pool Exhausted

**Symptoms**: `TimeoutError: QueuePool limit exceeded`

**Diagnosis**:
```python
from sqlalchemy import inspect

# Check active connections
engine = get_db_engine()
pool = engine.pool
print(f"Pool size: {pool.size()}")
print(f"Checked out: {pool.checkedout()}")
print(f"Overflow: {pool.overflow()}")
```

**Resolution**:
- Increase `DB_POOL_SIZE` and `DB_MAX_OVERFLOW`
- Ensure connections are properly closed (use context managers)
- Reduce concurrent script executions

### Issue: Redis Lock Stuck

**Symptoms**: Lock acquisition always fails

**Diagnosis**:
```bash
# Check lock in Redis
redis-cli GET "lock:cleanup:quiz_responses"

# Check TTL
redis-cli TTL "lock:cleanup:quiz_responses"
```

**Resolution**:
```bash
# If lock is stale (process died without releasing)
redis-cli DEL "lock:cleanup:quiz_responses"
```

## References

- Database connection pooling: https://docs.sqlalchemy.org/en/14/core/pooling.html
- Redis distributed locking: https://redis.io/docs/manual/patterns/distributed-locks/
- Structured logging: https://www.structlog.org/
- Sentry error tracking: https://docs.sentry.io/platforms/python/
