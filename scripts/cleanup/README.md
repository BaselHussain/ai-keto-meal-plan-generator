# Cleanup Scripts

Automated data cleanup jobs for enforcing retention policies and maintaining database health.

## Overview

This directory contains cron job scripts that delete expired data according to documented retention policies:

1. **Quiz Responses**: Delete after 24 hours (or after meal plan purchased)
2. **PDFs**: Delete after 90 days from Vercel Blob storage
3. **Magic Link Tokens**: Delete expired tokens (24-hour TTL)
4. **Email Blacklist**: Remove entries after 90 days

All scripts implement:
- Idempotent operations (safe to retry)
- Batch processing to avoid overwhelming the database
- Distributed locking via Redis to prevent concurrent execution
- Comprehensive audit logging for compliance
- Dry-run mode for safe testing
- SLA monitoring and alerting

## Scripts

### cleanup_quiz_responses.py

**Purpose**: Delete quiz responses older than 24 hours (or after meal plan purchase)

**Retention Policy**:
- Quiz responses are deleted 24 hours after creation
- If user purchases meal plan, quiz data is deleted immediately after PDF generation
- Audit logs are retained indefinitely for compliance

**Schedule**: Daily at 2:00 AM UTC

**Cron Expression**: `0 2 * * *`

**Execution Strategy**:
1. Acquire distributed lock via Redis (`lock:cleanup:quiz_responses`)
2. Query for quiz responses where `created_at < NOW() - INTERVAL '24 hours'`
3. For each batch (default 1000 records):
   - Log deletion intent to audit table
   - Delete quiz response in transaction
   - Emit metrics (records deleted, duration)
4. Release lock
5. Report SLA compliance

**SLA**: Complete within 60 minutes, process 100K records/hour

**Estimated Runtime**: 5-15 minutes (varies with data volume)

**Database Impact**:
- Writes: DELETE on `quiz_responses` table
- Reads: SELECT with timestamp index
- Locks: Row-level locks during batch deletion
- Index usage: `idx_quiz_responses_created_at`

### cleanup_pdfs.py

**Purpose**: Delete PDF files from Vercel Blob storage after 90 days

**Retention Policy**:
- PDFs are stored for 90 days after generation
- After 90 days, PDF is deleted from Vercel Blob
- Database record (`meal_plans.pdf_url`) is set to NULL
- Metadata (meal plan data, user association) retained indefinitely

**Schedule**: Daily at 3:00 AM UTC

**Cron Expression**: `0 3 * * *`

**Execution Strategy**:
1. Acquire distributed lock via Redis (`lock:cleanup:pdfs`)
2. Query for meal plans where `pdf_generated_at < NOW() - INTERVAL '90 days'` AND `pdf_url IS NOT NULL`
3. For each batch (default 100 PDFs to avoid Vercel API rate limits):
   - Extract Blob URL from `pdf_url`
   - Delete from Vercel Blob via API
   - Update database: SET `pdf_url = NULL, pdf_deleted_at = NOW()`
   - Log deletion to audit table
4. Release lock
5. Report SLA compliance

**SLA**: Complete within 120 minutes, process 10K PDFs/hour

**Estimated Runtime**: 10-30 minutes (depends on Vercel API latency)

**External Dependencies**:
- Vercel Blob API (rate limit: 1000 requests/hour)
- Network latency to Vercel CDN

**Error Handling**:
- If Blob deletion fails (404 already deleted), still update database
- If Blob API is unreachable, retry with exponential backoff (max 3 attempts)
- If persistent failure, add to manual resolution queue

### cleanup_magic_links.py

**Purpose**: Delete expired magic link tokens (24-hour TTL)

**Retention Policy**:
- Magic link tokens expire 24 hours after creation
- Expired tokens are soft-deleted (marked as `is_deleted = TRUE`)
- Hard deletion occurs after 30 days of soft-delete (for audit trail)

**Schedule**: Hourly (on the hour)

**Cron Expression**: `0 * * * *`

**Execution Strategy**:
1. Acquire distributed lock via Redis (`lock:cleanup:magic_links`)
2. Soft-delete: UPDATE magic_links SET `is_deleted = TRUE` WHERE `expires_at < NOW()` AND `is_deleted = FALSE`
3. Hard-delete: DELETE FROM magic_links WHERE `is_deleted = TRUE` AND `deleted_at < NOW() - INTERVAL '30 days'`
4. Log deletions to audit table
5. Release lock
6. Report SLA compliance

**SLA**: Complete within 5 minutes, process 50K tokens/hour

**Estimated Runtime**: 1-3 minutes

**Database Impact**:
- Low impact (small table, indexed queries)
- Soft-delete allows for audit trail and potential recovery

### cleanup_blacklist.py

**Purpose**: Remove email blacklist entries after 90 days

