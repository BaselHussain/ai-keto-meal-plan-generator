# Scripts Directory Structure

```
scripts/
├── README.md                          # Main documentation (you are here)
├── STRUCTURE.md                       # This file - visual directory map
│
├── cleanup/                           # Automated data cleanup jobs
│   ├── README.md                      # Cleanup scripts documentation
│   ├── .gitkeep                       # Git tracking placeholder
│   ├── cleanup_quiz_responses.py      # [Future] Delete quiz data after 24h
│   ├── cleanup_pdfs.py                # [Future] Delete PDFs after 90 days
│   ├── cleanup_magic_links.py         # [Future] Delete expired tokens
│   └── cleanup_blacklist.py           # [Future] Remove 90-day blacklist entries
│
├── sla-monitoring/                    # SLA breach detection and alerting
│   ├── README.md                      # SLA monitoring documentation
│   ├── .gitkeep                       # Git tracking placeholder
│   ├── monitor_cleanup_sla.py         # [Future] Track cleanup job performance
│   ├── monitor_manual_resolution_queue.py  # [Future] Monitor queue depth/age
│   └── check_cleanup_health.py        # [Future] Validate dependencies
│
├── manual-resolution/                 # Manual intervention queue management
│   ├── README.md                      # Manual resolution documentation
│   ├── .gitkeep                       # Git tracking placeholder
│   ├── add_to_queue.py                # [Future] Add items to queue
│   ├── process_queue.py               # [Future] Operator resolution workflow
│   ├── escalate_breaches.py           # [Future] Auto-escalate SLA breaches
│   └── report_metrics.py              # [Future] Queue health reports
│
├── retention/                         # Data retention policy enforcement
│   ├── README.md                      # Retention policy documentation
│   ├── .gitkeep                       # Git tracking placeholder
│   ├── enforce_retention_policies.py  # [Future] Master retention orchestrator
│   ├── archive_before_delete.py       # [Future] Archive to cold storage
│   ├── generate_compliance_report.py  # [Future] GDPR/compliance reports
│   ├── enforce_gdpr_deletion.py       # [Future] Right to erasure workflow
│   └── retention_policies.yaml        # [Future] Retention policy configuration
│
└── utils/                             # Shared utilities and helpers
    ├── README.md                      # Utilities documentation
    ├── .gitkeep                       # Git tracking placeholder
    ├── db_utils.py                    # [Future] Database connection pooling
    ├── redis_lock.py                  # [Future] Distributed locking
    ├── logging_utils.py               # [Future] Structured logging
    ├── metrics_utils.py               # [Future] Metrics emission
    ├── retry_utils.py                 # [Future] Retry logic + circuit breaker
    ├── script_template.py             # [Future] Boilerplate for new scripts
    └── test_helpers.py                # [Future] Test fixtures and mocks
```

## Current Status

**Phase**: Directory structure setup complete
**Next Phase**: Phase 9 - Implement cleanup job scripts

## Quick Reference

| Directory | Purpose | Script Count | Status |
|-----------|---------|--------------|--------|
| `cleanup/` | Delete expired data per retention policies | 4 | Planned |
| `sla-monitoring/` | Monitor job performance and SLA breaches | 3 | Planned |
| `manual-resolution/` | Manage human intervention queue | 4 | Planned |
| `retention/` | Enforce compliance and GDPR requirements | 4 | Planned |
| `utils/` | Shared libraries for all scripts | 7 | Planned |

## Documentation Index

- **Main README**: `/scripts/README.md` - Overview and setup instructions
- **Cleanup Jobs**: `/scripts/cleanup/README.md` - Automated deletion workflows
- **SLA Monitoring**: `/scripts/sla-monitoring/README.md` - Performance tracking
- **Manual Resolution**: `/scripts/manual-resolution/README.md` - Queue management
- **Retention Policies**: `/scripts/retention/README.md` - Compliance enforcement
- **Utilities**: `/scripts/utils/README.md` - Shared libraries

## Implementation Sequence

When implementing scripts in Phase 9, follow this order:

1. **Utils first** (foundation for all other scripts):
   - `db_utils.py` - Database connections
   - `redis_lock.py` - Distributed locks
   - `logging_utils.py` - Structured logging
   - `metrics_utils.py` - Observability
   - `retry_utils.py` - Error handling

2. **Cleanup scripts** (core operational functionality):
   - `cleanup_quiz_responses.py` - Most frequent (daily)
   - `cleanup_magic_links.py` - Second most frequent (hourly)
   - `cleanup_pdfs.py` - Resource-intensive
   - `cleanup_blacklist.py` - Least frequent

3. **SLA monitoring** (operational visibility):
   - `check_cleanup_health.py` - Validate setup
   - `monitor_cleanup_sla.py` - Track performance
   - `monitor_manual_resolution_queue.py` - Queue alerts

4. **Manual resolution** (handle edge cases):
   - `add_to_queue.py` - Integration with cleanup scripts
   - `process_queue.py` - Operator workflow
   - `escalate_breaches.py` - Auto-escalation
   - `report_metrics.py` - Queue analytics

5. **Retention policies** (compliance layer):
   - `enforce_retention_policies.py` - Master orchestrator
   - `enforce_gdpr_deletion.py` - Right to erasure
   - `archive_before_delete.py` - Cold storage
   - `generate_compliance_report.py` - Audit reports

## Testing Strategy

Each script requires:
- Unit tests (70%+ coverage)
- Integration tests (with test database)
- Dry-run mode validation
- SLA performance benchmarks

Test files location: `/backend/tests/scripts/`

## Deployment Checklist

Before deploying scripts to production:
- [ ] Environment variables configured in Render
- [ ] Cron schedules defined in `render.yaml`
- [ ] Distributed locks tested (no concurrent execution)
- [ ] Audit logging verified (all deletions captured)
- [ ] SLA monitoring alerts configured
- [ ] Dry-run tested with production-like data
- [ ] Runbooks documented for operators
- [ ] Rollback plan prepared

## Contact

For questions about:
- **Data retention policies**: Consult `/specs/001-keto-meal-plan-generator/plan.md`
- **Compliance requirements**: Contact compliance team
- **Operational issues**: Check runbooks in each subdirectory README
- **Script implementation**: See utility documentation in `/scripts/utils/README.md`
