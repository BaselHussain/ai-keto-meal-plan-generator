# Scripts Directory

This directory contains all automated maintenance scripts for data lifecycle management, compliance, and operational reliability.

## Directory Structure

```
scripts/
├── cleanup/              # Automated data cleanup jobs
├── sla-monitoring/       # SLA breach detection and alerting
├── manual-resolution/    # Manual intervention queue processing
├── retention/            # Data retention policy enforcement
└── utils/                # Shared utilities and helpers
```

## Overview

The scripts in this directory implement critical operational workflows:

1. **Data Cleanup**: Automated deletion of expired data (quiz responses, PDFs, tokens, blacklist entries)
2. **SLA Monitoring**: Real-time monitoring and alerting for cleanup job performance
3. **Manual Resolution**: Queue management for operations requiring human intervention
4. **Retention Enforcement**: Policy-driven data lifecycle management with compliance tracking
5. **Utilities**: Shared libraries for database connections, logging, metrics, and error handling

## Design Principles

All scripts in this directory follow these core principles:

- **Idempotency**: Safe to retry without side effects
- **Observability**: Structured logging with correlation IDs, metrics emission, distributed tracing
- **Safety**: Dry-run modes, transaction management, progressive rollout
- **Compliance**: Comprehensive audit trails for all data operations
- **Resilience**: Error handling with exponential backoff, circuit breakers, graceful degradation

## Technology Stack

- **Language**: Python 3.11+
- **Database**: Neon DB (PostgreSQL with serverless features)
- **Caching/Locks**: Redis (distributed locks, rate limiting)
- **Storage**: Vercel Blob (PDF lifecycle management)
- **Orchestration**: Render Cron (scheduled job execution)
- **Observability**: Sentry (errors), Structured logging (JSON)

## Environment Variables

All scripts require these environment variables (never hardcode):

```bash
# Database
DATABASE_URL=postgresql://...             # Neon DB connection string
DB_POOL_SIZE=10                           # Connection pool size
DB_MAX_OVERFLOW=20                        # Max overflow connections

# Redis
REDIS_URL=redis://...                     # Redis connection string
REDIS_LOCK_TIMEOUT=300                    # Lock timeout in seconds

# Vercel Blob
BLOB_READ_WRITE_TOKEN=...                 # Vercel Blob API token

# Monitoring
SENTRY_DSN=...                            # Sentry error tracking
LOG_LEVEL=INFO                            # Logging level (DEBUG, INFO, WARN, ERROR)

# Cleanup Configuration
CLEANUP_BATCH_SIZE=1000                   # Records per batch
CLEANUP_DRY_RUN=false                     # Enable dry-run mode
CLEANUP_MAX_DURATION_SECONDS=3600         # Max execution time

# SLA Thresholds
SLA_WARNING_THRESHOLD_PERCENT=80          # Warning at 80% of SLA
SLA_CRITICAL_THRESHOLD_PERCENT=100        # Critical at 100% of SLA
```

## Running Scripts

### Local Development

```bash
# Install dependencies
cd /mnt/f/saas\ projects/ai-based-meal-plan/backend
pip install -r requirements.txt

# Run with dry-run mode (safe testing)
CLEANUP_DRY_RUN=true python ../scripts/cleanup/cleanup_quiz_responses.py

# Run for real (after testing)
python ../scripts/cleanup/cleanup_quiz_responses.py
```

### Production (Render Cron)

Scripts are configured as Render cron jobs with appropriate schedules:

```yaml
# Example: Daily quiz response cleanup at 2 AM UTC
- type: cron
  name: cleanup-quiz-responses
  env: production
  schedule: "0 2 * * *"
  command: python scripts/cleanup/cleanup_quiz_responses.py
  timeout: 3600
```

## Monitoring and Alerting

All scripts emit structured logs and metrics:

```json
{
  "timestamp": "2026-01-03T15:30:00Z",
  "level": "INFO",
  "correlation_id": "abc123",
  "script": "cleanup_quiz_responses",
  "event": "cleanup_completed",
  "records_deleted": 1234,
  "duration_seconds": 45.2,
  "sla_status": "within_sla"
}
```

SLA breaches trigger alerts via Sentry and can be monitored in dashboards.

## Safety and Compliance

### Before Running Any Script

1. **Test with LIMIT**: Start with small batches (LIMIT 10, then 100, then 1000)
2. **Enable Dry-Run**: Always test with `CLEANUP_DRY_RUN=true` first
3. **Check Dependencies**: Verify foreign key relationships won't break
4. **Review Audit Logs**: Ensure audit trail is working before deletion
5. **Monitor Performance**: Watch for lock contention and query duration

### Compliance Requirements

- **Audit Trail**: Every deletion logged with actor, resource, timestamp, reason
- **Retention Policies**: Documented in specs/001-keto-meal-plan-generator/plan.md
- **GDPR/CCPA**: Right to deletion honored within 30 days
- **Data Minimization**: Automated cleanup ensures we don't over-retain data

## Troubleshooting

### Common Issues

**Issue**: Script times out
- **Solution**: Reduce `CLEANUP_BATCH_SIZE`, increase `CLEANUP_MAX_DURATION_SECONDS`

**Issue**: Lock acquisition fails
- **Solution**: Check Redis connectivity, verify no zombie locks, reduce `REDIS_LOCK_TIMEOUT`

**Issue**: Foreign key violations during deletion
- **Solution**: Review deletion order, implement cascading deletes, use soft-delete for referenced data

**Issue**: SLA breach alerts firing
- **Solution**: Analyze query performance, add indexes, scale database resources, adjust batch size

### Emergency Procedures

**Stop a Running Cleanup Job**:
```bash
# Find the process
ps aux | grep cleanup_

# Kill gracefully
kill -TERM <pid>

# If stuck, force kill (may leave incomplete transactions)
kill -KILL <pid>
```

**Release a Stuck Redis Lock**:
```bash
redis-cli DEL "lock:cleanup:quiz_responses"
```

## Development Guidelines

When adding new scripts:

1. Copy template from `utils/script_template.py`
2. Implement idempotent cleanup logic with transactions
3. Add comprehensive error handling with exponential backoff
4. Emit structured logs at key checkpoints
5. Include dry-run mode support
6. Write unit tests for core logic
7. Document retention policy rationale in ADR
8. Create runbook for operators
9. Configure SLA monitoring thresholds
10. Test with progressive rollout (10, 100, 1000, full)

## Contact

For questions about data retention policies, contact the compliance team.
For operational issues, check runbooks in each subdirectory or escalate to on-call.

## References

- Main spec: `/mnt/f/saas projects/ai-based-meal-plan/specs/001-keto-meal-plan-generator/spec.md`
- Architecture plan: `/mnt/f/saas projects/ai-based-meal-plan/specs/001-keto-meal-plan-generator/plan.md`
- Project constitution: `/mnt/f/saas projects/ai-based-meal-plan/.specify/memory/constitution.md`