**Retention Policy**:
- Blacklist entries (failed payments, abuse) are retained for 90 days
- After 90 days, users can retry without blacklist restriction
- Permanent bans require manual flag (`is_permanent = TRUE`)

**Schedule**: Daily at 4:00 AM UTC

**Cron Expression**: `0 4 * * *`

**Execution Strategy**:
1. Acquire distributed lock via Redis (`lock:cleanup:blacklist`)
2. DELETE FROM email_blacklist WHERE `created_at < NOW() - INTERVAL '90 days'` AND `is_permanent = FALSE`
3. Log deletions to audit table
4. Emit metrics
5. Release lock
6. Report SLA compliance

**SLA**: Complete within 10 minutes, process 10K entries/hour

**Estimated Runtime**: 2-5 minutes

**Compliance Note**: Blacklist cleanup supports GDPR right to be forgotten (automatic expiry reduces indefinite blocking)

## Configuration

All scripts use environment variables (never hardcode):

```bash
# Cleanup Configuration
CLEANUP_BATCH_SIZE=1000                   # Records per batch
CLEANUP_DRY_RUN=false                     # Dry-run mode (logs actions but doesn't delete)
CLEANUP_MAX_DURATION_SECONDS=3600         # Kill switch: abort if exceeds this duration
CLEANUP_LOCK_TIMEOUT_SECONDS=300          # Redis lock timeout

# Database
DATABASE_URL=postgresql://...             # Neon DB connection
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Redis (Distributed Locks)
REDIS_URL=redis://...
REDIS_CONNECT_TIMEOUT=5

# Vercel Blob (PDFs only)
BLOB_READ_WRITE_TOKEN=...

# Monitoring
SENTRY_DSN=...
LOG_LEVEL=INFO
```

## Dry-Run Mode

Always test with dry-run before production deployment:

```bash
CLEANUP_DRY_RUN=true python cleanup_quiz_responses.py
```

Dry-run output:
```
[DRY-RUN] Would delete 1,234 quiz responses older than 24 hours
[DRY-RUN] Batch 1: 1000 records (IDs: 12345-13345)
[DRY-RUN] Batch 2: 234 records (IDs: 13346-13580)
[DRY-RUN] Total execution time: 2.3 seconds
[DRY-RUN] SLA status: WITHIN_SLA (target: 3600s, actual: 2.3s)
```

## Monitoring and Alerting

All scripts emit structured logs:

```json
{
  "timestamp": "2026-01-03T02:15:30Z",
  "level": "INFO",
  "correlation_id": "cleanup-20260103-021530",
  "script": "cleanup_quiz_responses",
  "event": "batch_completed",
  "batch_number": 1,
  "records_deleted": 1000,
  "batch_duration_seconds": 1.2,
  "cumulative_duration_seconds": 1.2,
  "sla_remaining_seconds": 3598.8
}
```

SLA breach alerts:

```json
{
  "level": "WARN",
  "event": "sla_warning",
  "sla_threshold_percent": 80,
  "current_percent": 82,
  "message": "Cleanup job approaching SLA limit"
}
```

## Error Handling

All scripts implement:

1. **Transactional Safety**: Each batch operates in a transaction (rollback on error)
2. **Exponential Backoff**: Transient failures retry with delay (1s, 2s, 4s, 8s, max 3 retries)
3. **Circuit Breaker**: After 5 consecutive failures, abort and alert
4. **Partial Success**: If batch 1 succeeds but batch 2 fails, batch 1 deletions are committed
5. **Manual Resolution Queue**: Persistent failures added to queue for operator review

Error log example:

```json
{
  "level": "ERROR",
  "event": "batch_failed",
  "batch_number": 3,
  "error": "deadlock detected",
  "retry_attempt": 1,
  "will_retry": true,
  "backoff_seconds": 2
}
```

## Safety Checklist

Before deploying a new cleanup script:

- [ ] Dry-run tested with production-like data volume
- [ ] Batch size tuned to avoid timeouts (start small: 100, then 1000)
- [ ] Foreign key relationships verified (no orphaned records)
- [ ] Audit logging captures all required fields (actor, resource, timestamp, reason)
- [ ] SLA thresholds defined and monitoring configured
- [ ] Error handling covers all identified failure modes (deadlock, timeout, network)
- [ ] Distributed lock prevents concurrent execution
- [ ] Runbook created for manual intervention scenarios
- [ ] Progressive rollout plan (10%, 50%, 100%)

## Runbook: Manual Intervention

### Issue: Cleanup Job Stuck

**Symptoms**: Job exceeds max duration, Redis lock not released

**Diagnosis**:
```bash
# Check if lock exists
redis-cli GET "lock:cleanup:quiz_responses"

# Check running processes
ps aux | grep cleanup_quiz_responses
```

**Resolution**:
```bash
# Kill process gracefully
kill -TERM <pid>

# Release lock manually (only if process is confirmed dead)
redis-cli DEL "lock:cleanup:quiz_responses"
```

