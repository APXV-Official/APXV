# APXV1 Quickstart (15 Minutes)

*Attested Proof Execution Verified* — 1st-generation platform. Get from zero to a verified governed pipeline.

## Prerequisites

- Python 3.9+
- Rust toolchain ([install guide](INSTALL-RUST.md))

## Install (one command)

**Windows (PowerShell):**

```powershell
.\scripts\install.ps1
```

**macOS / Linux:**

```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

**Manual path:**

```bash
pip install -e ".[dev]"
python -m scripts.setup_first_run
python -m scripts.apx_doctor
```

Save any API keys or signing PEMs printed during setup.

Optional voice extras (local STT/TTS or CI-simulated mode):

```bash
pip install -e ".[dev,voice]"
python -m scripts.setup_voice    # downloads Vosk model (~40 MB) for local STT
```

## Verify

```bash
python -m scripts.apx_ctl integrity
python -m scripts.run_apx --attest
python -m scripts.verify_attestation --real-zk
```

Expected: `HEALTHY`, `ATTESTED`, `Entity proofs: VALID`, and `ALL GOVERNANCE + ENTITY GROTH16 PROOFS INDEPENDENTLY VERIFIED [OK]`.

### Voice attest (v1.1)

```bash
# Simulated STT (no model) — same as CI
APX_VOICE_MODE=simulated python -m scripts.run_apx \
  --voice-transcript "Email me at user@example.com" --attest
python -m scripts.verify_attestation --real-zk
```

### Ceremony transcript (v1.1, optional)

After setup, commit VK lineage for releases:

```bash
python -m scripts.ceremony_transcript --write --tier B
python -m scripts.ceremony_transcript --verify
python -m scripts.export_verifier_bundle --out dist/apxv1-verifier-bundle
```

See [cryptography/CEREMONY.md](cryptography/CEREMONY.md) and [cryptography/CIRCUITS.md](cryptography/CIRCUITS.md).

## Run the local API

```bash
python -m scripts.apx_serve
```

Open `http://127.0.0.1:8741/health` (no auth required).

### API key

If you missed the key on first start:

```bash
python -m scripts.apx_ctl api-key create my-app --description "Local development"
```

Set environment variable:

```bash
export APX_API_KEY="<key-from-output>"
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

First `run_apx --attest` can take 1–3 minutes while Rust compiles; `apx_doctor` may show `apx-circuits=no` until binaries are on PATH even when attest works.

See [SECURITY.md](../SECURITY.md) for what APXV1 does and does not protect.