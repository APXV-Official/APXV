# APXV1 v1.0.0 Migration Plan

**Status:** Active — Phase 0 complete; ready for Phase 1  
**Branch:** `apx-v1-migration` (local; push only when ready)  
**Canonical workspace:** `C:\APXV1`  
**Date:** June 2026

---

## Purpose

Convert legacy privacy technology (redaction, entity ZK proofs, encryption, voice later) into **native APXV1 modules** with:

- No legacy product naming in shipped code
- Apache 2.0 on all published files
- Python + Rust runtime only (no Node.js dependency)
- APXV1 governance spine unchanged

Legacy source folders stay **local and gitignored** — they are reference only during porting.

---

## What stays unchanged

| Subsystem | Location |
|-----------|----------|
| 3-agent pipeline | `agents/agent1.py`, `agent2.py`, `agent3.py` |
| Governance (propose → approve → apply) | `agents/governance*.py` |
| Signed capabilities | `agents/capability_*.py` |
| SQLite CAS + audit chains | `agents/store.py`, `audit_logger.py` |
| Local API + job queue | `agents/local_api.py` |
| 3 governance ZK circuits | `rust/` (`redaction`, `rule-binding`, `pipeline`) |
| Independent auditor | `auditor/` |

---

## Target architecture

```
Input
  → APX FormatParser + UnicodeArmor
  → APX RedactionEngine v3 (entities[])
  → Agent 1 → Agent 2 → Agent 3
  → [optional] APX E2EE encrypt payload
  → ZK Track A: governance proofs (3 existing circuits)
  → ZK Track B: entity proofs (new rust/apx-zk crate)
  → SqliteArtifactProvider + audit
```

---

## Naming rules

| Legacy | APXV1 |
|--------|-------|
| `*RedactEnhanced*` | `APXRedactionEngine` |
| `*E2EE*` class | `APXE2EE` |
| `peet-zk` / `peet_zk` | `apx-zk` / `apx_zk` |
| `PEET_*` env vars | `APX_*` |
| Layer IDs 1–14 | APX audit event types |

All new file headers: Apache 2.0, `apxv1dev`, © 2026.

---

## Phases

### Phase 0 — Prep & baseline

| Task | Status |
|------|--------|
| Gitignore legacy reference folders | ✅ Done |
| Create branch `apx-v1-migration` | ✅ Done (local only) |
| This plan document | ✅ Done |
| Baseline: 51 pytest green | ✅ See `docs/migration/BASELINE.md` |
| Fixtures dir `tests/fixtures/apx/` | ✅ Done |
| pytest ignores legacy reference dirs | ✅ Done (`pyproject.toml`) |

**Gate:** All existing tests pass. No ported code yet.

---

### Phase 1 — Redaction engine v3 (1–2 weeks)

**Source reference:** `PEET SDK v1.0.0/src/modules/redaction/` (gitignored)

**Destination:**

```
agents/redaction/
  __init__.py
  format_parser.py
  unicode_armor.py
  patterns.py
  engine.py              # APXRedactionEngine
agents/redaction_engine.py   # backward-compat wrapper
```

**Deliverables:**
- ~90 pattern redaction, format-aware (JSON/CSV/XML/YAML/text)
- Unicode armor, production guards (max length, timeout)
- `entities[]` output on every run
- Agent 1 wired to new engine

**Tests:** `tests/test_redaction_v3.py`, `test_format_parser.py`, `test_unicode_armor.py`  
**Gate:** Existing `test_redaction_engine.py` still passes + ≥50 new cases green.

---

### Phase 2 — Encryption module (3–5 days)

**Source reference:** `PEET SDK v1.0.0/src/modules/encryption/` (gitignored)

**Destination:** `agents/encryption_engine.py` (`APXE2EE`, PyNaCl)

**Deliverables:**
- X25519 + XSalsa20-Poly1305
- Keypair at `managed/config/e2ee-keypair.json` (gitignored)
- Optional `--encrypt` on `run_apx.py`

