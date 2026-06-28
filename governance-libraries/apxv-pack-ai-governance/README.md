# AI Governance Pack

**Pack ID:** `apxv-pack-ai-governance`  
**Version:** 0.1.0  
**Requires:** APXV1 >= 1.2.0

## What this pack adds

Governed redaction plus LLM review:

1. Redact input with **APX-AGENT-001** (core redactor)
2. Run **APX-AGENT-LLM-001** (`LLMReasoner`) for governance review (simulated backend by default)
3. Orchestrate and attest with **compliance policy id 4** (AI governance / regulated metadata)

Agents ship in APXV1 core. This pack adds governance specs, pipeline logic (`agents/governance_agents.py`), demo fixtures, and acceptance tests.

## Prerequisites

- APXV1 v1.2+ with `setup_first_run` complete
- `python -m scripts.apx_doctor` → HEALTHY

## Quick demo

From APXV1 root:

```bash
python governance-libraries/apxv-pack-ai-governance/examples/run_pack_demo.py
```

Expected:

```
Pack demo complete: final_status=ATTESTED, llm_decision=REVIEW_REQUIRED, total_redactions=4, compliance_policy_id=4
```

Custom input file:

```bash
python governance-libraries/apxv-pack-ai-governance/examples/run_pack_demo.py governance-libraries/apxv-pack-ai-governance/examples/inputs/sample.txt
```

## Install (production)

Apply governance via propose → approve → apply for each spec in `governance/`. See `ACCEPTANCE.md`.

## Attestation note

The demo runs the governance attestation path (Agents 1–3 + LLM review metadata). For full Groth16 entity proofs including `compliance` with policy id 4, run `python -m scripts.run_apx --attest` after integrating pack output into your pipeline.

## BYO LLM

Pass your own `LLMBackend` to `run_governed_ai_pipeline(..., backend=your_backend)`. See `docs/BUILDING.md` and `examples/llm-ollama/`.