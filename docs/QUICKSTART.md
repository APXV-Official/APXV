# APXV1 Quickstart (15 Minutes)

**APXV** is the platform; **APXV1** is this open-source implementation. **v1.2.1** is the current release (stability patch on v1.2.0): one-command onboarding, three official agent packs, and `merkle-inclusion` / `compliance` on the default attest path.

## One command

Pick the path that matches your machine:

| Path | Prerequisites | Command |
|------|---------------|---------|
| **Native** | Python 3.9+, Rust ([install guide](INSTALL-RUST.md)) | `.\scripts\install.ps1` or `./scripts/install.sh` |
| **Docker** | Docker + Compose only | `.\scripts\install-docker.ps1` or `./scripts/install-docker.sh` |

Both run the same onboarding: `setup` → doctor → integrity → **pack demo** → `run_apx --attest` → `verify_attestation --real-zk`.

Expected finale:

- `Pack demo complete: final_status=ATTESTED, total_redactions=4`
- `ALL GOVERNANCE + ENTITY GROTH16 PROOFS INDEPENDENTLY VERIFIED [OK]`

First native install may take a few minutes while Rust compiles. Docker build is slower once, then cached.

Re-run without reinstalling: `python -m scripts.onboard --skip-setup`

**Linux / WSL:** use `python3` (or activate `.venv/bin/activate` first) if `python` is not on PATH.

**API key after onboard:** printed once in the terminal, or read `managed/config/OPERATOR-KEY-default-operator.txt`, or create with `python -m scripts.apx_ctl api-key create my-key --save-hint`.

Polluted runtime state from prior experiments: `.\scripts\install.ps1 -Fresh` or `.\scripts\install-docker.ps1 -Fresh` (clears audit/config/store; keeps governance templates)

## 5-minute path (already installed)

If `setup_first_run` is done, skip reinstall and run:

```bash
./scripts/apx_demo.sh                    # reference pack (default)
./scripts/apx_demo.sh --pack document    # Document Processing Pack
./scripts/apx_demo.sh --pack ai          # AI Governance Pack
./scripts/apx_demo.sh --pack all         # all packs, then attest + verify
```

Windows: `.\scripts\apx_demo.ps1` (add `-Pack document` etc.)

The script prints the latest ZK attested artifact path when verification succeeds.

## Linux and WSL

**Recommended:** use the project virtualenv created by `install.sh` (`.venv/`).

```bash
./scripts/install.sh
source .venv/bin/activate
./scripts/apx_demo.sh
```

**WSL / Ubuntu / Debian prerequisites** (before native install):

```bash
sudo apt update
sudo apt install -y build-essential python3-venv curl
```

- **build-essential** — Rust compiles `apx-circuits` and `apx-zk` on first attest (1–3 minutes).
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
python -m scripts.onboard
```

Save any API keys or signing PEMs printed during setup.

Optional voice model: `python -m scripts.setup_voice` (~40 MB Vosk download).

Official packs: [Reference Redaction](../governance-libraries/apxv-pack-reference-redaction/), [Document Processing](../governance-libraries/apxv-pack-document-processing/), [AI Governance](../governance-libraries/apxv-pack-ai-governance/). Index: [governance-libraries/README.md](../governance-libraries/README.md). Custom agents: [BUILDING.md](BUILDING.md).

### Voice attest (platform)

```bash
# Simulated STT (no model) — same as CI
APX_VOICE_MODE=simulated python -m scripts.run_apx \
  --voice-transcript "Email me at user@example.com" --attest
python -m scripts.verify_attestation --real-zk
```

### Ceremony transcript (optional)

After setup, commit VK lineage for releases:

```bash
python -m scripts.ceremony_transcript --write --tier B
python -m scripts.ceremony_transcript --verify
python -m scripts.export_verifier_bundle --out dist/apxv1-verifier-bundle
```

Verifier VKs are unchanged since v1.1.0 — download from [GitHub Releases](https://github.com/APXV-Official/APXV/releases) or export your own. See [cryptography/CEREMONY.md](cryptography/CEREMONY.md) and [cryptography/CIRCUITS.md](cryptography/CIRCUITS.md).

## Run the local API

```bash
python -m scripts.apx_serve
```

Open `http://127.0.0.1:8741/health` (no auth required).

### API key

On first `setup_first_run` or `apx_serve`, the default key is printed once and written to:

`managed/config/OPERATOR-KEY-default-operator.txt`

If you missed it, create a new key (works immediately — no server restart required in v1.2.1+):

```bash
python -m scripts.apx_ctl api-key create my-app --save-hint --description "Local development"
```

Set environment variable:

```bash
export APX_API_KEY="<key-from-output-or-hint-file>"
```

## Try the examples

```bash
python examples/hello-agent/hello_agent.py "hello APXV1"
APX_API_KEY=<key> python examples/api-client/run_pipeline.py
```

## Build something

Read [BUILDING.md](BUILDING.md) for custom agents, company deployment, and optional LLMs.

## Docker (companies)

See [DOCKER.md](DOCKER.md). Use **fresh volumes** — do not mount a dev `managed/` folder.

## Troubleshooting

```bash
python -m scripts.apx_doctor
```

If `apx_doctor` or `apx_ctl integrity` fails after heavy local testing (broken audit chain), use a **fresh** instance: re-run `python -m scripts.setup_first_run` on a clean tree, or remove `managed/audit/` and run setup again — do not hand-edit audit logs.

**Docker:** if `docker compose up` fails with `container name "/apx-v1" is already in use`, run `docker rm -f apx-v1` then retry. See [DOCKER.md](DOCKER.md).

First `run_apx --attest` can take 1–3 minutes while Rust compiles; `apx_doctor` may show `apx-circuits=no` until binaries are on PATH even when attest works.

See [SECURITY.md](../SECURITY.md) for what APXV1 does and does not protect.