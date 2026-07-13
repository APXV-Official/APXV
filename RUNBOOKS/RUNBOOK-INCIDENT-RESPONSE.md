# APXV — Runbook: Incident Response

**Purpose:** Guide for detecting, responding to, and recovering from incidents involving an APXV deployment.

---

## 1. Incident Categories

| Category | Examples | Severity |
|----------|----------|----------|
| **Tampering** | Audit log or artifact chain broken | High |
| **Access Violations** | Repeated capability denials, unauthorized attempts | Medium–High |
| **Governance Violations** | LLM agents bypassing or violating rules | Medium |
| **Operational Failures** | Service crashes, disk full, permission errors | Medium |
| **Key / Setup Issues** | Verification key corruption or loss | High |

---

## 2. Detection

### Automated Checks
- Run `AuditLogger.verify_chain()` on all audit logs
- Monitor for sudden spikes in failed capability checks
- Watch for governance rule enforcement events in LLM agents

### Manual Review
- Periodically review recent entries in `managed/audit/`
- Check for unexpected artifact writes

---

## 3. Response Steps

### Step 1: Contain
- Stop affected services if tampering or unauthorized access is suspected
- Preserve current state (do not delete logs or artifacts)

### Step 2: Investigate
- Run `python -m scripts.apxv_doctor` or `python -m scripts.apxv_ctl integrity` (v1.2.2+ reports `corrupt_lines` vs `chain_break` per log)
- Verify audit log integrity (`GET /health` or `AuditLogger.verify_chain()` on affected logs)
- Identify the scope (which artifacts, which agents, which time window)
- Collect relevant log entries and artifact metadata

### Step 3: Communicate
- Notify responsible parties in your organization
- Document findings clearly (what happened, when, and evidence)

### Step 4: Remediate
- Re-issue or rotate verification keys if setup is suspected compromised
- Update governance rules if agentic behavior is the issue
- Restart services once the issue is resolved

### Step 5: Recover
- Restore from known-good backup if data was lost or corrupted
- Re-verify artifact and audit log chains after recovery

---

## 4. Post-Incident Actions

- Update runbooks and detection rules based on lessons learned
- Review and strengthen capability grants if access was abused
- Consider adding new governance rules for future prevention

---

## 5. Escalation

- High-severity incidents (tampering, key compromise, repeated violations) should be escalated to the security/governance team immediately
- Maintain a clear chain of custody for any forensic artifacts

---

*Last updated: 2026-06-10*