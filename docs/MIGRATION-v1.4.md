# Migrating from APXV v1.3.x to v1.4.0

v1.4.0 removes **legacy v1.3 compatibility shims** introduced during the APX → APXV rename. Canonical `apxv_*` CLI, `APXV_*` environment variables, and Tauri `*_apxv_server` commands are now the only supported operator surface.

Cryptography, circuit semantics, and pack directory layout are unchanged from v1.3.3 unless you also adopt v1.4 circuit-trim changes (see [MIGRATION notes in CHANGELOG](../CHANGELOG.md)).

## Breaking changes

### 1. CLI and pip entry points

| v1.3.x (removed) | v1.4.0 (use instead) |
|------------------|----------------------|
| `python -m scripts.run_apx` | `python -m scripts.run_apxv` |
| `python -m scripts.apx_serve` | `python -m scripts.apxv_serve` |
| `python -m scripts.apx_ctl` | `python -m scripts.apxv_ctl` |
| `python -m scripts.apx_doctor` | `python -m scripts.apxv_doctor` |
| `python -m scripts.apx_demo` | `python -m scripts.apxv_demo` |
| `python -m scripts.apx_verify_bundle` | `python -m scripts.apxv_verify_bundle` |
| `auditor/apx_verify.py` | `python -m scripts.apxv_verify_bundle` |
| Pip: `run-apx`, `apx-serve`, `apx-ctl`, … | Pip: `run-apxv`, `apxv-serve`, `apxv-ctl`, … |

Shim modules under `scripts/apx_*.py` and `scripts/run_apx.py` are **deleted** — they no longer warn and delegate.

### 2. Environment variables

Only `APXV_*` names are read. Legacy `APX_*` fallbacks are **removed**.

| Removed | Canonical |
|---------|-----------|
| `APX_API_KEY` | `APXV_API_KEY` |
| `APX_BASE_PATH` | `APXV_BASE_PATH` |
| `APX_CONTAINER_BIND` | `APXV_CONTAINER_BIND` |
| `APX_LLM_TIMEOUT_SECONDS` | `APXV_LLM_TIMEOUT_SECONDS` |
| `APX_VOICE_MODE` | `APXV_VOICE_MODE` |
| `APX_KEYS_DIR` | `APXV_KEYS_DIR` |
| `APX_DEV_WARNINGS` | `APXV_DEV_WARNINGS` |
| `APX_API_BASE` | `APXV_API_BASE` |
| `APX_CIRCUITS_BIN` | `APXV_CIRCUITS_BIN` |
| `APX_ZK_BIN` | `APXV_ZK_BIN` |

Update `.env`, systemd units, Docker compose overrides, and CI secrets before upgrading.

### 3. Desktop (Tauri) commands

Removed aliases:

- `start_apx_server` → `start_apxv_server`
- `stop_apx_server` → `stop_apxv_server`
- `get_apx_server_status` → `get_apxv_server_status`

The operator UI already calls `*_apxv_server`. Custom integrations or scripts invoking Tauri must use the `apxv` names.

### 4. Python / Rust internal aliases

Removed from v1.4:

- `APXLocalServer` (use `APXVLocalServer`)
- `resolve_apx_root`, `resolve_apx_*_binary`, `build_apx_*_command` in `scripts/rust_bins.py`

## Upgrade steps

1. **Backup** — `python -m scripts.apxv_ctl backup-create`
2. **Pull / install v1.4.0** — desktop installer or `pip install -e .` from the v1.4 tag
3. **Replace env vars** — grep your deployment for `APX_` and `apx_`; switch to `APXV_` / `apxv_`
4. **Replace scripts** — cron, runbooks, and CI that call `run_apx` or `apx_doctor`
5. **Verify**

```bash
python -m scripts.apxv_doctor
python -m scripts.apxv_ctl integrity
python -m scripts.apxv_demo --pack reference
python -m scripts.verify_attestation --real-zk <latest-artifact>
```

Confirm `managed/config/install.json` still shows `"sovereign_setup": true`.

## What does not change

- Historical attestation JSON with `APX-AGENT-*` IDs (verification accepts both prefixes)
- SQLite migration `managed/store/apx.db` → `apxv.db` on first open
- API v2 paths (`/api/v2/*`) — primary operator API since v1.3
- Sovereign ceremony outputs and `vk_hashes` for an unchanged install tree
- Pack ids `apxv-pack-*` and governance library layout

## Related

- [MIGRATION-v1.3.md](MIGRATION-v1.3.md) — v1.2.5 → v1.3 rename and sovereign bootstrap
- [SOVEREIGN-SETUP.md](SOVEREIGN-SETUP.md) — trust model and verify
- [RUNBOOKS/RUNBOOK-UPGRADE.md](../RUNBOOKS/RUNBOOK-UPGRADE.md) — production upgrade flow