# Data Retention Policy Scripts

Automated enforcement of data retention policies with compliance tracking, audit logging, and regulatory adherence.

## Overview

This directory contains scripts that enforce data retention policies across the application lifecycle:

1. **Policy Enforcement**: Ensure data is retained/deleted per compliance requirements
2. **Archive-Before-Delete**: Archive data to cold storage before hard deletion
3. **Compliance Reporting**: Generate reports demonstrating retention policy adherence
4. **GDPR/CCPA Support**: Right to erasure, data portability, retention minimums/maximums

All retention scripts prioritize compliance, auditability, and safety over performance.

## Retention Policies (from specs)

| Data Type | Retention Period | Policy Type | Compliance |
|-----------|------------------|-------------|------------|
| Quiz Responses | 24 hours after creation OR immediately after purchase | Time-based | Data minimization (GDPR) |
| PDFs | 90 days after generation | Time-based | Storage cost optimization |
| Magic Link Tokens | 24 hours after creation (soft-delete + 30 days) | Time-based + Grace Period | Security best practice |
| Email Blacklist | 90 days (unless `is_permanent = TRUE`) | Time-based | Right to be forgotten (GDPR) |
| Audit Logs | Indefinite | Permanent | Compliance audit trail |
| User Accounts | Until user-initiated deletion | User-controlled | GDPR right to erasure |
| Payment Records | 7 years | Regulatory | Tax/financial compliance |

## Scripts

### enforce_retention_policies.py

**Purpose**: Orchestrate all retention policy enforcement (master script)

**Execution Strategy**:
1. Load retention policies from configuration
2. For each policy:
   - Identify data subject to policy (query by timestamp/status)
   - Validate compliance constraints (e.g., regulatory holds)
   - Execute retention action (delete, archive, soft-delete)
   - Log enforcement to audit table
3. Generate compliance report
4. Emit metrics

**Schedule**: Daily at 1:00 AM UTC

**Cron Expression**: `0 1 * * *`

**Configuration** (`retention_policies.yaml`):
```yaml
policies:
  - name: quiz_responses_24h
    data_type: quiz_response
    retention_period: 24 hours
    retention_action: hard_delete
    compliance_reason: GDPR data minimization
    exceptions:
      - condition: has_associated_meal_plan
        action: delete_immediately_after_pdf_generation

  - name: pdfs_90d
    data_type: meal_plan_pdf
    retention_period: 90 days
    retention_action: delete_blob_keep_metadata
    compliance_reason: Storage cost optimization
    exceptions:
      - condition: user_requested_retention
        action: extend_indefinitely

  - name: magic_links_24h_soft
    data_type: magic_link_token
    retention_period: 24 hours
    retention_action: soft_delete
    grace_period: 30 days
    compliance_reason: Security + audit trail

  - name: magic_links_30d_hard
    data_type: magic_link_token
    retention_period: 30 days after soft_delete
    retention_action: hard_delete
    compliance_reason: Data minimization

  - name: blacklist_90d
    data_type: email_blacklist
    retention_period: 90 days
    retention_action: hard_delete
    compliance_reason: GDPR right to be forgotten
    exceptions:
      - condition: is_permanent = TRUE
        action: retain_indefinitely

  - name: audit_logs_indefinite
    data_type: audit_log
    retention_period: indefinite
    retention_action: retain
    compliance_reason: Compliance audit trail

  - name: payment_records_7y
    data_type: payment_transaction
    retention_period: 7 years
    retention_action: archive_to_cold_storage
    compliance_reason: Tax compliance (IRS requirement)
```

**Policy Validation**:
Before enforcing any policy, validate:
- No regulatory hold on data (e.g., legal discovery request)
- No active user session referencing data
- Foreign key dependencies resolved
- Audit log captures deletion reason

