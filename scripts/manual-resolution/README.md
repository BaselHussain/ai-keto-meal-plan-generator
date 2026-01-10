# Manual Resolution Queue Scripts

Scripts for managing operations that require human intervention, queue prioritization, and resolution workflows.

## Overview

Some cleanup operations cannot be fully automated due to:
- Ambiguous edge cases requiring human judgment
- Failed automated deletions needing investigation
- Compliance requirements for manual review before deletion
- External API failures requiring retry coordination

This directory contains scripts that manage a queue of such items, prioritize them, and facilitate operator resolution.

## Queue Table Schema

The manual resolution queue is stored in the `manual_resolution_queue` table:

```sql
CREATE TABLE manual_resolution_queue (
  id SERIAL PRIMARY KEY,
  item_type VARCHAR(50) NOT NULL,           -- 'pdf_deletion_failed', 'quiz_orphaned', etc.
  resource_type VARCHAR(50) NOT NULL,       -- 'meal_plan', 'quiz_response', etc.
  resource_id INTEGER NOT NULL,             -- ID of the resource requiring attention
  priority VARCHAR(20) NOT NULL,            -- 'low', 'medium', 'high', 'critical'
  reason TEXT NOT NULL,                     -- Why it's in the queue
  context JSONB,                            -- Additional context for resolution
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  assigned_to VARCHAR(100),                 -- Operator username
  assigned_at TIMESTAMP,
  resolved_at TIMESTAMP,
  resolution TEXT,                          -- How it was resolved
  resolution_metadata JSONB,                -- Additional resolution details
  status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'assigned', 'resolved', 'escalated'
  escalated_at TIMESTAMP,
  sla_deadline TIMESTAMP,                   -- When this item breaches SLA

  INDEX idx_mrq_status (status),
  INDEX idx_mrq_priority (priority),
  INDEX idx_mrq_created_at (created_at),
  INDEX idx_mrq_sla_deadline (sla_deadline)
);
```

## Scripts

### add_to_queue.py

**Purpose**: Add items to manual resolution queue (called by cleanup scripts on failure)

**Usage**:
```python
from scripts.manual_resolution.add_to_queue import add_to_queue

# Example: PDF deletion failed due to Vercel API error
add_to_queue(
    item_type="pdf_deletion_failed",
    resource_type="meal_plan",
    resource_id=12345,
    priority="medium",
    reason="Vercel Blob API returned 503 after 3 retry attempts",
    context={
        "pdf_url": "https://blob.vercel-storage.com/...",
        "pdf_generated_at": "2023-10-01T12:00:00Z",
        "retry_count": 3,
        "last_error": "ServiceUnavailable: Blob service temporarily unavailable"
    },
    sla_hours=24  # Must be resolved within 24 hours
)
```

**Priorities**:
- **critical**: Data compliance violation (e.g., GDPR deletion request not honored) - SLA: 4 hours
- **high**: User-facing issue (e.g., orphaned quiz data blocking new submission) - SLA: 24 hours
- **medium**: Operational cleanup (e.g., failed PDF deletion) - SLA: 7 days
- **low**: Non-urgent maintenance (e.g., orphaned test data) - SLA: 30 days

**Item Types**:
- `pdf_deletion_failed`: Vercel Blob API failure
- `quiz_orphaned`: Quiz response without associated user
- `blacklist_disputed`: User appeals blacklist entry
- `retention_exception`: Regulatory hold prevents deletion
- `foreign_key_violation`: Cleanup blocked by unexpected reference

### process_queue.py

**Purpose**: Present queue items to operators for resolution via CLI or UI

**Execution Strategy**:
1. Query queue for pending items ordered by priority and SLA deadline
2. For each item:
   - Display context (reason, resource details, priority, age)
   - Present resolution options based on item type
   - Capture operator decision and justification
   - Update queue item with resolution details
   - Execute resolution action (delete, retry, escalate, defer)
3. Emit metrics (resolution rate, time-to-resolution)

**CLI Mode**:
```bash
python process_queue.py --mode cli

# Output:
Queue Item #42 (MEDIUM priority, age: 3 days)
Type: pdf_deletion_failed
Resource: meal_plan #12345
Reason: Vercel Blob API returned 503 after 3 retry attempts
Context:
  - PDF URL: https://blob.vercel-storage.com/...
  - Generated: 2023-10-01T12:00:00Z
  - Last error: ServiceUnavailable

Resolution options:
  1. Retry deletion now
  2. Mark as permanently failed (update DB only)
  3. Escalate to engineering
  4. Defer for 24 hours

Your choice [1-4]: 1

Action: Retrying PDF deletion...
Result: ✓ PDF deleted successfully
Resolution recorded: "Manual retry successful after Vercel API recovery"
```

