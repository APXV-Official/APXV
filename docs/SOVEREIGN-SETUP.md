# Sovereign setup — local trust model

**APXV v1.3+** requires every operator deployment to run its own **trusted setup** on local storage. Your instance generates unique proving keys; attestations are verifiable with **your** verification keys — not keys from the repo, Docker image, or vendor.

## What sovereign means

| Your deployment owns | APXV ships (auditable source) |
|----------------------|-------------------------------|
| Proving keys (`rust/apxv-circuits/keys/`, `rust/apxv-zk/keys/`) | Circuit source, prover binaries |
| `managed/` (store, audit, config, artifacts) | Governance pack templates |
| Operator API keys | Operator console + runtime code |
| `managed/config/install.json` provenance | Documentation and verifier bundle export |

Two APXV instances on different machines **must** have different `vk_hashes` in `install.json`. If hashes match a known pre-v1.3 vendor bundle, `apxv_doctor` fails with a migration warning.

## Bootstrap entry point

All operator paths call the same orchestrator:

```bash
python -m scripts.apxv_bootstrap
```

**Called automatically by:**

| Path | When |
|------|------|
| Desktop app (MSI, deb, AppImage) | First launch — bootstrap wizard |
| Docker | Entrypoint on empty volumes |
| Native / developer | `install-full.ps1` / `install-full.sh` |

### Bootstrap steps (summary)

1. Preflight (disk, ports, Python, prover binaries)
2. Build provers if missing (`cargo build --release`) — native/dev only
3. Governance ZK setup (3 circuits)
4. Entity ZK setup (8 circuits)
5. `setup_first_run` — policy, governance, operator key
6. Ollama (optional — AI Governance pack)
7. Vosk voice model (optional — voice workflows)
8. Write `managed/config/install.json`
9. Smoke: doctor → integrity → pipeline attest → verify

First run typically takes **20–60 minutes** (prover build, 11-circuit setup, optional model downloads). The desktop wizard and CLI show per-step progress.

### `install.json`

After bootstrap, check provenance:

```bash
python -m scripts.apxv_doctor
cat managed/config/install.json
```

Expect `"sovereign_setup": true`, `"profile": "production"`, and `vk_hashes` for all required circuits. The dashboard **System** page and `GET /api/v2/system/health` also expose `sovereign_setup`.

## Verify your keys

Confirm keys on disk match `install.json`:

```bash
python -m scripts.apxv_doctor
python -m scripts.apxv_ctl integrity
```

Run an end-to-end proof:

```bash
python -m scripts.run_apxv --attest
python -m scripts.verify_attestation --real-zk
```

Export verification keys only (safe to share for offline verify):

```bash
python -m scripts.export_verifier_bundle --out dist/apxv-verifier-bundle
```

Verifier key **bytes** are unchanged since v1.1.0 — but **your** setup ceremony produces **your** key files. To verify artifacts from your instance, use **your** exported bundle or the `.vk` files under `rust/*/keys/`.

See [cryptography/CEREMONY.md](cryptography/CEREMONY.md) and [cryptography/VERIFICATION.md](cryptography/VERIFICATION.md).

## Backup (required)

Without proving keys you cannot produce new attestations. Historical attestations remain verifiable only if you retain the verification keys used at attest time.

Back up regularly:

```text
managed/
rust/apxv-circuits/keys/
rust/apxv-zk/keys/
managed/config/install.json
```

```bash
python -m scripts.apxv_ctl backup-create
```

Desktop operators: data lives under `%LOCALAPPDATA%\APXV\` (Windows), `~/.local/share/APXV/` (Linux), or `~/Library/Application Support/APXV/` (macOS when available).

## Production profile

`APXV_PROFILE=production` is the default for all operator bootstrap paths:

- ZK setup **required** before attest
- AI Governance pack: **Ollama** + `llama3.2` (no simulated LLM)
- Voice workflows: **Vosk** (no simulated fallback)
- Missing integration → feature disabled with an explicit error

`APXV_PROFILE=ci` is for pytest/CI only — never used in Docker entrypoint, desktop bootstrap, or operator documentation.

## Optional integrations

Skip heavy downloads at bootstrap if needed:

```bash
python -m scripts.apxv_bootstrap --skip-ollama --skip-voice
```

Repair later from **Settings → Repair integrations** or `POST /api/v2/integrations/repair`.

## Migrating from pre-v1.3 installs

If you copied keys from an old Docker image or repo checkout, doctor will fail the vendor-key guard. Fix:

1. Back up `managed/` if you need historical artifacts
2. Remove old `rust/apxv-circuits/keys/` and `rust/apxv-zk/keys/`
3. Re-run `python -m scripts.apxv_bootstrap` (or desktop wizard / `install-docker` with fresh key volumes)

See [MIGRATION-v1.3.md](MIGRATION-v1.3.md).

## Related

| Doc | Purpose |
|-----|---------|
| [INSTALL-USER.md](INSTALL-USER.md) | Desktop MSI / Linux installers |
| [QUICKSTART.md](QUICKSTART.md) | All install paths |
| [DOCKER.md](DOCKER.md) | Team Docker deploy |
| [AIR-GAP-INSTALL.md](AIR-GAP-INSTALL.md) | Offline install |