**Metrics Emitted**:
```json
{
  "metric": "retention_policy_enforcement",
  "policy": "quiz_responses_24h",
  "records_evaluated": 5000,
  "records_deleted": 4800,
  "records_skipped": 200,
  "skip_reasons": {
    "regulatory_hold": 0,
    "active_session": 50,
    "exception_matched": 150
  },
  "enforcement_duration_seconds": 45,
  "timestamp": "2026-01-03T01:15:30Z"
}
```

### archive_before_delete.py

**Purpose**: Archive data to cold storage before permanent deletion

**Use Cases**:
- Payment records older than 7 years (tax compliance)
- User account data after deletion request (90-day grace period)
- Historical meal plans for analytics (anonymized)

**Execution Strategy**:
1. Query data eligible for archival (based on retention policy)
2. For each record:
   - Export to JSON format
   - Compress (gzip)
   - Upload to archive storage (Neon cold storage, S3 Glacier, etc.)
   - Verify upload successful
   - Delete from operational database
   - Log archival to audit table
3. Emit metrics

**Archive Format**:
```json
{
  "archive_metadata": {
    "archive_id": "20260103-payment-records-batch-001",
    "data_type": "payment_transaction",
    "record_count": 1000,
    "date_range": {
      "start": "2019-01-01",
      "end": "2019-12-31"
    },
    "archived_at": "2026-01-03T01:30:00Z",
    "retention_policy": "payment_records_7y",
    "compression": "gzip"
  },
  "records": [
    {
      "id": 12345,
      "user_id": 67890,
      "amount": 39.99,
      "currency": "USD",
      "transaction_date": "2019-06-15T14:22:00Z",
      "status": "completed",
      ...
    },
    ...
  ]
}
```

**Archive Storage Options**:
- **Neon Cold Storage**: For infrequent access (>90 days)
- **AWS S3 Glacier**: For long-term archival (7+ years)
- **Local Backup**: For disaster recovery (encrypted)

**Schedule**: Monthly (1st of month at 2:00 AM UTC)

**Cron Expression**: `0 2 1 * *`

### generate_compliance_report.py

**Purpose**: Generate reports demonstrating retention policy adherence for audits

**Report Types**:

1. **Data Inventory Report**: What data we store, how long, why
2. **Retention Enforcement Report**: What was deleted, when, by which policy
3. **Exception Report**: Data retained beyond policy (with justification)
4. **GDPR Compliance Report**: Right to erasure, data minimization, lawful basis
5. **Audit Trail Report**: Complete history of data lifecycle events

**Execution Strategy**:
1. Query audit logs for time period (default: last 30 days)
2. Aggregate by policy, data type, action
3. Identify exceptions and anomalies
4. Generate report in PDF or CSV format
5. Email to compliance team
6. Store report in secure archive

**Report Output** (GDPR Compliance Report):
```
GDPR Compliance Report - January 2026

Data Minimization:
  ✓ Quiz responses: 4,800 deleted within 24h (100% compliance)
  ✓ Magic link tokens: 1,200 soft-deleted after expiry (100% compliance)
  ✓ Email blacklist: 50 removed after 90 days (100% compliance)

Right to Erasure:
  - User deletion requests: 3 (all fulfilled within 30 days)
  - Data types deleted: user_account, quiz_responses, meal_plans, payment_metadata
  - Audit trail: Retained per legal requirement

Data Portability:
  - Export requests: 2 (fulfilled within 7 days)
  - Data formats: JSON, PDF

Lawful Basis for Processing:
  - Quiz responses: Contractual necessity (meal plan generation)
  - PDFs: Contractual necessity (service delivery)
  - Audit logs: Legal obligation (compliance)

Exceptions:
  - Payment records retained 7 years: Tax compliance (IRS requirement)
  - Audit logs retained indefinitely: Legal obligation

Compliance Status: ✓ COMPLIANT
Next Review: 2026-02-01
```

**Schedule**: Monthly (1st of month at 9:00 AM UTC, after archival)

