# APXV Quickstart (15 Minutes)

**APXV** (*Attested Proof Execution Verified*) is an air-gapped governed agent platform. **v1.3** added sovereign local trust and a desktop operator console; **v1.3.3** completed Windows server lifecycle on `:8741`. **v1.4** adds the Pack Studio **authoring wizard**, **Build your pipeline** on-ramp, removes pre-v1.3 shims, and trims unused entity circuits from default keygen.

## Choose your path

| Path | Who | One command / action |
|------|-----|----------------------|
| **Desktop** | Individual operators | [Download MSI or Linux installer](INSTALL-USER.md) → bootstrap wizard |
| **Docker** | Teams, servers, no local Rust | `.\scripts\install-docker.ps1` or `./scripts/install-docker.sh` |
| **Native** | Contributors, power users | `.\scripts\install-full.ps1` or `./scripts/install-full.sh` |

All paths run the same sovereign contract: `apxv_bootstrap` → your ZK keys → `install.json` with `sovereign_setup: true`.

Legacy `install.ps1` / `install.sh` redirect to **install-full**. See [SOVEREIGN-SETUP.md](SOVEREIGN-SETUP.md) for the trust model.

### Expected finale

After bootstrap completes:

- `Pack demo complete: final_status=ATTESTED, total_redactions=4`
- `ALL GOVERNANCE + ENTITY GROTH16 PROOFS INDEPENDENTLY VERIFIED [OK]`

First native install may take **20–60 minutes** (Rust compile + 3 governance and 6 entity circuit setup). Docker build is slower once, then cached. Desktop wizard shows per-step progress.

Re-run demos without reinstalling: `python -m scripts.onboard --skip-setup`

**Command cheat sheet:**

