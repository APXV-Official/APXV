# Hello Agent Example

Minimal custom governed agent for APXV.

## Prerequisites

Run first-time setup from the project root:

```bash
python -m scripts.setup_first_run
```

On Linux/WSL use `python3` if `python` is not on PATH.

The example reuses `APXV-AGENT-LLM-001` from the default capability policy.

## Run

```bash
python examples/hello-agent/hello_agent.py "your message here"
```

## What It Demonstrates

- Attaching to `APXRuntime` (required for all governed agents)
- Capability checks before execution
- Writing an immutable artifact
- Chained audit logging

Use this as a template for your own deterministic agents.