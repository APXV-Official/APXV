# APXV1 Quickstart (15 Minutes)

**APXV** is the platform; **APXV1** is this open-source implementation. **v1.1.1** ships the runtime plus the [Reference Redaction Pack](../governance-libraries/apxv-pack-reference-redaction/) — start here to prove both work on your machine.

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

## Verify the platform

```bash
python -m scripts.apx_ctl integrity
python -m scripts.run_apx --attest
python -m scripts.verify_attestation --real-zk
```

Expected: `HEALTHY`, `ATTESTED`, `Entity proofs: VALID`, and `ALL GOVERNANCE + ENTITY GROTH16 PROOFS INDEPENDENTLY VERIFIED [OK]`.

## Try the Reference Redaction Pack (v1.1.1)

Official agent pack — governance rules, workflow, knowledge, and a runnable demo on the core 3-agent pipeline:

```bash
python governance-libraries/apxv-pack-reference-redaction/examples/run_pack_demo.py
```

Expected: `final_status=ATTESTED` with redactions applied. See the pack's [ACCEPTANCE.md](../governance-libraries/apxv-pack-reference-redaction/ACCEPTANCE.md) for criteria.

More packs and templates: [governance-libraries/README.md](../governance-libraries/README.md). Custom agents: [BUILDING.md](BUILDING.md).

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

Verifier VKs are unchanged since v1.1.0 — download from [v1.1.1 release assets](https://github.com/APXV-Official/APXV/releases/tag/v1.1.1) or export your own. See [cryptography/CEREMONY.md](cryptography/CEREMONY.md) and [cryptography/CIRCUITS.md](cryptography/CIRCUITS.md).

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