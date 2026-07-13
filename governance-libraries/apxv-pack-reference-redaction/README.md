# Reference Redaction Pack

**Pack ID:** `apxv-pack-reference-redaction`  
**Version:** 0.1.0  
**Requires:** APXV >= 1.1.0

## What this pack adds

The official reference vertical for governed sensitive-text processing:

1. **RuleGovernedRedactor** (`APXV-AGENT-001`) — load rules and apply deterministic redaction
2. **WorkflowOrchestrator** (`APXV-AGENT-002`) — enforce APXV-WF-001 workflow steps
3. **AttestationCoordinator** (`APXV-AGENT-003`) — package results for audit and proof

Agents ship with **APXV core** (`agents/agent1.py` … `agent3.py`). This pack provides the **governance bundle**, install steps, demo, and acceptance checklist — not duplicate agent code.

## Prerequisites

- APXV installed and `python -m scripts.setup_first_run` completed
- `python -m scripts.apxv_doctor` reports HEALTHY

## Install

Run from your APXV instance root. Replace `PACK` with the path to this directory.

### 1. Apply governance (propose → approve → apply)

```bash
PACK=governance-libraries/apxv-pack-reference-redaction

python -m scripts.apxv_ctl governance-propose --spec rule --file $PACK/governance/rules/RULE-RED-001.md
python -m scripts.apxv_ctl governance-approve --proposal-id <rule-proposal-id>
python -m scripts.apxv_ctl governance-apply --proposal-id <rule-proposal-id>

python -m scripts.apxv_ctl governance-propose --spec workflow --file $PACK/governance/workflows/WORKFLOW-RED-001.md
python -m scripts.apxv_ctl governance-approve --proposal-id <workflow-proposal-id>
python -m scripts.apxv_ctl governance-apply --proposal-id <workflow-proposal-id>

python -m scripts.apxv_ctl governance-propose --spec knowledge --file $PACK/governance/knowledge/KB-RED-001.md
python -m scripts.apxv_ctl governance-approve --proposal-id <knowledge-proposal-id>
python -m scripts.apxv_ctl governance-apply --proposal-id <knowledge-proposal-id>
```

Active specs are written to `managed/rules/rule1.md`, `managed/workflows/workflow1.md`, and `managed/knowledge/knowledge1.md`.

### 2. Verify capabilities

```bash
python -m scripts.apxv_ctl policy-verify
python -m scripts.apxv_ctl capabilities
```

See `capabilities/CAPABILITIES.md` if your policy was customized.

### 3. Run acceptance

Complete [ACCEPTANCE.md](ACCEPTANCE.md).

## Agents

| ID | Type | Core module | Role |
|----|------|-------------|------|
| APXV-AGENT-001 | deterministic | `agents.agent1` | Rule-governed redaction |
| APXV-AGENT-002 | deterministic | `agents.agent2` | Workflow orchestration |
| APXV-AGENT-003 | deterministic | `agents.agent3` | Attestation coordination |

## Demo

```bash
python governance-libraries/apxv-pack-reference-redaction/examples/run_pack_demo.py
```

Expected: `final_status=ATTESTED`, `total_redactions=4`.

## Attestation

This pack's pipeline is fully deterministic. Full Groth16 attestation is supported:

```bash
python -m scripts.run_apxv --attest
python -m scripts.verify_attestation --real-zk
```

Proofs bind governance hashes and circuit inputs — not semantic correctness of free-text reasoning.