# Migrating from APXV v1.2.5 to v1.3.0

v1.3.0 is a **platform rename**, **sovereign local trust**, and new operator features (API v2, Pack Studio, desktop app). Cryptography circuit semantics are unchanged — verifier VK **bytes** for a given ceremony are the same since v1.1.0, but **each deployment must run its own ceremony**.

## Sovereign trust (breaking change)

| v1.2.5 and earlier | v1.3.0 |
|--------------------|--------|
| Docker image could include proving keys at build time | Image ships **binaries only** — keys on mounted volumes |
| `setup_first_run` could run without fresh ZK on some paths | **`apxv_bootstrap` required** — 11-circuit sovereign setup |
| Simulated LLM/voice in default paths | **Production profile** — Ollama/Vosk or explicit disable |
| No `install.json` provenance | `managed/config/install.json` with `vk_hashes`, `sovereign_setup` |

### If you copied keys from an old image or repo

`apxv_doctor` fails the vendor-key migration guard. Fix:

1. `python -m scripts.apxv_ctl backup-create`
2. Remove `rust/apxv-circuits/keys/` and `rust/apxv-zk/keys/` (or use fresh Docker key volumes)
3. Re-run `python -m scripts.apxv_bootstrap` (or desktop wizard / `install-docker` with empty key mounts)

Two hosts after sovereign bootstrap must show **different** `vk_hashes`. See [SOVEREIGN-SETUP.md](SOVEREIGN-SETUP.md).

## Rename summary

| Area | v1.2.5 | v1.3.0 (canonical) | v1.3.0 compat (until v1.4) |
|------|--------|-------------------|---------------------------|
| Pip package | `apx-v1` | `apxv` | `apx-v1` shim not published — use `pip install -e .` |
| Docker image/service | `apx-v1` | `apxv` | Install scripts remove both container names |
| API server | `python -m scripts.apx_serve` | `python -m scripts.apxv_serve` | `apx_serve` warns + delegates |
| CLI | `apx_ctl`, `apx_doctor`, `apx_demo` | `apxv_ctl`, `apxv_doctor`, `apxv_demo` | `apx_*` warns + delegates |
| Pipeline CLI | `run_apx` | `run_apxv` | `run_apx` warns + delegates |
| API key env | `APX_API_KEY` | `APXV_API_KEY` | Both read; legacy warns once |
| API key header | `X-APX-API-Key` | `APXV-API-KEY` | Both accepted |
| Base path env | `APX_BASE_PATH` | `APXV_BASE_PATH` | Both read |
| Rust crates/bins | `apx-circuits`, `apx-zk` | `apxv-circuits`, `apxv-zk` | `rust_bins.py` legacy fallback |
| SQLite store | `managed/store/apx.db` | `managed/store/apxv.db` | Opens `apx.db` if `apxv.db` missing |
| Agent IDs (new artifacts) | `APX-AGENT-*` | `APXV-AGENT-*` | Dual-prefix lookup/display |
| Governance spec IDs (seeds) | `APX-RULE-*`, etc. | `APXV-RULE-*`, etc. | Old attestation JSON unchanged |
| Verifier bundle name | `apxv1-verifier-bundle` | `apxv-verifier-bundle` | Same VK files inside |
| HTTP API v1 | `/health`, `/pipeline/run`, … | Still available | `Deprecation: true`, `Sunset: v1.4` |
| HTTP API v2 | — | `/api/v2/*` | Primary for operator UI |
| Install scripts | `install.ps1` / `install.sh` | `install-full.*` (sovereign) | Legacy scripts redirect |

## Upgrade steps

### 1. Backup

```bash
python -m scripts.apxv_ctl backup-create
```

Back up the entire `managed/` directory and ZK key directories before upgrading.

### 2. Pull v1.3.0 and reinstall

**Native / developer:**

```bash
pip install -e ".[dev,voice]" --upgrade
./scripts/install-full.sh    # or .\scripts\install-full.ps1
```

**Docker:**

```bash
docker compose down
.\scripts\install-docker.ps1   # or ./scripts/install-docker.sh
```

Container name is now **`apxv`** (was `apx-v1`). Keys generate on host volumes on first start.

**Desktop:** download the latest MSI or Linux installer — [INSTALL-USER.md](INSTALL-USER.md) · [releases/latest](https://github.com/APXV-Official/APXV/releases/latest).

### 3. Environment variables

Prefer canonical names in scripts and `.env` files:

```bash
export APXV_API_KEY="<your-key>"
export APXV_BASE_PATH="/path/to/runtime"
```

`APX_*` variables still work through v1.3.x. **Removed in v1.4.0** — see [MIGRATION-v1.4.md](MIGRATION-v1.4.md).

### 4. Agent and governance IDs

**Existing attestation artifacts** under `managed/store/blobs/` keep their original `APX-AGENT-*` IDs. Verification and audit display accept both prefixes.

**New installs** seed `APXV-AGENT-*` keys in `capabilities.json`. After upgrade on an existing tree:

1. Re-run `python -m scripts.apxv_bootstrap` (or refresh policy manually).
2. Re-sign `managed/config/capabilities.json` if agent keys changed.
3. Optionally run pack activation to sync governance spec IDs to `APXV-*`.

Historical audit logs and blob JSON are **not** bulk-rewritten.

### 5. API clients

| If you use… | Action |
|-------------|--------|
| Legacy v1 paths (`/pipeline/run`, `/jobs`, …) | Plan migration to `/api/v2/*` before v1.4 |
| Operator UI | No change — already on v2 |
| `examples/api-client/run_pipeline.py` | Set `APXV_API_KEY`; consider v2 `/api/v2/pipeline/run` |

See [LOCAL-API-V2.md](LOCAL-API-V2.md) (primary) and [LOCAL-API-V1.md](LOCAL-API-V1.md) (deprecated).

### 6. Verify

```bash
python -m scripts.apxv_doctor
python -m scripts.apxv_ctl integrity
python -m scripts.apxv_demo --pack reference
python -m scripts.verify_attestation --real-zk <latest-artifact>
```

Confirm `managed/config/install.json` shows `"sovereign_setup": true`.

## What does not change

- GitHub repository URL: `APXV-Official/APXV`
- ZK verification key bytes and circuit semantics (D4) for a given ceremony
- Pack directory prefix `apxv-pack-*`
- Historical files in `managed/store/blobs/`, `managed/audit/*.log`
- Private operator workspace folder names (e.g. local `APXV Production\APXV`) — not part of the public repo layout

## Removed in v1.4.0

See [MIGRATION-v1.4.md](MIGRATION-v1.4.md) for the full upgrade guide.

- CLI/env shims: `apx_*`, `APX_*`
- Tauri command aliases `start_apx_server`, etc.
- Pip entry points `run-apx`, `apx-serve`, …

## Related

- [SOVEREIGN-SETUP.md](SOVEREIGN-SETUP.md) — trust model, backup, verify
- [INSTALL-USER.md](INSTALL-USER.md) — desktop installers
- [RUNBOOKS/RUNBOOK-UPGRADE.md](../RUNBOOKS/RUNBOOK-UPGRADE.md)
