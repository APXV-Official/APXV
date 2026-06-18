# APXV1 — Phase 2 Security Review & Threat Model

**Status:** Phase 2 Completion Document (Updated)  
**Date:** 2026-06-17  
**Deployment:** Local, self-hosted, air-gapped compatible

---

## 1. Components Reviewed

- `agents/agent1.py`, `agent2.py`, `agent3.py` — deterministic pipeline agents
- `agents/store.py` — SQLite + content-addressable artifact store
- `agents/artifact_provider.py` — `SqliteArtifactProvider`
- `agents/runtime.py` — unified `APXRuntime`
- `agents/governance.py` — governance specification registry
- `agents/audit_logger.py` — cryptographically chained audit logs
- `agents/capability_checker.py` — persistent local capability policy
- `managed/config/capabilities.json` — air-gapped policy file

---

## 2. Security Strengths (Phase 2)

- Immutable artifact storage with SQLite index + CAS blobs
- Artifact hash chaining verified via `apx_ctl store-verify`
- Cryptographically chained audit logs (system + per-agent)
- Persistent capability policy on local disk (no in-memory-only grants in production path)
- Governance specification change tracking in SQLite
- Unified runtime with integrity check (`apx_ctl integrity`)
- No network dependencies — suitable for air-gapped deployment
- ZK proof layer (Phase 1) remains independently verifiable

---

## 3. Residual Limitations

| Area | Limitation | Phase |
|------|------------|-------|
| Capability policy | Local JSON file — not signed or HSM-protected | 3+ |
| Governance approval | Changes logged but no multi-party approval workflow | 3+ |
| Input validation | Basic regex redaction; no formal bounds checking | 3+ |
| Agent isolation | Same process — no container sandbox yet | 3 |
| Rate limiting | None | 4 |
| Centralized monitoring | CLI only — no automated alerting | 4 |

---

## 4. Threat Model (Air-Gapped Local Deployment)

### Assets
- Governance markdown (rules, workflows, knowledge)
- SQLite store + CAS blobs
- Audit logs and ZK proof artifacts
- Capability policy file
- Rust proving keys (`rust/keys/`)

### Threat Actors
- **Malicious local operator** — can edit capability policy or governance files
- **Compromised agent code** — bug or tampered Python module
- **Insider with filesystem access** — can attempt to tamper with logs or store

### Mitigations

| Threat | Mitigation |
|--------|------------|
| Artifact tampering | CAS blobs + hash chain; integrity verification |
| Audit log tampering | Cryptographic chaining; `audit-verify` |
| Unauthorized agent actions | Persistent capability policy + audit of all checks |
| Wrong VK / stale proofs | Phase 1 manifest VK integrity checks |
| Policy tampering | Ed25519-signed capability policy; file permissions (OS-level) |

---

## 5. Incident Response (Air-Gapped)

1. Run `python -m scripts.apx_ctl integrity`
2. If failed, run `store-verify` and `audit-verify` separately
3. Preserve `managed/` directory — do not delete or modify
4. Collect latest artifacts from `managed/store/blobs/`
5. Export audit logs from `managed/audit/`

---

## 6. Phase 2 Security Posture

**Acceptable for:** trusted internal environments, air-gapped labs, demonstration deployments with sensitive-but-non-regulated data.

**Not yet acceptable for:** multi-tenant SaaS, regulated production (HIPAA/PCI), internet-exposed deployments.

---

*Phase 2 security requirements addressed. See `PHASE2-STATUS.md` for exit criteria.*