**Cron Expression**: `0 9 1 * *`

### enforce_gdpr_deletion.py

**Purpose**: Process GDPR "right to erasure" (right to be forgotten) requests

**Execution Strategy**:
1. Query for user deletion requests (`user_deletion_requests` table)
2. For each request:
   - Validate request (user identity, consent)
   - Identify all user data across tables (user, quiz, meal_plans, payments, etc.)
   - For each data type:
     - **Delete immediately**: Quiz responses, magic links, sessions
     - **Archive then delete**: Payment metadata (retain transaction ID for financial compliance)
     - **Anonymize**: Audit logs (replace user ID with pseudonym)
     - **Retain**: Legal obligations (e.g., fraud investigations, tax records)
   - Log all deletions to audit table
   - Mark request as fulfilled
   - Email confirmation to user
3. Emit metrics

**Data Deletion Scope**:
| Data Type | Action | Justification |
|-----------|--------|---------------|
| User Account | DELETE | Primary request |
| Quiz Responses | DELETE | Personal data |
| Meal Plans (metadata) | DELETE | Personal data |
| PDFs | DELETE (Blob) | Personal data |
| Payment Transactions | ANONYMIZE (user_id → pseudonym) | Financial/tax compliance |
| Audit Logs | ANONYMIZE (user_id → pseudonym) | Legal compliance |
| Email Blacklist | DELETE | No longer needed |
| Magic Link Tokens | DELETE | Personal data |

**Anonymization Strategy**:
```sql
-- Replace user ID with pseudonym in audit logs
UPDATE audit_log
SET metadata = jsonb_set(
  metadata,
  '{user_id}',
  to_jsonb(MD5('user_' || user_id || '_deleted'))
)
WHERE metadata->>'user_id' = '67890';
```

**Schedule**: Daily at 3:00 AM UTC (to honor 30-day GDPR deadline)

**Cron Expression**: `0 3 * * *`

**GDPR Deadline**: User deletion requests must be fulfilled within 30 days

**Metrics Emitted**:
```json
{
  "metric": "gdpr_deletion_request",
  "request_id": 42,
  "user_id": 67890,
  "request_date": "2025-12-15T10:00:00Z",
  "fulfillment_date": "2026-01-03T03:15:00Z",
  "days_to_fulfillment": 19,
  "data_deleted": {
    "user_account": 1,
    "quiz_responses": 3,
    "meal_plans": 2,
    "pdfs": 2,
    "magic_links": 5
  },
  "data_anonymized": {
    "payment_transactions": 2,
    "audit_logs": 45
  },
  "compliance_status": "within_deadline"
}
```

## Configuration

Environment variables:

```bash
# Retention Policy
RETENTION_CONFIG_PATH=./scripts/retention/retention_policies.yaml

# Archive Storage
ARCHIVE_STORAGE_TYPE=s3_glacier         # Options: neon_cold, s3_glacier, local
ARCHIVE_S3_BUCKET=my-app-cold-storage
ARCHIVE_S3_ACCESS_KEY=...
ARCHIVE_S3_SECRET_KEY=...

# Compliance
COMPLIANCE_REPORT_EMAIL=compliance@example.com
GDPR_DELETION_DEADLINE_DAYS=30

# Safety
RETENTION_DRY_RUN=false
RETENTION_BATCH_SIZE=1000
```

## Compliance Audit Trail

Every retention action is logged to `audit_log` table:

```sql
INSERT INTO audit_log (
  actor,                -- 'system:retention_policy'
  action,               -- 'DELETE', 'ARCHIVE', 'ANONYMIZE'
  resource_type,        -- 'quiz_response', 'payment_transaction', etc.
  resource_id,          -- ID of deleted/archived record
  timestamp,            -- NOW()
  reason,               -- 'retention_policy_quiz_responses_24h'
  metadata              -- JSONB with policy details, original data hash
) VALUES (
  'system:retention_policy',
  'DELETE',
  'quiz_response',
  12345,
  NOW(),
  'retention_policy_quiz_responses_24h',
  '{
    "policy": "quiz_responses_24h",
    "retention_period": "24 hours",
    "compliance_reason": "GDPR data minimization",
    "data_hash": "sha256:abcdef...",
    "deleted_at": "2026-01-03T01:15:30Z"
  }'::jsonb
);
```

