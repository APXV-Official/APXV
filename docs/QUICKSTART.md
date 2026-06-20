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

## Verify

```bash
python -m scripts.apx_ctl integrity
python -m scripts.run_apx --attest
python -m scripts.verify_attestation --real-zk
```

Expected: `HEALTHY`, `ATTESTED`, `Entity proofs: VALID`, and `ALL GOVERNANCE + ENTITY GROTH16 PROOFS INDEPENDENTLY VERIFIED [OK]`.

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

See [SECURITY.md](../SECURITY.md) for what APXV1 does and does not protect.