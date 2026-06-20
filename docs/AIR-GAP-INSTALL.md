# Air-Gapped Installation Guide

APXV1 is designed to run fully offline after initial download.

## 1. Download (Online Machine)

On a machine with internet access:

```bash
git clone https://github.com/apxv1dev/APXV1.git
cd APXV1
pip download -d ./offline-wheels -e ".[dev]"
```

If building Rust/ZK locally, also install the Rust toolchain on the online machine and run:

```bash
cd rust && cargo build --release
```

Copy the entire `APXV1/` folder (including `offline-wheels/` and `rust/target/release/` if pre-built) to removable media.

## 2. Install (Offline Machine)

```bash
cd APXV1
pip install --no-index --find-links=./offline-wheels -e ".[dev]"
python -m scripts.setup_first_run
```

ZK circuit keys are generated during setup (requires Rust on offline machine). Use `--skip-zk` only for development without attestation.

## 3. Verify

```bash
python -m scripts.apx_ctl integrity
python -m scripts.apx_ctl status
```

Expected: `healthy: true` in status output.

## 4. Run

**API server (recommended for integrations):**

```bash
python -m scripts.apx_serve
```

Binds to `http://127.0.0.1:8741` only. No outbound network.

**One-shot pipeline:**

```bash
python -m scripts.run_apx --attest
python -m scripts.verify_attestation --real-zk
```

## 5. Backup

Back up regularly:

- `managed/` — artifacts, audit logs, config, store
- `rust/apx-circuits/keys/` and `rust/apx-zk/keys/` — ZK proving/verification keys

```bash
python -m scripts.apx_ctl backup-create
```

## 6. Update Safely

1. Create a backup before updating.
2. Replace code on the offline machine.
3. Re-run `python -m scripts.apx_ctl integrity`.
4. Re-run tests: `python -m pytest tests/ -v`.

Do not overwrite `managed/` or ZK key directories during updates unless restoring from backup.

## 7. Change Rules Safely

Do not edit `managed/rules/`, `workflows/`, or `knowledge/` directly in production.

Use the approval workflow:

```bash
python -m scripts.apx_ctl governance-propose --spec rule --file my-new-rule.md
python -m scripts.apx_ctl governance-approve --proposal-id <id>
python -m scripts.apx_ctl governance-apply --proposal-id <id>
```

## What Privacy Means Here

- Data stays on your machine
- No cloud dependency
- No built-in telemetry
- Governance changes are signed and auditable

See [SECURITY.md](../SECURITY.md) for limits and threat model.