Audit logs are:
- **Immutable**: No UPDATE/DELETE permissions (append-only)
- **Tamper-evident**: SHA256 hash of deleted data
- **Retained indefinitely**: Legal compliance requirement
- **Queryable**: For compliance reports and audits

## Safety and Testing

### Dry-Run Mode

Always test retention policies with dry-run before production:

```bash
RETENTION_DRY_RUN=true python enforce_retention_policies.py

# Output:
[DRY-RUN] Policy: quiz_responses_24h
[DRY-RUN] Would delete 4,800 records older than 24 hours
[DRY-RUN] Skipping 200 records (exceptions matched)
[DRY-RUN] Compliance: 100% within policy
```

### Pre-Deployment Checklist

Before enabling retention policies:
- [ ] Retention policy documented in ADR
- [ ] Legal/compliance team approval obtained
- [ ] Audit logging tested and verified
- [ ] Archive storage configured and accessible
- [ ] GDPR deletion workflow tested end-to-end
- [ ] Compliance reports generated and reviewed
- [ ] Exception handling covers edge cases
- [ ] Dry-run tested with production-like data
- [ ] Rollback plan documented

## Runbook: GDPR Deletion Request

### Scenario: User Requests Account Deletion

**Step 1: Validate Request**
```sql
-- Create deletion request
INSERT INTO user_deletion_requests (user_id, request_date, email, status)
VALUES (67890, NOW(), 'user@example.com', 'pending');
```

**Step 2: Identify User Data**
```sql
-- Audit all data associated with user
SELECT 'user_account' AS table_name, COUNT(*) FROM users WHERE id = 67890
UNION ALL
SELECT 'quiz_responses', COUNT(*) FROM quiz_responses WHERE user_id = 67890
UNION ALL
SELECT 'meal_plans', COUNT(*) FROM meal_plans WHERE user_id = 67890
UNION ALL
SELECT 'payment_transactions', COUNT(*) FROM payment_transactions WHERE user_id = 67890;
```

**Step 3: Execute Deletion**
```bash
# Run GDPR deletion script
python enforce_gdpr_deletion.py --user-id 67890 --request-id 42

# Verify deletion
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users WHERE id = 67890;"  # Should return 0
```

**Step 4: Confirm to User**
Email template:
```
Subject: Your Account Deletion Request Has Been Fulfilled

Dear User,

Your account deletion request submitted on 2025-12-15 has been fulfilled.

Data Deleted:
- User account
- Quiz responses (3)
- Meal plans (2)
- PDFs (2)

Data Retained (Legal Requirement):
- Payment transaction metadata (anonymized)
- Audit logs (anonymized)

You will no longer receive emails from us.

Thank you,
Support Team
```

## Future Enhancements

Planned improvements:
- [ ] Automated GDPR deletion request workflow (user-initiated via UI)
- [ ] Data portability API (export user data to JSON/CSV)
- [ ] Retention policy versioning (track changes over time)
- [ ] Compliance dashboard (real-time monitoring)
- [ ] Integration with DPO (Data Protection Officer) tools

## References

- GDPR compliance guide: https://gdpr.eu/
- Retention policies: `/mnt/f/saas projects/ai-based-meal-plan/specs/001-keto-meal-plan-generator/plan.md`
- Audit logging: `/mnt/f/saas projects/ai-based-meal-plan/backend/services/audit.py`
- Database schema: `/mnt/f/saas projects/ai-based-meal-plan/backend/models/`
