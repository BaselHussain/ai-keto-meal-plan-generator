# SLA Monitoring Scripts

Real-time monitoring and alerting for cleanup job performance, SLA breach detection, and operational health.

## Overview

This directory contains scripts that monitor cleanup job execution, detect SLA breaches, and trigger alerts for operational issues:

1. **Cleanup Job SLA Monitoring**: Track execution time, success rate, throughput
2. **Breach Detection**: Alert when jobs exceed time budgets (80% warning, 100% critical)
3. **Manual Resolution Queue Monitoring**: Alert on queue depth, age, escalation
4. **Health Checks**: Validate cleanup job configuration and dependencies

All monitoring scripts emit metrics to observability platforms and trigger alerts via Sentry/PagerDuty.

## Scripts

### monitor_cleanup_sla.py

**Purpose**: Monitor cleanup job execution and detect SLA breaches

**Monitors**:
- Cleanup job execution time vs. SLA budget
- Success rate (successful completions / total attempts)
- Throughput (records processed per hour)
- Error rate and failure patterns
- Lock acquisition failures (indicating concurrent execution attempts)

**Alert Thresholds**:
- **Warning**: Job duration exceeds 80% of SLA budget
- **Critical**: Job duration exceeds 100% of SLA budget
- **Critical**: Success rate < 95% over 24-hour window
- **Warning**: Throughput drops below 50% of baseline
- **Critical**: 3 consecutive failures

**SLA Budgets** (from specs):
```python
SLA_BUDGETS = {
    "cleanup_quiz_responses": 3600,    # 60 minutes
    "cleanup_pdfs": 7200,              # 120 minutes
    "cleanup_magic_links": 300,        # 5 minutes
    "cleanup_blacklist": 600,          # 10 minutes
}
```

**Execution Strategy**:
1. Query audit logs for recent cleanup job executions
2. Calculate metrics:
   - `duration_seconds` from start to completion
   - `sla_utilization_percent = (duration / budget) * 100`
   - `success_rate = successes / (successes + failures)`
   - `throughput_per_hour = records_processed / (duration / 3600)`
3. Compare against thresholds
4. If breach detected:
   - Emit alert to Sentry with severity (warning/critical)
   - Log detailed diagnostics (batch sizes, query times, lock contention)
   - Trigger PagerDuty escalation for critical breaches
5. Store metrics for historical analysis

**Schedule**: Every 15 minutes

**Cron Expression**: `*/15 * * * *`

**Metrics Emitted**:
```json
{
  "metric": "cleanup_sla_utilization",
  "job": "cleanup_quiz_responses",
  "duration_seconds": 1234,
  "sla_budget_seconds": 3600,
  "utilization_percent": 34.3,
  "status": "within_sla",
  "timestamp": "2026-01-03T15:30:00Z"
}
```

**Alert Payload**:
```json
{
  "alert_type": "sla_breach_warning",
  "job": "cleanup_quiz_responses",
  "sla_budget_seconds": 3600,
  "actual_duration_seconds": 2950,
  "utilization_percent": 81.9,
  "threshold_percent": 80,
  "message": "Cleanup job approaching SLA limit (81.9% utilization)",
  "recommended_action": "Review batch size, check database load, verify indexes",
  "runbook": "https://github.com/yourorg/yourrepo/blob/main/scripts/sla-monitoring/runbooks/sla-breach.md"
}
```

### monitor_manual_resolution_queue.py

**Purpose**: Monitor manual resolution queue for depth, age, and escalation triggers

**Monitors**:
- Queue depth (total pending items)
- Average age of items in queue
- Items exceeding SLA for manual resolution (24 hours)
- Resolution rate (items resolved per day)
- Escalation triggers (items stuck >7 days)

**Alert Thresholds**:
- **Warning**: Queue depth > 100 items
- **Critical**: Queue depth > 500 items
- **Warning**: Average item age > 48 hours
- **Critical**: Any item age > 7 days (escalation required)
- **Warning**: Resolution rate drops below 50% of average

**Execution Strategy**:
1. Query manual resolution queue table
2. Calculate metrics:
   - Total pending items
   - Average age: `AVG(NOW() - created_at)`
   - Oldest item age: `MAX(NOW() - created_at)`
   - Items exceeding 24h SLA
   - Items requiring escalation (>7 days)
3. Compare against thresholds
4. If breach detected:
   - Alert operators with queue summary
   - Highlight oldest/highest priority items
   - Provide links to resolution UI
