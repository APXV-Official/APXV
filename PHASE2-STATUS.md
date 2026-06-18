# APX Phase 2 — Governed Core Hardening Status

**Goal:** Deterministic governed execution path trustworthy for real internal use.  
**Deployment model:** Local, self-hosted, air-gapped compatible  
**Last verified:** 2026-06-17

## Design Principles

- **No cloud dependencies** — stdlib sqlite3 + local files only
- **No external network** — all state on disk under `managed/`
- **Immutable artifacts** — content-addressable blobs + SQLite index
- **Cryptographic audit chains** — system + per-agent logs
- **Persistent local policy** — `managed/config/capabilities.json`

## Exit Criteria Checklist

- [x] **Production artifact store** — `SqliteArtifactStore` + CAS blobs in `managed/store/`
- [x] **Artifact chain verification** — `python -m scripts.apx_ctl store-verify`
- [x] **Audit logging** — chained logs + `python -m scripts.apx_ctl audit-verify`
- [x] **Persistent capabilities** — `managed/config/capabilities.json`
- [x] **Governance version tracking** — `GovernanceRegistry` in SQLite
- [x] **Unified runtime** — `APXRuntime` wires store, audit, capabilities, governance
- [x] **Pipeline uses production path** — `run_apx.py` uses `APXRuntime` + `SqliteArtifactProvider`
- [x] **Local control plane** — `python -m scripts.apx_ctl`
- [x] **Security review** — `docs/security/PHASE2-SECURITY-REVIEW.md`
- [x] **Tests** — `tests/test_phase2.py`

## Verification Commands

```bash
python -m scripts.apx_ctl integrity
python -m scripts.apx_ctl status
python -m scripts.run_apx --attest
python -m scripts.verify_attestation --real-zk
python -m pytest tests/ -v
```

## Key Paths

| Path | Purpose |
|------|---------|
| `managed/store/apx.db` | SQLite artifact index |
| `managed/store/blobs/` | Content-addressable artifact blobs |
| `managed/config/capabilities.json` | Persistent agent capabilities |
| `managed/config/runtime.json` | Local runtime settings |
| `managed/audit/system_audit.log` | Central system audit chain |

## Phase 2 Complete — Phase 3 Next

Phase 3 adds real LLM/tool agents under the same governance regime with sandboxing and output contracts.