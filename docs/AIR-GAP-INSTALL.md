# Air-Gapped Installation Guide

APXV is designed to run fully offline after initial download. APXV v1.3+ requires **sovereign bootstrap** on the offline machine — your proving keys are generated locally, never copied from an online image.

## 1. Download (Online Machine)

On a machine with internet access:

```bash
git clone https://github.com/APXV-Official/APXV.git
cd APXV
pip download -d ./offline-wheels -e ".[dev]"
```

If building Rust/ZK locally, also install the Rust toolchain on the online machine and run:

```bash
cd rust && cargo build --release
```

Copy the entire `APXV/` folder (including `offline-wheels/` and `rust/target/release/` if pre-built) to removable media.

**Do not copy proving keys from another deployment** — each air-gapped site runs its own ceremony. See [SOVEREIGN-SETUP.md](SOVEREIGN-SETUP.md).

## 2. Install (Offline Machine)

```bash
cd APXV
pip install --no-index --find-links=./offline-wheels -e ".[dev]"
python -m scripts.apxv_bootstrap
```

ZK circuit keys are generated during sovereign bootstrap (requires Rust prover binaries on the offline machine). Bootstrap runs all 11 circuits and writes `managed/config/install.json`.

Skip optional integrations if bandwidth or time is limited:

```bash
python -m scripts.apxv_bootstrap --skip-ollama --skip-voice
```

## 3. Verify

```bash
python -m scripts.apxv_doctor
python -m scripts.apxv_ctl integrity
curl http://127.0.0.1:8741/health
```

Expected: `sovereign_setup: true` in doctor and `install.json`. On upgraded or reused `managed/` trees, v1.2.2+ may report `degraded` with `integrity.audit_summary` (`corrupt_lines` vs `chain_break`) while core paths still run — see [RUNBOOKS/RUNBOOK-UPGRADE.md](../RUNBOOKS/RUNBOOK-UPGRADE.md).

## 4. Run

**API server (recommended for integrations):**

```bash
python -m scripts.apxv_serve
```

Binds to `http://127.0.0.1:8741` only. No outbound network.

**One-shot pipeline:**

```bash
python -m scripts.run_apxv --attest
python -m scripts.verify_attestation --real-zk
```

## 5. Backup

Back up regularly:

- `managed/` — artifacts, audit logs, config, store
- `rust/apxv-circuits/keys/` and `rust/apxv-zk/keys/` — ZK proving/verification keys
- `managed/config/install.json` — sovereign provenance

```bash
python -m scripts.apxv_ctl backup-create
```

## 6. Update Safely

1. Create a backup before updating.
2. Replace code on the offline machine.
3. Re-run `python -m scripts.apxv_doctor`.
4. Re-run tests: `python -m pytest tests/ -v`.

Do not overwrite `managed/` or ZK key directories during updates unless restoring from backup.

## 7. Change Rules Safely

Do not edit `managed/rules/`, `workflows/`, or `knowledge/` directly in production.

Use the approval workflow:

```bash
python -m scripts.apxv_ctl governance-propose --spec rule --file my-new-rule.md
python -m scripts.apxv_ctl governance-approve --proposal-id <id>
python -m scripts.apxv_ctl governance-apply --proposal-id <id>
```

## What Privacy Means Here

- Data stays on your machine
- No cloud dependency
- No built-in telemetry
- Governance changes are signed and auditable
- Cryptographic trust is **local** — your keys, your proofs

See [SECURITY.md](../SECURITY.md) for limits and threat model.