| OS | Install | Demo / CLI |
|----|---------|------------|
| Linux / WSL | `./scripts/install-full.sh` then `source .venv/bin/activate` | `python3 -m scripts.apxv_demo --pack all` |
| Windows | `.\scripts\install-full.ps1` | `py -3 -m scripts.apxv_demo --pack all` |
| Docker (any) | `.\scripts\install-docker.ps1` or `./scripts/install-docker.sh` | `curl http://127.0.0.1:8741/health` |
| Desktop | Installer from [Releases](https://github.com/APXV-Official/APXV/releases) | Launch app → wizard |

On Linux/WSL, use `python3` (or activated `.venv`) if bare `python` is not on PATH.

**API key after onboard:** printed once in the terminal, or read `managed/config/OPERATOR-KEY-default-operator.txt`, or create with `python -m scripts.apxv_ctl api-key create my-key --save-hint`.

Polluted runtime state from prior experiments: `.\scripts\install-full.ps1 -Fresh` or `.\scripts\install-docker.ps1 -Fresh` (clears audit/config/store; keeps governance templates)

## 5-minute path (already bootstrapped)

If sovereign bootstrap is done, skip reinstall and run:

```bash
./scripts/apxv_demo.sh                    # reference pack (default)
./scripts/apxv_demo.sh --pack document    # Document Processing Pack
./scripts/apxv_demo.sh --pack ai          # AI Governance Pack (needs Ollama)
./scripts/apxv_demo.sh --pack all         # all packs, then attest + verify
```

Windows: `.\scripts\apxv_demo.ps1` (add `-Pack document` etc.)

The script prints the latest ZK attested artifact path when verification succeeds.

## Linux and WSL

**Recommended:** use the project virtualenv created by `install-full.sh` (`.venv/`).

```bash
./scripts/install-full.sh
source .venv/bin/activate
./scripts/apxv_demo.sh
```

**WSL / Ubuntu / Debian prerequisites** (before native install):

```bash
sudo apt update
sudo apt install -y build-essential python3-venv curl
```

- **build-essential** — Rust compiles `apxv-circuits` and `apxv-zk` during bootstrap.
- **python3-venv** — creates `.venv` when system pip is restricted (common on Ubuntu).

If `python3 -m venv` fails, install the version-specific package, e.g. `sudo apt install -y python3.12-venv`.

**Re-run onboarding** with a different pack:

```bash
python -m scripts.onboard --skip-setup --pack document
python -m scripts.onboard --skip-setup --pack all
```

## Manual install (step by step)

```bash
pip install -e ".[dev,voice]"
python -m scripts.apxv_bootstrap
```

Save any API keys or signing PEMs printed during setup.

Optional voice model: included in bootstrap step 7, or `python -m scripts.setup_voice` (~40 MB Vosk download).

Official packs: [Reference Redaction](../governance-libraries/apxv-pack-reference-redaction/), [Document Processing](../governance-libraries/apxv-pack-document-processing/), [AI Governance](../governance-libraries/apxv-pack-ai-governance/). Index: [governance-libraries/README.md](../governance-libraries/README.md). Custom agents: [BUILDING.md](BUILDING.md).

### Voice attest (production)

With Vosk installed via bootstrap:

```bash
python -m scripts.run_apxv --voice-transcript "Email me at user@example.com" --attest
python -m scripts.verify_attestation --real-zk
```

Simulated voice is **CI-only** (`APXV_PROFILE=ci`), not available in production operator paths.

### Ceremony transcript (optional)

After setup, commit VK lineage for releases:

```bash
python -m scripts.ceremony_transcript --write --tier B
python -m scripts.ceremony_transcript --verify
python -m scripts.export_verifier_bundle --out dist/apxv-verifier-bundle
```

Verifier VK **circuit semantics** are unchanged since v1.1.0 — your ceremony still produces **your** key files. See [cryptography/CEREMONY.md](cryptography/CEREMONY.md) and [cryptography/CIRCUITS.md](cryptography/CIRCUITS.md).

## Run the local API

```bash
python -m scripts.apxv_serve
```

Open `http://127.0.0.1:8741/health` (no auth required).

### API key

On first bootstrap or `apxv_serve`, the default key is printed once and written to:

`managed/config/OPERATOR-KEY-default-operator.txt`

If you missed it, create a new key (works immediately — no server restart required in v1.2.1+):

```bash
python -m scripts.apxv_ctl api-key create my-app --save-hint --description "Local development"
```

Set environment variable:

```bash
export APXV_API_KEY="<key-from-output-or-hint-file>"
```

## Operator UI

With bootstrap done and the API running:

```bash
# Terminal 1 — runtime
python -m scripts.apxv_serve

# Terminal 2 — UI (monorepo checkout)
cd ui && pnpm install && pnpm dev
```

Open http://localhost:5173 → paste operator API key. Or use the **desktop app** — [INSTALL-USER.md](INSTALL-USER.md).

Guide: [ui/docs/OPERATOR-GUIDE.md](../../ui/docs/OPERATOR-GUIDE.md)

## Try the examples

```bash
python examples/hello-agent/hello_agent.py "hello APXV"
APXV_API_KEY=<key> python examples/api-client/run_pipeline.py
```

## Build something

Read [BUILDING.md](BUILDING.md) for custom agents, company deployment, and optional LLMs.

## Docker (companies)

See [DOCKER.md](DOCKER.md). Use **fresh volumes** — do not mount a dev `managed/` folder.

## Troubleshooting

```bash
python -m scripts.apxv_doctor
```

Confirm `sovereign_setup: true` in doctor output and `managed/config/install.json`.

If `apxv_doctor` or `apxv_ctl integrity` fails after heavy local testing, read the per-log hint (v1.2.2+):

- **corrupt lines** (`corrupt_line_count` > 0) — back up `managed/`, remove affected files under `managed/audit/`, re-run bootstrap
- **chain break** (`corrupt_line_count` == 0, `chain_valid` false) — common on long-lived dev trees; remove `managed/audit/*.log` and re-run bootstrap, or `python -m scripts.fresh_reset` for a full local reset
- **vendor key guard** — remove copied pre-v1.3 keys and re-run `apxv_bootstrap` — [SOVEREIGN-SETUP.md](SOVEREIGN-SETUP.md)

Pipelines may still work while `/health` shows `degraded`. See [RUNBOOKS/RUNBOOK-UPGRADE.md](../RUNBOOKS/RUNBOOK-UPGRADE.md).

### Upgrading from v1.2.x

See [MIGRATION-v1.3.md](MIGRATION-v1.3.md). Re-run sovereign bootstrap if you used pre-v1.3 Docker images that shipped proving keys in the image.

**Docker:** if `docker compose up` fails with `container name "/apxv" is already in use` (or legacy `/apx-v1`), run `docker rm -f apxv apx-v1` then retry. `install-docker.ps1` and `install-docker.sh` do this automatically (v1.2.2+). See [DOCKER.md](DOCKER.md).

First `run_apxv --attest` after bootstrap can take 1–3 minutes while Rust warms up; `apxv_doctor` may show `apxv-circuits=no` until binaries are on PATH even when attest works.

See [SECURITY.md](../SECURITY.md) for what APXV does and does not protect.