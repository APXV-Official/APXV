# APXV1

**APXV1** — *Attested Proof Execution Verified* — **1st-generation** open-source, air-gapped platform for building governed agent systems.

> Not [apx.guide](https://apx.guide) / `apx-project` semantic-drift tooling. Current release: **v0.3.0**.

Run APXV1 locally. Your rules, data, artifacts, and cryptographic proofs stay on your machine. Build your own agents, workflows, and integrations on your infrastructure.

## Who This Is For

- **Developers** building privacy-preserving agent pipelines on local infrastructure
- **Companies** prototyping self-hosted governance without cloud dependency
- **Teams** that need auditable rule changes, immutable artifacts, and verifiable execution

APXV1 is a **foundation to build on** — not a finished end-user product.

## What You Get

- **Governed agents** — read living markdown rules, workflows, and knowledge at runtime
- **Immutable artifacts** — SQLite + content-addressable storage
- **Chained audit logs** — every action recorded and verifiable
- **Signed capability policies** — agents only do what they're granted
- **Governance approval workflow** — propose → approve → apply rule changes
- **Groth16 ZK proofs** — real, independently verifiable attestation (required)
- **Local HTTP API** — localhost only, no cloud, no telemetry
- **Pluggable LLMs** — bring Ollama or any backend via `LLMBackend` (optional)

## What It Does NOT Do

- Not HIPAA, SOC2, or GDPR certified
- Not full DLP-grade PII protection (pattern-based redaction)
- Not safe against malicious insiders with filesystem access
- Does not bundle an LLM — you add one if you need it

See [SECURITY.md](SECURITY.md) for the full threat model.

## Status

Phase 1 (cryptography) and Phase 2 (governed core) are complete. The deterministic 3-agent reference pipeline and ZK attestation path are verified end-to-end. See [PROJECT-OVERVIEW.md](PROJECT-OVERVIEW.md) for component details.

## Quickstart

**Start here:** [docs/QUICKSTART.md](docs/QUICKSTART.md) (15 minutes)

### One-command install

**Windows:** `.\scripts\install.ps1`  
**macOS/Linux:** `./scripts/install.sh`

Requires Python 3.9+ and Rust ([install guide](docs/INSTALL-RUST.md)).

### Health check

```bash
python -m scripts.apx_doctor
python -m scripts.apx_ctl integrity
```

### API keys

```bash
python -m scripts.apx_ctl api-key create my-app
export APX_API_KEY="<key>"
python -m scripts.apx_serve
```

## Build On APXV1

| Resource | Description |
|----------|-------------|
| [docs/BUILDING.md](docs/BUILDING.md) | **Start here** — agents, API, LLMs, deployment |
| [examples/hello-agent/](examples/hello-agent/) | Minimal custom governed agent |
| [examples/api-client/](examples/api-client/) | Python API client |
| [examples/llm-ollama/](examples/llm-ollama/) | Plug in a local Ollama LLM |
| [governance-libraries/](governance-libraries/) | Reusable governance templates |

## Docker

See [docs/DOCKER.md](docs/DOCKER.md). Use **fresh volumes** for clean deploys.

```bash
docker compose up -d --build
curl http://127.0.0.1:8741/health
```

## Architecture

- **Deterministic Core** — RuleGovernedRedactor, WorkflowOrchestrator, AttestationCoordinator
- **Agentic Layer** — `LLMBackend` + `LLMReasoner` (pluggable), `ToolUser`, `AgenticContract`
- **Governance & Control** — CapabilityChecker, AuditLogger, GovernanceRegistry
- **Cryptographic Layer** — Groth16 proofs over BN254 (arkworks)

## Documentation

| Doc | Purpose |
|-----|---------|
| [PROJECT-OVERVIEW.md](PROJECT-OVERVIEW.md) | Repository layout and components |
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | Getting started |
| [docs/BUILDING.md](docs/BUILDING.md) | Extension patterns |
| [docs/INSTALL-RUST.md](docs/INSTALL-RUST.md) | Rust toolchain setup |
| [docs/DOCKER.md](docs/DOCKER.md) | Container deployment |
| [docs/AIR-GAP-INSTALL.md](docs/AIR-GAP-INSTALL.md) | Offline install |
| [docs/LOCAL-API.md](docs/LOCAL-API.md) | API reference |
| [SECURITY.md](SECURITY.md) | Threat model |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |
| [RUNBOOKS/](RUNBOOKS/) | Deployment and operations |

## Backup

```bash
python -m scripts.apx_ctl backup-create
```

Back up `managed/` and `rust/keys/` regularly.

## Support

APXV1 is open source (Apache 2.0).

- **Bugs and how-to:** [GitHub Issues](https://github.com/apxv1dev/APXV1/issues) — include `python -m scripts.apx_doctor` output
- **Security:** [SECURITY.md](SECURITY.md) — do not post vulnerabilities in public issues
- **Contact:** [@apxv1dev](https://github.com/apxv1dev) · [apxv1dev@protonmail.com](mailto:apxv1dev@protonmail.com)

Community support is best-effort. Start with [docs/QUICKSTART.md](docs/QUICKSTART.md) and [docs/BUILDING.md](docs/BUILDING.md).

## License

Copyright © 2026 The APXV1 Project. Licensed under the [Apache License, Version 2.0](LICENSE).