### Issue: SLA Breach

**Symptoms**: Job exceeds 80% of time budget

**Diagnosis**:
```sql
-- Check table size
SELECT COUNT(*) FROM quiz_responses WHERE created_at < NOW() - INTERVAL '24 hours';

-- Check slow queries
SELECT * FROM pg_stat_statements WHERE query LIKE '%quiz_responses%' ORDER BY mean_exec_time DESC LIMIT 10;
```

**Resolution**:
- Reduce `CLEANUP_BATCH_SIZE` (e.g., 1000 → 500)
- Add/optimize indexes on timestamp columns
- Scale database resources (Neon autoscaling)
- Split cleanup into multiple smaller jobs

### Issue: Foreign Key Violations

**Symptoms**: Deletion fails with FK constraint error

**Diagnosis**:
```sql
-- Find dependent records
SELECT * FROM meal_plans WHERE quiz_response_id IN (
  SELECT id FROM quiz_responses WHERE created_at < NOW() - INTERVAL '24 hours'
);
```

**Resolution**:
- Implement cascading delete in cleanup logic
- OR: Soft-delete quiz responses instead of hard-delete
- OR: Add to manual resolution queue for operator review

## Performance Tuning

### Indexes Required

All cleanup scripts depend on these indexes:

```sql
-- Quiz responses cleanup
CREATE INDEX CONCURRENTLY idx_quiz_responses_created_at
  ON quiz_responses(created_at)
  WHERE created_at < NOW() - INTERVAL '24 hours';

-- PDF cleanup
CREATE INDEX CONCURRENTLY idx_meal_plans_pdf_generated_at
  ON meal_plans(pdf_generated_at)
  WHERE pdf_url IS NOT NULL;

-- Magic link cleanup
CREATE INDEX CONCURRENTLY idx_magic_links_expires_at
  ON magic_links(expires_at)
  WHERE is_deleted = FALSE;

CREATE INDEX CONCURRENTLY idx_magic_links_deleted_at
  ON magic_links(deleted_at)
  WHERE is_deleted = TRUE;

-- Blacklist cleanup
CREATE INDEX CONCURRENTLY idx_email_blacklist_created_at
  ON email_blacklist(created_at)
  WHERE is_permanent = FALSE;
```

### Batch Size Guidelines

- **Small tables** (<10K records): Batch size 1000-5000
- **Medium tables** (10K-100K): Batch size 500-1000
- **Large tables** (>100K): Batch size 100-500
- **External API calls** (Vercel Blob): Batch size 50-100 (respect rate limits)

## Compliance and Audit

All deletions are logged to the `audit_log` table:

```sql
INSERT INTO audit_log (
  actor,              -- 'system:cleanup_quiz_responses'
  action,             -- 'DELETE'
  resource_type,      -- 'quiz_response'
  resource_id,        -- ID of deleted record
  timestamp,          -- NOW()
  reason,             -- 'retention_policy_24h'
  metadata            -- JSONB with additional context
) VALUES (...);
```

Audit logs are:
- Immutable (no UPDATE/DELETE permissions for cleanup jobs)
- Retained indefinitely (separate from operational data)
- Queryable for compliance reports
- Exportable for external audits

## Testing

Unit tests for each script (in `tests/scripts/cleanup/`):

```python
# tests/scripts/cleanup/test_cleanup_quiz_responses.py

def test_cleanup_respects_24h_retention():
    """Quiz responses older than 24h are deleted."""

def test_cleanup_preserves_recent_responses():
    """Quiz responses newer than 24h are NOT deleted."""

def test_cleanup_is_idempotent():
    """Running cleanup twice has same effect as once."""

def test_dry_run_mode_does_not_delete():
    """Dry-run logs actions but doesn't modify data."""

def test_audit_log_captures_deletions():
    """Every deletion is recorded in audit_log."""
```

Run tests:
```bash
cd /mnt/f/saas\ projects/ai-based-meal-plan/backend
pytest tests/scripts/cleanup/ -v
```

## Future Enhancements

Planned improvements:
- [ ] Parallel batch processing (multi-threaded cleanup for large datasets)
- [ ] Adaptive batch sizing (auto-tune based on query performance)
- [ ] Predictive SLA monitoring (forecast breaches before they occur)
- [ ] Self-healing (auto-retry with reduced batch size on timeout)
- [ ] Dashboard for cleanup job metrics (Grafana/Datadog)

## References

- Retention policies: `/mnt/f/saas projects/ai-based-meal-plan/specs/001-keto-meal-plan-generator/plan.md`
- Database schema: `/mnt/f/saas projects/ai-based-meal-plan/backend/models/`
- Audit logging: `/mnt/f/saas projects/ai-based-meal-plan/backend/services/audit.py`