**UI Mode** (future enhancement):
- Web dashboard for operators to browse queue
- Batch resolution for similar items
- Search/filter by type, priority, age
- One-click resolution for common cases

**Schedule**: On-demand (operators run when processing queue)

### escalate_breaches.py

**Purpose**: Auto-escalate items that exceed SLA deadline

**Execution Strategy**:
1. Query queue for items where `NOW() > sla_deadline` AND `status = 'pending'`
2. For each breached item:
   - Update status to `'escalated'`
   - Set `escalated_at = NOW()`
   - Send alert to on-call engineer with full context
   - Create incident in PagerDuty (critical priority only)
3. Emit metrics

**Schedule**: Every 30 minutes

**Cron Expression**: `*/30 * * * *`

**Escalation Alert**:
```json
{
  "alert_type": "manual_resolution_sla_breach",
  "item_id": 42,
  "item_type": "pdf_deletion_failed",
  "priority": "medium",
  "sla_deadline": "2026-01-02T15:00:00Z",
  "breach_duration_hours": 8,
  "reason": "Vercel Blob API returned 503 after 3 retry attempts",
  "recommended_action": "Check Vercel status page, retry deletion, or mark as permanently failed",
  "queue_url": "https://app.example.com/admin/manual-resolution-queue/42"
}
```

### report_metrics.py

**Purpose**: Generate reports on queue health and operator performance

**Metrics**:
- Queue depth by priority
- Average time-to-resolution by item type
- SLA compliance rate (% resolved within deadline)
- Operator resolution rate (items/day per operator)
- Escalation rate (% of items escalated)

**Report Output**:
```
Manual Resolution Queue Report (2026-01-03)

Queue Status:
  - Total pending: 42
  - Critical: 1 (SLA: 4h)
  - High: 8 (SLA: 24h)
  - Medium: 25 (SLA: 7d)
  - Low: 8 (SLA: 30d)

Performance (Last 30 Days):
  - Items resolved: 1,234
  - Avg time-to-resolution: 18.3 hours
  - SLA compliance: 94.2%
  - Escalation rate: 2.1%

By Item Type:
  - pdf_deletion_failed: 15 pending, avg resolution 12h
  - quiz_orphaned: 5 pending, avg resolution 6h
  - blacklist_disputed: 2 pending, avg resolution 48h

Top Resolvers:
  - alice@example.com: 45 items, avg 8h
  - bob@example.com: 38 items, avg 12h
```

**Schedule**: Daily at 9:00 AM UTC (emailed to team)

**Cron Expression**: `0 9 * * *`

## Resolution Workflows

### PDF Deletion Failed

**Context Required**:
- PDF URL
- Meal plan ID
- Error message from Vercel API
- Retry count

**Resolution Options**:
1. **Retry Deletion**: Call Vercel Blob API again (may succeed if transient error)
2. **Mark as Permanently Failed**: Update DB (`pdf_url = NULL, pdf_deleted_at = NOW()`) but don't retry API
3. **Escalate**: If Vercel API is consistently failing, escalate to engineering for investigation

**Operator Decision Factors**:
- Check Vercel status page for ongoing incidents
- If error is `404 NotFound`, PDF already deleted → mark as permanently failed
- If error is `503 ServiceUnavailable`, retry after 1 hour
- If persistent (>3 days), escalate

### Quiz Orphaned

**Context Required**:
- Quiz response ID
- User ID (if any)
- Creation timestamp
- Foreign key references

**Resolution Options**:
1. **Delete Immediately**: If truly orphaned (no FK references)
2. **Associate with User**: If user ID exists but FK missing, repair association
3. **Defer**: If recent (<24h), wait to see if user completes flow

