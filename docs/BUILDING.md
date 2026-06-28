# Building On APXV1

**APXV** (*Attested Proof Execution Verified*) is an air-gapped governed agent platform: markdown rules, signed capabilities, chained audit, Groth16 proofs, local API — bring your own LLMs. **APXV1** is the first-generation open-source implementation. You bring your agents, rules, and (optionally) LLMs; APXV1 provides governance, audit, artifacts, and cryptographic attestation.

## Core Concepts

| Concept | What you use |
|---------|--------------|
| **Governance specs** | Markdown in `managed/rules/`, `workflows/`, `knowledge/` |
| **Agents** | Python classes wired through `APXRuntime` |
| **Capabilities** | Signed policy in `managed/config/capabilities.json` |
| **Artifacts** | Immutable outputs via `runtime.provider` |
| **Attestation** | `run_apx --attest` + Groth16 proofs (required) |

## Quick Integration Paths

### 1. Custom deterministic agent

See [examples/hello-agent/](../examples/hello-agent/).

```python
from agents.runtime import APXRuntime
from agents.agent_base import init_agent_context

runtime = APXRuntime()
ctx = init_agent_context("APX-AGENT-001", "MyAgent", "my_agent_audit.log", runtime=runtime)
# capability checks → process → provider.write_artifact() → audit_logger.log_event()
```

Add your agent ID to the capability policy:

```bash
python -m scripts.apx_ctl policy-sign --description "Added my agent"
```

### 2. Local API integration

See [examples/api-client/](../examples/api-client/).

Run `python -m scripts.apx_serve`, then call `/pipeline/run` from any app on the same machine.

### 3. Add an LLM (optional)

APXV1 ships **without** a bundled model. You plug one in:

1. Implement `LLMBackend` (see `agents/llm_backend.py`)
2. Pass it to `LLMReasoner(runtime=runtime, backend=your_backend)`
3. Grant `APX-AGENT-LLM-001` capabilities (included in default policy)

**Ollama example:** [examples/llm-ollama/](../examples/llm-ollama/)

```python
from agents.llm_backend import OllamaLLMBackend
from agents.llm_reasoner import LLMReasoner

agent = LLMReasoner(
    runtime=APXRuntime(),
    backend=OllamaLLMBackend(model="llama3.2"),
)
output = agent.execute({"prompt": "Your task here"})
```

LLM agents must return structured `AgenticOutput` — never raw ungoverned text as final output.

### 4. BYO ML redaction backend (optional)

APXV1 ships **pattern-based** redaction by default. You may register an external model or service as an optional backend — **no model is bundled**.

```python
from agents.audit_logger import AuditLogger
from agents.redaction import APXRedactionEngine

def my_model_backend(*, text: str, input_format: str) -> dict:
    # Your model returns redacted text + entities[] (same envelope as the engine)
    return {
        "redacted_text": "...",
        "entities": [{"type": "email", "value": "...", "start": 0, "category": "EMAIL"}],
        "total_redactions": 1,
    }

audit = AuditLogger(log_path="managed/audit/redaction_backend.log")
engine = APXRedactionEngine(audit_logger=audit)
backend_id = engine.register_backend("My Model", my_model_backend)
result = engine.apply(input_text, backend_id=backend_id)
```

- Audit event: `redaction_backend_invoked` (backend id, input hash, entity count — no raw PII in the log payload you pass).
- **ZK proofs bind the pattern engine path and `entities[]` you supply** — they do **not** prove your ML model was correct or fair. Document this for auditors.
- Omit `backend_id` to use the built-in deterministic engine (default for governance demos).

### 5. Agent packs and governance templates

**Official packs (v1.2.0):**

| Pack | Demo |
|------|------|
| [Reference Redaction](../governance-libraries/apxv-pack-reference-redaction/README.md) | `python governance-libraries/apxv-pack-reference-redaction/examples/run_pack_demo.py` |
| [Document Processing](../governance-libraries/apxv-pack-document-processing/README.md) | `python governance-libraries/apxv-pack-document-processing/examples/run_pack_demo.py` |
| [AI Governance](../governance-libraries/apxv-pack-ai-governance/README.md) | `python governance-libraries/apxv-pack-ai-governance/examples/run_pack_demo.py` |

Quick path (setup already done): `python -m scripts.apx_demo --pack document` (or `reference`, `ai`, `all`).

Install governance via propose → approve → apply per pack `governance/` specs; complete each pack's `ACCEPTANCE.md`.

**Governance templates** (e.g. `ai-governance-template/`) are markdown starters for custom rules — not full packs. For AI governance with agents and acceptance tests, use [apxv-pack-ai-governance](../governance-libraries/apxv-pack-ai-governance/README.md). To roll your own specs, copy a template into `managed/`, then apply via approval workflow:

```bash
python -m scripts.apx_ctl governance-propose --spec rule --file my-rule.md
python -m scripts.apx_ctl governance-approve --proposal-id <id>
python -m scripts.apx_ctl governance-apply --proposal-id <id>
```

## ZK Attestation (Required)

Cryptographic proofs are part of the APXV1 contract — not an optional extra.

```bash
python -m scripts.setup_first_run          # includes ZK setup
python -m scripts.run_apx --attest
python -m scripts.verify_attestation --real-zk
```

Third parties verify proofs without re-running your system. See [docs/cryptography/VERIFICATION.md](cryptography/VERIFICATION.md).

## Company / Team Deployment

1. Run `setup_first_run` on each instance
2. Mount persistent volumes for `managed/`, `rust/apx-circuits/keys/`, and `rust/apx-zk/keys/` (Docker)
3. Back up regularly: `python -m scripts.apx_ctl backup-create`
4. Restrict host filesystem access to APXV1 directories
5. Keep API on localhost unless you add your own network controls
6. Read [SECURITY.md](../SECURITY.md) — understand what APXV1 does and does not protect

## What You Build

Examples of systems on APXV1:

- Local PII processing service with audit trail + proofs
- Policy-governed document pipeline
- Compliance automation with signed rule changes
- Hybrid workflow: deterministic core + optional LLM reasoning step
- Attestation export for external auditors

## Extension Checklist

- [ ] Agent ID added to signed capability policy
- [ ] Agent uses `APXRuntime` (not direct file reads for specs)
- [ ] All outputs written as artifacts
- [ ] All actions audit-logged
- [ ] Governance changes go through approval workflow
- [ ] Pipeline attestation tested with `--attest`
- [ ] `verify_attestation --real-zk` passes