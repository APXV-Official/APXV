# Building On APX

APX is a **local platform** for devs and companies to build governed agent systems. You bring your agents, rules, and (optionally) LLMs. APX provides governance, audit, artifacts, and cryptographic attestation.

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

APX ships **without** a bundled model. You plug one in:

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

### 4. Custom governance packs

Copy templates from `governance-libraries/` into `managed/`, then apply via approval workflow:

```bash
python -m scripts.apx_ctl governance-propose --spec rule --file my-rule.md
python -m scripts.apx_ctl governance-approve --proposal-id <id>
python -m scripts.apx_ctl governance-apply --proposal-id <id>
```

## ZK Attestation (Required)

Cryptographic proofs are part of the APX contract — not an optional extra.

```bash
python -m scripts.setup_first_run          # includes ZK setup
python -m scripts.run_apx --attest
python -m scripts.verify_attestation --real-zk
```

Third parties verify proofs without re-running your system. See [docs/cryptography/VERIFICATION.md](cryptography/VERIFICATION.md).

## Company / Team Deployment

1. Run `setup_first_run` on each instance
2. Mount persistent volumes for `managed/` and `rust/keys/` (Docker)
3. Back up regularly: `python -m scripts.apx_ctl backup-create`
4. Restrict host filesystem access to APX directories
5. Keep API on localhost unless you add your own network controls
6. Read [SECURITY.md](../SECURITY.md) — understand what APX does and does not protect

## What You Build

Examples of systems on APX:

- Local PII processing service with audit trail + proofs
- Policy-governed document pipeline
- Internal compliance bot with signed rule changes
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