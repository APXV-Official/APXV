# APXV — Runbook: Operations

**Purpose:** Day-to-day operations, monitoring, and maintenance of an APXV deployment.

---

## 1. Daily Operations Checklist

- Verify all containers/services are running (`docker ps` or equivalent)
- Check recent audit log entries for anomalies
- Confirm disk space on `managed/` volume
- Review any failed capability checks or governance violations
- Run `python -m scripts.apxv_doctor` on a schedule (or `GET /health` for API deployments)

---

## 2. Monitoring & Health

### Key Signals to Watch
- Audit log growth rate
- Number of artifacts written per day
- Capability check failure rate
- Agent execution success/failure rate
- Cost and latency of LLM agents (if enabled)
- Integrity status (`healthy` vs `degraded` on `/health`)

### Health Check Commands

```bash
python -m scripts.apxv_doctor
python -m scripts.apxv_ctl integrity
curl http://127.0.0.1:8741/health
```

`/health` (no auth) returns `status: healthy` or `degraded` plus `integrity.audit_summary` per log when degraded (v1.2.2+).

---

## 3. Common Operational Tasks

### Viewing Recent Activity
```bash
tail -n 50 managed/audit/*.log
```

### Checking Artifact Chain Integrity
```bash
python -m scripts.apxv_ctl integrity
```

### Restarting the Service
```bash
docker compose restart apxv
```

---

## 4. Audit log recovery (v1.2.2+)

When integrity fails, classify before acting (`python -m scripts.apxv_doctor` or `python -m scripts.apxv_ctl integrity` — v1.2.2+ reports `issue: corrupt_lines` vs `chain_break`).

**Before any destructive step:**

```bash
python -m scripts.apxv_ctl backup-create
# optional archive of audit dir
mkdir -p managed/backups/audit-$(date +%Y%m%d)
cp managed/audit/*.log managed/backups/audit-$(date +%Y%m%d)/ 2>/dev/null || true
```

Confirm classification:

```bash
python -m scripts.apxv_ctl integrity
python -m scripts.apxv_doctor
```

**Corrupt lines** (`corrupt_line_count` > 0, `issue: corrupt_lines`):
1. Back up entire `managed/` (see above)
2. Remove only the affected log files under `managed/audit/` (or all `*.log` if unsure)
3. Run `python -m scripts.setup_first_run`
4. Re-check: `python -m scripts.apxv_ctl integrity` → HEALTHY

**Hash chain break** (`corrupt_line_count` == 0, `chain_valid: false`, `issue: chain_break`):
1. Back up `managed/` if artifacts and config matter (`backup-create` + copy `managed/audit/`)
2. Clear audit logs (pick one scope):
   - **Audit only:** `rm -f managed/audit/*.log` (Linux/macOS) or `Remove-Item managed\audit\*.log` (Windows)
   - **Broader runtime reset:** `python -m scripts.fresh_reset` (clears audit/config/store artifacts; keeps governance templates)
3. Run `python -m scripts.setup_first_run`
4. Re-check integrity and `/health` — expect `healthy` on a fresh chain

**After recovery:** re-run a pack demo to confirm attest path:

```bash
python -m scripts.apxv_demo --pack reference
python -m scripts.apxv_ctl integrity
```

Pipelines and ZK verification may continue to work while health is degraded — treat integrity failure as an operator signal, not necessarily a production outage.

See [RUNBOOK-UPGRADE.md](RUNBOOK-UPGRADE.md) for upgrade-specific context.

---

## 5. Backup Recommendations

- Regularly back up the entire `managed/` directory
- Include `managed/keys/` (contains verification keys)
- Store backups in a separate, secure location
- Test restore procedure periodically

```bash
python -m scripts.apxv_ctl backup-create
```

---

## 6. Logging & Alerting

- All critical events are written to `managed/audit/`
- Use structured JSON logs for integration with log aggregation tools
- Recommended alerts:
  - Sudden spike in capability denials
  - Governance rule violations
  - `/health` status `degraded` for more than N minutes
  - `apxv_ctl integrity` exit code non-zero

---

## 7. Scaling Considerations

- The current design is single-node friendly
- For higher scale, consider:
  - Shared storage for `managed/`
  - Centralized log aggregation
  - Multiple APXV instances with coordinated governance rules

---

*Last updated: 2026-07-02*