5. Emit metrics for dashboards

**Schedule**: Hourly

**Cron Expression**: `0 * * * *`

**Metrics Emitted**:
```json
{
  "metric": "manual_resolution_queue_depth",
  "total_pending": 42,
  "average_age_hours": 18.3,
  "oldest_item_hours": 72,
  "items_exceeding_24h_sla": 3,
  "items_requiring_escalation": 1,
  "timestamp": "2026-01-03T15:00:00Z"
}
```

### check_cleanup_health.py

**Purpose**: Validate cleanup job configuration, dependencies, and operational readiness

**Health Checks**:
1. **Database Connectivity**: Can connect to Neon DB
2. **Redis Connectivity**: Can acquire/release locks
3. **Vercel Blob API**: Can authenticate and list blobs
4. **Required Indexes**: All cleanup indexes exist and are valid
5. **Cron Job Configuration**: Jobs scheduled correctly in Render
6. **Environment Variables**: All required vars are set
7. **Audit Log Table**: Accessible and has correct schema
8. **Lock Timeout**: No zombie locks exist (older than max timeout)

**Execution Strategy**:
1. For each dependency:
   - Attempt connection/operation
   - Measure latency
   - Check for errors
2. For each index:
   - Verify existence: `SELECT * FROM pg_indexes WHERE indexname = '...'`
   - Check validity: `SELECT pg_relation_size(...)`
3. For each environment variable:
   - Check if set (not empty)
   - Validate format (URLs, tokens)
4. Report results:
   - `PASS`: All checks successful
   - `WARN`: Non-critical issues (slow latency, missing optional config)
   - `FAIL`: Critical issues (missing index, DB unreachable)

**Schedule**: Every 6 hours

**Cron Expression**: `0 */6 * * *`

**Health Check Report**:
```json
{
  "status": "WARN",
  "checks": [
    {"name": "database_connectivity", "status": "PASS", "latency_ms": 12},
    {"name": "redis_connectivity", "status": "PASS", "latency_ms": 8},
    {"name": "vercel_blob_api", "status": "PASS", "latency_ms": 145},
    {"name": "index_quiz_responses_created_at", "status": "PASS"},
    {"name": "index_meal_plans_pdf_generated_at", "status": "FAIL", "error": "Index not found"},
    {"name": "env_var_database_url", "status": "PASS"},
    {"name": "env_var_redis_url", "status": "PASS"},
    {"name": "zombie_locks", "status": "WARN", "locks_found": 1, "lock_age_hours": 2.5}
  ],
  "timestamp": "2026-01-03T12:00:00Z"
}
```

## Configuration

Environment variables for monitoring scripts:

```bash
# SLA Thresholds
SLA_WARNING_THRESHOLD_PERCENT=80          # Warning at 80% of SLA
SLA_CRITICAL_THRESHOLD_PERCENT=100        # Critical at 100% of SLA
SLA_SUCCESS_RATE_THRESHOLD=0.95           # Alert if success rate < 95%

# Manual Resolution Queue Thresholds
MRQ_DEPTH_WARNING=100                     # Warn if queue > 100 items
MRQ_DEPTH_CRITICAL=500                    # Critical if queue > 500 items
MRQ_AGE_WARNING_HOURS=48                  # Warn if avg age > 48 hours
MRQ_AGE_ESCALATION_HOURS=168              # Escalate if any item > 7 days

# Alerting
SENTRY_DSN=...                            # Sentry for error tracking
PAGERDUTY_API_KEY=...                     # PagerDuty for critical alerts (optional)
PAGERDUTY_SERVICE_ID=...

# Monitoring Interval
MONITORING_INTERVAL_MINUTES=15            # How often to run SLA checks
```

## Alert Routing

Alerts are routed based on severity:

| Severity | Channel | Response Time | Escalation |
|----------|---------|---------------|------------|
| **INFO** | Logs only | N/A | None |
| **WARNING** | Sentry + Slack | 4 hours | Email to team lead after 24h |
| **CRITICAL** | Sentry + PagerDuty | 15 minutes | Page on-call after 30m |

## Metrics and Dashboards

All monitoring scripts emit metrics to observability platforms:

### Metrics Emitted

1. **cleanup_sla_utilization** (gauge, 0-100%): SLA budget utilization
2. **cleanup_success_rate** (gauge, 0-1): Success rate over time window
3. **cleanup_throughput** (gauge, records/hour): Processing throughput
4. **cleanup_duration** (histogram, seconds): Job execution time distribution
5. **manual_resolution_queue_depth** (gauge, count): Pending items in queue
6. **manual_resolution_queue_age** (histogram, hours): Age distribution of queue items

