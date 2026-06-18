# Demo Video Script (~2 minutes)

Record this after `install.ps1` / `install.sh` succeeds.

## 1. Intro (15s)

> APXV1 — Attested Proof Execution Verified, 1st generation — is a local platform for building governed agent systems. Rules stay in markdown, execution is audited, and Groth16 proofs show what policy was followed.

## 2. Install (20s)

Show terminal:

```bash
./scripts/install.sh
# or .\scripts\install.ps1
```

Cut to: `APXV1 install complete` + doctor HEALTHY.

## 3. Pipeline + proof (40s)

```bash
python -m scripts.run_apx --attest
python -m scripts.verify_attestation --real-zk
```

Highlight: `ALL THREE GROTH16 PROOFS INDEPENDENTLY VERIFIED`.

## 4. API + custom agent (30s)

```bash
python -m scripts.apx_serve
python examples/hello-agent/hello_agent.py "demo"
```

Optional: `apx_ctl api-key create demo` + api-client.

## 5. Build on it (15s)

> Clone it, bring your agents and optional local LLMs, run air-gapped. See BUILDING.md.

## Outro

Link: GitHub repo + `docs/QUICKSTART.md`