**Tests:** `tests/test_encryption_engine.py`  
**Gate:** Round-trip encrypt/decrypt + key persistence tests green.

---

### Phase 3 — Proof system crate (2–3 weeks)

**Source reference:** `peet-proof-system/` (gitignored)

**Destination:**

```
rust/
  Cargo.toml          # workspace
  apx-circuits/       # existing 3 governance circuits (moved)
  apx-zk/             # 8 entity circuits (ported + renamed)
```

**Deliverables:**
- 8 entity Groth16 circuits (Poseidon Merkle, redaction_v1, etc.)
- Separate key manifest for entity vs governance circuits
- `cargo test` green in both crates

**Gate:** Governance circuits unchanged; entity circuits prove + verify independently.

---

### Phase 4 — ZK orchestration bridge (1–2 weeks)

**Source reference:** `PEET SDK v1.0.0/src/modules/zk/` (gitignored)

**Destination:**

```
agents/zk/
  entity_commitment.py
  merkle_tree.py
  bundle.py
  bridge.py
```

**Deliverables:**
- Dual proof bundle in `AttestedResult`: `governance_proofs` + `entity_proofs`
- `run_apx.py --attest` runs both tracks
- `verify_attestation.py --real-zk` verifies both

**Tests:** `tests/test_zk_entity_bundle.py` + E2E pipeline  
**Gate:** Full redact → govern → dual attest → independent verify.

---

### Phase 5 — Voice module (v1.1, deferred)

**Destination:** `agents/voice/` with `APXSTTProvider` / `APXTTSProvider`

Not required for v1.0.0.

---

### Phase 6 — v1.0.0 release (1 week)

| Task |
|------|
| Version bump to `1.0.0` |
| Update README, SECURITY.md, PROJECT-OVERVIEW.md, site |
| Re-record demo video |
| CI: Rust workspace + extended pytest |
| `rg -i peet` → zero hits in tracked files |
| Tag `v1.0.0`, merge `apx-v1-migration` → `main`, push |

---

## What we do NOT port

| Component | Reason |
|-----------|--------|
| TypeScript pipeline engine | APXV1 uses Python agents |
| JWT IdentityModule | API keys + capabilities + governance |
| SecurityModule (threat scoring) | Out of scope |
| StorageModule (AES vault) | CAS + optional E2EE |
| Node.js runtime | Python + Rust only |

---

## Testing discipline

Every phase:

1. Port tests first
2. Port implementation until tests pass
3. Full regression (`python -m pytest`)
4. Manual E2E: `python -m scripts.run_apx --attest`
5. Verify: `python -m scripts.verify_attestation --real-zk`
6. Update this doc phase status
7. Only then start next phase

**Test targets:**

| Milestone | Python tests | Rust tests |
|-----------|--------------|------------|
| Baseline (Phase 0) | 51 | existing |
| After Phase 1 | ~100 | — |
| After Phase 2 | ~115 | — |
| After Phase 3 | ~115 | ~45 |
| After Phase 4 | ~135 | ~45 |

---

## Repo hygiene

- Legacy reference folders: **gitignored, never pushed**
- Only converted APX code in commits
- Migration branch: local until merge-ready
- Push `main` only when launching a release

---

## Open decisions (record answers here)

| # | Decision | Choice |
|---|----------|--------|
| 1 | Redaction placeholder style | Keep APXV1 `[REDACTED-EMAIL]` for rule compat |
| 2 | Encryption default | Opt-in (`--encrypt`) |
| 3 | Rust layout | Sibling crate `rust/apx-zk/` |
| 4 | v1.0.0 scope | Redaction + encryption + dual ZK; voice in v1.1 |

---

## Phase log

| Phase | Started | Completed | Notes |
|-------|---------|-----------|-------|
| 0 | 2026-06-20 | 2026-06-20 | Baseline + plan + branch |
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |
| 6 | | | |