### Recommended Dashboards

**Cleanup Job Performance**:
- SLA utilization over time (line chart)
- Success rate by job (line chart)
- Throughput by job (line chart)
- Duration distribution (histogram: p50, p95, p99)

**Manual Resolution Queue**:
- Queue depth over time (line chart)
- Age distribution (histogram)
- Resolution rate (line chart)
- Items by priority (pie chart)

**Health Checks**:
- Dependency status (table: PASS/WARN/FAIL)
- Latency by dependency (bar chart)
- Alert history (timeline)

## Runbook: SLA Breach Response

### Warning Alert (80% Utilization)

**Immediate Actions**:
1. Review current job execution (check logs for slow batches)
2. Check database load (query pg_stat_activity for locks/waits)
3. Verify batch size is appropriate (reduce if too large)
4. Check for infrastructure issues (Neon DB autoscaling, network latency)

**Preventative Actions**:
1. Optimize queries (add indexes, rewrite inefficient SQL)
2. Scale database resources (increase Neon compute units)
3. Reduce batch size to spread load
4. Split large jobs into smaller, more frequent jobs

**Escalation**:
- If utilization stays >80% for 3 consecutive runs, escalate to engineering lead

### Critical Alert (100% Utilization or Failure)

**Immediate Actions**:
1. **DO NOT** kill running job (may leave incomplete transactions)
2. Check for deadlocks: `SELECT * FROM pg_locks WHERE NOT granted;`
3. Review error logs for root cause
4. If job is stuck (no progress for 10+ minutes):
   - Kill process gracefully: `kill -TERM <pid>`
   - Release Redis lock: `redis-cli DEL "lock:cleanup:..."`

**Recovery Actions**:
1. Identify root cause (timeout, deadlock, resource exhaustion)
2. Fix immediate issue (free locks, restart failed job)
3. Implement fix (optimize query, increase timeout, reduce batch size)
4. Test with dry-run before re-enabling

**Escalation**:
- Page on-call immediately
- Open incident channel in Slack
- Document root cause and resolution in incident report

### Manual Resolution Queue Overflow

**Immediate Actions**:
1. Review queue for patterns (common failure modes)
2. Batch resolve items if possible (e.g., all PDFs from same day)
3. Assign high-priority items to operators
4. Add temporary capacity if needed

**Preventative Actions**:
1. Identify root cause of queue overflow (failing cleanup jobs, edge cases)
2. Fix upstream issues to prevent items entering queue
3. Automate resolution for common cases
4. Increase operator capacity for queue processing

## Testing

Health check validation:

```bash
# Run health check manually
python check_cleanup_health.py

# Expected output (all PASS)
✓ Database connectivity: PASS (12ms)
✓ Redis connectivity: PASS (8ms)
✓ Vercel Blob API: PASS (145ms)
✓ Index: idx_quiz_responses_created_at: PASS
✓ Index: idx_meal_plans_pdf_generated_at: PASS
...
Overall status: PASS
```

Simulate SLA breach:

```bash
# Insert test execution that exceeds SLA
psql $DATABASE_URL << EOF
INSERT INTO audit_log (
  actor, action, resource_type, timestamp, metadata
) VALUES (
  'system:test',
  'CLEANUP_COMPLETED',
  'quiz_response',
  NOW(),
  '{"duration_seconds": 3700, "sla_budget_seconds": 3600}'::jsonb
);
EOF

# Run SLA monitor (should trigger alert)
python monitor_cleanup_sla.py
```

## Future Enhancements

Planned improvements:
- [ ] Predictive SLA monitoring (ML-based forecasting)
- [ ] Auto-remediation for common issues (reduce batch size, clear zombie locks)
- [ ] Integration with Grafana/Datadog for advanced dashboards
- [ ] Anomaly detection for throughput/success rate
- [ ] Cost tracking (database CPU, Vercel Blob API calls)

## References

- SLA budgets: `/mnt/f/saas projects/ai-based-meal-plan/specs/001-keto-meal-plan-generator/plan.md`
- Cleanup scripts: `/mnt/f/saas projects/ai-based-meal-plan/scripts/cleanup/`
- Audit logging: `/mnt/f/saas projects/ai-based-meal-plan/backend/services/audit.py`
