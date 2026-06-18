# APXV1

**The APXV1 Project** — *Attested Proof Execution Verified* — open-source, air-gapped platform for building governed agent systems.

Maintained by [@apxv1dev](https://github.com/apxv1dev) · [apxv1dev@protonmail.com](mailto:apxv1dev@protonmail.com)

> **APXV1** is the first-generation APX platform (release **v0.3.0**). Not [apx.guide](https://apx.guide) / `apx-project` semantic-drift tooling.

Run APX locally. Your rules, data, artifacts, and cryptographic proofs stay on your machine. **Build your own agents, workflows, and integrations** — as an individual developer or as a company team.

## Who This Is For

- **Developers** building privacy-preserving agent pipelines on local infrastructure
- **Companies** prototyping self-hosted governance without cloud dependency
- **Teams** that need auditable rule changes, immutable artifacts, and verifiable execution

APX is a **foundation to build on** — not a finished end-user product.

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

Working platform foundation: Phase 1 (cryptography) and Phase 2 (governed core) complete. Deterministic 3-agent pipeline + ZK attestation verified end-to-end. LLM support is via pluggable backends — see [examples/llm-ollama/](examples/llm-ollama/).

## Quickstart

**Start here:** [docs/QUICKSTART.md](docs/QUICKSTART.md) (15 minutes)

### One-command install

**Windows:** `.\scripts\install.ps1`  
**macOS/Linux:** `./scripts/install.sh`

Requires Python 3.9+ and Rust ([install guide](docs/INSTALL-RUST.md)).

### Health check anytime

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

## Build On APX

| Resource | Description |
|----------|-------------|
| [docs/BUILDING.md](docs/BUILDING.md) | **Start here** — agents, API, LLMs, company deployment |
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

## Operator Docs

| Doc | Purpose |
|-----|---------|
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | 15-minute getting started |
| [docs/BUILDING.md](docs/BUILDING.md) | How to build on APX |
| [docs/INSTALL-RUST.md](docs/INSTALL-RUST.md) | Rust toolchain setup |
| [docs/DOCKER.md](docs/DOCKER.md) | Company Docker deploy |
| [docs/AIR-GAP-INSTALL.md](docs/AIR-GAP-INSTALL.md) | Offline install |
| [docs/LOCAL-API.md](docs/LOCAL-API.md) | API reference |
| [SECURITY.md](SECURITY.md) | Threat model |
| [docs/MARKET-LANDSCAPE.md](docs/MARKET-LANDSCAPE.md) | Market scan & positioning |
| [docs/PUBLISH-READINESS.md](docs/PUBLISH-READINESS.md) | Pre-push checklist (maintainers) |

## Backup

```bash
python -m scripts.apx_ctl backup-create
```

Back up `managed/` and `rust/keys/` regularly.

## Community support

APXV1 is open source (Apache 2.0). For bugs and how-to questions, use [GitHub Issues](https://github.com/apxv1dev/APXV1/issues) and include output from `python -m scripts.apx_doctor`.

- **Best effort only** — no guaranteed response time for free support
- Start with [docs/QUICKSTART.md](docs/QUICKSTART.md) and [docs/BUILDING.md](docs/BUILDING.md)
- **Security:** see [SECURITY.md](SECURITY.md) — do not post vulnerabilities in public issues

## Professional services

Implementation, air-gapped deployment, custom agents, and team training may be available on a scoped basis for US organizations.

- Paid work is **separate** from the open-source project and does not include an SLA unless agreed in writing
- APX remains a **research foundation** — not a certified compliance product

Contact: [@apxv1dev](https://github.com/apxv1dev) · [apxv1dev@protonmail.com](mailto:apxv1dev@protonmail.com) (commercial inquiries welcome via issue or email).

## License

Apache License 2.0 — see [LICENSE](LICENSE).