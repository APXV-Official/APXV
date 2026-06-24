# APXV1 — Runbook: Operations

**Purpose:** Day-to-day operations, monitoring, and maintenance of an APXV1 deployment.

---

## 1. Daily Operations Checklist

- Verify all containers/services are running (`docker ps` or equivalent)
- Check recent audit log entries for anomalies
- Confirm disk space on `managed/` volume
- Review any failed capability checks or governance violations

---

## 2. Monitoring & Health

### Key Signals to Watch
- Audit log growth rate
- Number of artifacts written per day
- Capability check failure rate
- Agent execution success/failure rate
- Cost and latency of LLM agents (if enabled)

### Health Check Command

```bash
python -c "
from agents.artifact_provider import FileArtifactProvider
from agents.audit_logger import AuditLogger
print('Artifact provider and audit logger healthy')
"
```

---

## 3. Common Operational Tasks

### Viewing Recent Activity
```bash
tail -n 50 managed/audit/*.log
```

### Checking Artifact Chain Integrity
```bash
python -c "
from agents.artifact_provider import FileArtifactProvider
p = FileArtifactProvider()
print('Total artifacts:', len(p.list_artifacts()))
"
```

### Restarting the Service
```bash
docker-compose restart apx-v1
```

---

## 4. Backup Recommendations

- Regularly back up the entire `managed/` directory
- Include `managed/keys/` (contains verification keys)
- Store backups in a separate, secure location
- Test restore procedure periodically

---

## 5. Logging & Alerting

- All critical events are written to `managed/audit/`
- Use structured JSON logs for integration with log aggregation tools
- Recommended alerts:
  - Sudden spike in capability denials
  - Governance rule violations
  - Audit log tampering detection (`AuditLogger.verify_chain()` returns False)

---

## 6. Scaling Considerations

- The current design is single-node friendly
- For higher scale, consider:
  - Shared storage for `managed/`
  - Centralized log aggregation
  - Multiple APXV1 instances with coordinated governance rules

---

*Last updated: 2026-06-10*