# Document Processing Pack

**Pack ID:** `apxv-pack-document-processing`  
**Version:** 0.1.0  
**Requires:** APXV >= 1.2.0

## What this pack adds

Batch ingestion of `.txt` and `.json` documents:

1. Discover files in a folder
2. Redact each file with **APXV-AGENT-001** (core redactor)
3. Build a **batch manifest** with per-file hashes and counts
4. Orchestrate and attest with **compliance policy id 2**

Agents ship in APXV core. This pack adds governance, batch logic (`agents/document_agents.py`), demo fixtures, and acceptance tests.

## Prerequisites

- APXV v1.2+ with `setup_first_run` complete
- `python -m scripts.apxv_doctor` → HEALTHY

## Quick demo

From APXV root:

```bash
python governance-libraries/apxv-pack-document-processing/examples/run_pack_demo.py
```

Expected:

```
Pack demo complete: final_status=ATTESTED, file_count=2, total_redactions=4, compliance_policy_id=2
```

Custom batch folder (all supported `.txt` / `.json` files in the directory are processed):

```bash
python governance-libraries/apxv-pack-document-processing/examples/run_pack_demo.py /path/to/batch
```

The **default** demo path uses only `invoice.txt` and `customer.json` — extra files in `examples/inputs/batch/` are ignored so local experiments do not break `apxv_demo --pack document`.

## Install (production)

Apply governance via propose → approve → apply for each spec in `governance/`. See `ACCEPTANCE.md`.

## Attestation note

The demo runs the governance attestation path (Agent 3). For full Groth16 entity proofs including `compliance` with policy id 2, run `python -m scripts.run_apxv --attest` after integrating batch output into your pipeline or extend the demo with `--attest` in your deployment.