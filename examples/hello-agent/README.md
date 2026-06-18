# Hello Agent Example

Minimal custom governed agent for APX v1.

## Prerequisites

Run first-time setup from the project root:

```bash
python -m scripts.setup_first_run
```

The example reuses `APX-AGENT-LLM-001` from the default capability policy.

## Run

```bash
python examples/hello-agent/hello_agent.py "your message here"
```

## What It Demonstrates

- Attaching to `APXRuntime`
- Capability checks before execution
- Writing an immutable artifact
- Chained audit logging

Use this as a template for your own deterministic agents.