**Operator Decision Factors**:
- Check if quiz is referenced by meal_plan (if yes, don't delete)
- Check if user exists (if yes, associate)
- Check age (if >7 days, safe to delete)

### Blacklist Disputed

**Context Required**:
- Email address
- Blacklist reason
- User's appeal message
- Historical payment data

**Resolution Options**:
1. **Remove from Blacklist**: If appeal is valid (e.g., legitimate payment failure)
2. **Reject Appeal**: If abuse/fraud confirmed
3. **Escalate to Support**: If requires manual investigation

**Operator Decision Factors**:
- Review payment history (multiple failed payments = likely keep on blacklist)
- Check for fraud indicators (VPN, multiple retries, etc.)
- Consult support team for context

## Configuration

Environment variables:

```bash
# SLA Deadlines (hours)
MRQ_SLA_CRITICAL=4
MRQ_SLA_HIGH=24
MRQ_SLA_MEDIUM=168      # 7 days
MRQ_SLA_LOW=720         # 30 days

# Alerting
MRQ_ALERT_SLACK_WEBHOOK=...
MRQ_ALERT_PAGERDUTY_KEY=...

# Processing
MRQ_BATCH_SIZE=10       # Items to process per CLI session
```

## Monitoring

Queue metrics emitted:

```json
{
  "metric": "manual_resolution_queue_depth",
  "total_pending": 42,
  "by_priority": {
    "critical": 1,
    "high": 8,
    "medium": 25,
    "low": 8
  },
  "oldest_item_hours": 72,
  "items_breaching_sla": 3,
  "timestamp": "2026-01-03T15:00:00Z"
}
```

## Operator Training

New operators should:
1. Read this README completely
2. Shadow experienced operator for 5 queue resolutions
3. Practice on low-priority items first
4. Escalate when uncertain (better to escalate than guess)
5. Document unusual cases in resolution notes

## Runbook: Common Resolutions

### Retry Failed PDF Deletion

```bash
# Manually delete PDF from Vercel Blob
curl -X DELETE "https://blob.vercel-storage.com/..." \
  -H "Authorization: Bearer $BLOB_READ_WRITE_TOKEN"

# Update database
psql $DATABASE_URL -c "
  UPDATE meal_plans
  SET pdf_url = NULL, pdf_deleted_at = NOW()
  WHERE id = 12345;
"

# Mark queue item as resolved
psql $DATABASE_URL -c "
  UPDATE manual_resolution_queue
  SET status = 'resolved',
      resolved_at = NOW(),
      resolution = 'Manual PDF deletion via API and DB update',
      resolution_metadata = '{\"deleted_by\": \"alice@example.com\"}'::jsonb
  WHERE id = 42;
"
```

### Delete Orphaned Quiz Response

```bash
# Verify no foreign key references
psql $DATABASE_URL -c "
  SELECT * FROM meal_plans WHERE quiz_response_id = 67890;
"
# (Should return 0 rows)

# Delete quiz response
psql $DATABASE_URL -c "
  DELETE FROM quiz_responses WHERE id = 67890;
"

# Mark queue item as resolved
psql $DATABASE_URL -c "
  UPDATE manual_resolution_queue
  SET status = 'resolved',
      resolved_at = NOW(),
      resolution = 'Orphaned quiz response deleted (no FK references)',
      resolution_metadata = '{\"deleted_by\": \"bob@example.com\"}'::jsonb
  WHERE id = 43;
"
```

## Testing

Unit tests for queue operations:

```python
# tests/scripts/manual_resolution/test_queue.py

def test_add_to_queue_creates_item():
    """Adding item creates record with correct fields."""

def test_priority_determines_sla_deadline():
    """Critical items have 4h SLA, high 24h, etc."""

def test_escalation_triggers_for_breached_items():
    """Items past SLA deadline are auto-escalated."""

def test_resolution_updates_status_and_timestamp():
    """Resolving item sets status='resolved' and resolved_at."""
```

Run tests:
```bash
cd /mnt/f/saas\ projects/ai-based-meal-plan/backend
pytest tests/scripts/manual_resolution/ -v
```

## Future Enhancements

Planned improvements:
- [ ] Web UI for queue management (drag-and-drop prioritization)
- [ ] Batch resolution for similar items (e.g., all PDFs from same day)
- [ ] Auto-resolution for common patterns (ML-based)
- [ ] Integration with support ticketing system (Zendesk, Intercom)
- [ ] Resolution templates for common cases (one-click resolution)

## References

- Cleanup scripts: `/mnt/f/saas projects/ai-based-meal-plan/scripts/cleanup/`
- SLA monitoring: `/mnt/f/saas projects/ai-based-meal-plan/scripts/sla-monitoring/`
- Database schema: `/mnt/f/saas projects/ai-based-meal-plan/backend/models/`
