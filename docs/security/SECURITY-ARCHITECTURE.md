# APXV — Security Architecture

**Version:** 1.1.0
**Deployment:** Local, self-hosted, air-gapped compatible

Supplements the threat model in [SECURITY.md](../../SECURITY.md).

---

## Components Reviewed

- `agents/agent1.py`, `agent2.py`, `agent3.py` — deterministic pipeline agents
- `agents/redaction/` — APXRedactionEngine v3 (pattern redaction, format parsing)
- `agents/encryption_engine.py` — optional E2EE (`APXE2EE`)
- `agents/zk/` — dual-track ZK bridge (governance + entity proofs on attest path)
- `agents/voice/` — voice privacy pipeline (STT/TTS, `voice-redaction` inputs)
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
- Artifact hash chaining verified via `apxv_ctl store-verify`
- Cryptographically chained audit logs (system + per-agent)
- Ed25519-signed capability policy on local disk
- Governance specification change tracking in SQLite
- Unified runtime with integrity check (`apxv_ctl integrity`)
- No network dependencies — suitable for air-gapped deployment
- Dual-track Groth16 attestation independently verifiable via `verify_attestation --real-zk`
- Tier A/B ceremony transcript + exportable verifier bundle (VK lineage; signature when signing keys exist)
- Voice path with simulated (CI) or local offline STT/TTS backends
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
- Rust proving keys on the deployment host (`rust/apxv-circuits/keys/`, `rust/apxv-zk/keys/` — reference keys ship in-repo; re-run setup for production isolation)
- Optional E2EE keypair (`managed/config/e2ee-keypair.json`)

### Threat Actors

- **Malicious local user** — filesystem and key access
- **Compromised agent code** — bug or tampered Python module
- **Insider with filesystem access** — tampering with logs or store

### Mitigations

| Threat | Mitigation |
|--------|------------|
| Artifact tampering | CAS blobs + hash chain; integrity verification |
| Audit log tampering | Cryptographic chaining; `audit-verify` |
| Unauthorized agent actions | Signed capability policy + audit of all checks |
| Wrong VK / stale proofs | Separate VK manifests; ceremony transcript drift detection |
| Setup trust (single-party) | Documented in CEREMONY.md — self-host vs verify-release |
| Policy tampering | Ed25519-signed capability policy; OS file permissions |

---

## Incident Response (Air-Gapped)

1. Run `python -m scripts.apxv_ctl integrity`
2. If failed, run `store-verify` and `audit-verify` separately
3. Preserve `managed/` directory — do not delete or modify
4. Collect latest artifacts from `managed/store/blobs/`
5. Export audit logs from `managed/audit/`

See [RUNBOOKS/RUNBOOK-INCIDENT-RESPONSE.md](../../RUNBOOKS/RUNBOOK-INCIDENT-RESPONSE.md) for incident response steps.

---

## Voice data flow (v1.1)

- Audio or transcript enters `VoicePrivacyPipeline` locally (Vosk, pyttsx3, or simulated providers).
- Redaction uses the same `APXRedactionEngine` as the text pipeline.
- Attested artifacts may include `voice_session` (transcript hash, entities for ZK, `voice_redaction_inputs`).
- Raw audio is not embedded in Groth16 public inputs; treat artifacts as sensitive if entities/transcripts are present.

## ZK circuit scope (v1.1)

Eight entity circuits exist in `apxv-zk`; the default `--attest` path proves a subset (see [../cryptography/CIRCUITS.md](../cryptography/CIRCUITS.md)). `merkle-inclusion` and `compliance` are wired from v1.2.0; `normalization` and `threat` remain future modules.

---

## Deployment Posture (v1.1.0)

**Appropriate for:** self-hosted deployments, air-gapped labs, pilots with sensitive-but-non-regulated data.

**Not appropriate for:** multi-tenant SaaS, regulated production (HIPAA/PCI), internet-exposed deployments without additional controls.