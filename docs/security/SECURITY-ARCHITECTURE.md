# APXV1 — Security Architecture

**Version:** 1.0.1
**Deployment:** Local, self-hosted, air-gapped compatible

Supplements the operator-facing threat model in [SECURITY.md](../../SECURITY.md).

---

## Components Reviewed

- `agents/agent1.py`, `agent2.py`, `agent3.py` — deterministic pipeline agents
- `agents/redaction/` — APXRedactionEngine v3 (pattern redaction, format parsing)
- `agents/encryption_engine.py` — optional E2EE (`APXE2EE`)
- `agents/zk/` — dual-track ZK bridge (governance + entity proofs)
- `agents/store.py` — SQLite + content-addressable artifact store
- `agents/artifact_provider.py` — `SqliteArtifactProvider`
- `agents/runtime.py` — unified `APXRuntime`
- `agents/governance.py` — governance specification registry
- `agents/audit_logger.py` — cryptographically chained audit logs
- `agents/capability_checker.py` — persistent local capability policy
- `managed/config/capabilities.json` — air-gapped policy file

---

## Security Strengths

- Immutable artifact storage with SQLite index + CAS blobs
- Artifact hash chaining verified via `apx_ctl store-verify`
- Cryptographically chained audit logs (system + per-agent)
- Ed25519-signed capability policy on local disk
- Governance specification change tracking in SQLite
- Unified runtime with integrity check (`apx_ctl integrity`)
- No network dependencies — suitable for air-gapped deployment
- Dual-track Groth16 attestation independently verifiable via `verify_attestation --real-zk`
- Optional E2EE for pipeline payloads (`--encrypt`)

---

## Known Limitations

| Area | Limitation | Notes |
|------|------------|-------|
| Input validation | Pattern-based redaction | Not full DLP |
| Agent isolation | Same process | No container sandbox per agent |
| Rate limiting | None | Local API only |
| Centralized monitoring | CLI / JSON logs | Bring your own observability stack |
| E2EE scope | Pipeline payload only | Does not encrypt entire filesystem or store |

---

## Threat Model (Air-Gapped Local Deployment)

### Assets

- Governance markdown (rules, workflows, knowledge)
- SQLite store + CAS blobs
- Audit logs and ZK proof artifacts
- Capability policy and signing keys
- Rust proving keys (`rust/apx-circuits/keys/`, `rust/apx-zk/keys/`)
- Optional E2EE keypair (`managed/config/e2ee-keypair.json`)

### Threat Actors

- **Malicious local operator** — filesystem and key access
- **Compromised agent code** — bug or tampered Python module
- **Insider with filesystem access** — tampering with logs or store

### Mitigations

| Threat | Mitigation |
|--------|------------|
| Artifact tampering | CAS blobs + hash chain; integrity verification |
| Audit log tampering | Cryptographic chaining; `audit-verify` |
| Unauthorized agent actions | Signed capability policy + audit of all checks |
| Wrong VK / stale proofs | Separate VK manifests for governance and entity circuits |
| Policy tampering | Ed25519-signed capability policy; OS file permissions |

---

## Incident Response (Air-Gapped)

1. Run `python -m scripts.apx_ctl integrity`
2. If failed, run `store-verify` and `audit-verify` separately
3. Preserve `managed/` directory — do not delete or modify
4. Collect latest artifacts from `managed/store/blobs/`
5. Export audit logs from `managed/audit/`

See [RUNBOOKS/RUNBOOK-INCIDENT-RESPONSE.md](../../RUNBOOKS/RUNBOOK-INCIDENT-RESPONSE.md) for operator steps.

---

## Deployment Posture (v1.0.1)

**Appropriate for:** trusted internal environments, air-gapped labs, pilots with sensitive-but-non-regulated data.

**Not appropriate for:** multi-tenant SaaS, regulated production (HIPAA/PCI), internet-exposed deployments without additional controls.