# APXV

[![CI](https://github.com/APXV-Official/APXV/actions/workflows/ci.yml/badge.svg)](https://github.com/APXV-Official/APXV/actions/workflows/ci.yml)

**APXV** (*Attested Proof Execution Verified*) is an air-gapped governed agent platform: markdown rules, signed capabilities, chained audit, Groth16 proofs, and a local API — bring your own LLMs. This repository ships **APXV1**, the first open-source implementation.

> **Current release:** [v1.1.2](https://github.com/APXV-Official/APXV/releases/tag/v1.1.2) — runtime + [Reference Redaction Pack](governance-libraries/apxv-pack-reference-redaction/). [CHANGELOG](CHANGELOG.md)

Clone the repo, run one command, and you get a working instance: setup, health checks, the reference pack pipeline, a full attestation, and independent ZK verification. Everything stays on your machine.

## One command

Pick the path that matches your machine:

| You have | Command |
|----------|---------|
| **Python 3.9+ and Rust** | `.\scripts\install.ps1` (Windows) or `./scripts/install.sh` (macOS/Linux) |
| **Docker only** (no local Python/Rust) | `.\scripts\install-docker.ps1` or `./scripts/install-docker.sh` |

Polluted from prior experiments? Add `-Fresh` (PowerShell) or `--fresh` (shell).

**What it runs:** `setup` → doctor → integrity → **Reference Redaction Pack** → `run_apx --attest` → `verify_attestation --real-zk`

**You should see:**

```
Pack demo complete: final_status=ATTESTED, total_redactions=4
ALL GOVERNANCE + ENTITY GROTH16 PROOFS INDEPENDENTLY VERIFIED [OK]
```

First native install may take a few minutes (Rust compile). Docker build is slower once, then cached.

Re-run without reinstalling: `python -m scripts.onboard --skip-setup`

Details: [docs/QUICKSTART.md](docs/QUICKSTART.md)

## The foundation

APXV1 is a **runtime you build on** — not a finished end-user product. The core repo gives you:

| Capability | What it means |
|------------|---------------|
| **Living governance** | Agents read `managed/rules`, `workflows`, and `knowledge` at runtime — not hardcoded prompts |
| **Controlled change** | Rule updates go through propose → approve → apply; audit chain records every action |
| **Signed capabilities** | Each agent is granted explicit permissions; policy is verified before execution |
| **Immutable artifacts** | Pipeline outputs land in SQLite + content-addressable storage |
| **Dual-track Groth16 ZK** | Governance proofs (3 circuits) + entity proofs (up to 4 per attest) over BN254 |
| **Local API** | HTTP on `127.0.0.1:8741` — no cloud, no telemetry |
| **Optional voice + E2EE** | Voice privacy suite and payload encryption when you need them |

The **3-agent reference pipeline** (redactor → orchestrator → attestation coordinator) is the pattern packs plug into. Core ships the agent machinery; packs supply the governance and vertical logic for a use case.

**Who this is for:** developers and teams building privacy-preserving agent pipelines on local infrastructure — with auditable rule changes, immutable artifacts, and cryptographically verifiable execution.

## Agent packs — extend the foundation

A **pack** is a vertical bundle on top of APXV1: governance specs, install steps, a runnable acceptance path, capability notes, and an acceptance checklist. You install only what you need; multiple packs can share one runtime.

**Packs are not the platform.** The platform is the runtime (store, audit, capabilities, ZK, API). A pack is how you turn that runtime into something specific — e.g. governed redaction.

### What's available today

| Artifact | Type | What you get |
|----------|------|--------------|
| [Reference Redaction Pack](governance-libraries/apxv-pack-reference-redaction/) | **Official pack** | Rules, workflow, knowledge for sensitive-text redaction → orchestration → attestation. Runnable acceptance path + acceptance tests. |
| [AI governance template](governance-libraries/ai-governance-template/) | **Template** | Starter markdown only — copy into `managed/` and customize. No agents or acceptance tests. |
| [governance-libraries/](governance-libraries/) | **Index** | Packs vs templates — read before assuming something is a full pack |

The Reference Redaction Pack agents ship in **APXV1 core** (`agents/agent1.py` … `agent3.py`). The pack provides the **governance bundle** that binds those agents to a real vertical — not duplicate agent code.

### How packs fit in

```
APXV1 core (this repo)          Agent pack (e.g. reference redaction)
─────────────────────────       ─────────────────────────────────────
Runtime, audit, store, ZK  +    Rules / workflows / knowledge
3-agent pipeline pattern   +    Install + acceptance + capability notes
Capability framework       +    Vertical binding for that use case
```

**Onboarding already applies the reference pack** — `install.ps1` / `install-docker.ps1` run the pack pipeline as proof the stack works. For production, follow the pack's own install flow (governance propose → approve → apply) in [apxv-pack-reference-redaction/README.md](governance-libraries/apxv-pack-reference-redaction/README.md).

### Build your own

| Goal | Start here |
|------|------------|
| Custom agent on the runtime | [docs/BUILDING.md](docs/BUILDING.md) |
| Minimal worked example | [examples/hello-agent/](examples/hello-agent/) |
| API integration | [examples/api-client/](examples/api-client/) |
| Local LLM (Ollama) | [examples/llm-ollama/](examples/llm-ollama/) |
| New vertical / community pack | BUILDING.md + pack layout in [governance-libraries/README.md](governance-libraries/README.md) |

**Direction:** [ROADMAP.md](ROADMAP.md) — packs through v1.3, then a local control plane UI.

## What it does not do

- Not HIPAA, SOC2, or GDPR certified
- Not full DLP-grade PII protection (pattern-based redaction)
- Not safe against malicious insiders with filesystem access
- Does not bundle an LLM — you add one if you need it

See [SECURITY.md](SECURITY.md) for the full threat model.

## Verify without re-running

**Verifier bundle (VKs only):** [v1.1.2 release assets](https://github.com/APXV-Official/APXV/releases/tag/v1.1.2) (`apxv1-verifier-bundle-v1.1.0.zip` — VKs unchanged since v1.1.0), or export your own after `setup_first_run`:

```bash
python -m scripts.export_verifier_bundle --out dist/apxv1-verifier-bundle
```

| You want to… | Trust |
|--------------|-------|
| Run APXV1 yourself (`setup_first_run`, your keys) | **Yourself** |
| Verify artifacts from a published release | **Publisher's setup** for those VKs (proof math is self-checking; setup honesty is separate) |

See [docs/cryptography/CEREMONY.md](docs/cryptography/CEREMONY.md).

Reference Groth16 `.pk`/`.vk` files ship in the repository so install → attest works out of the box. For your own trust boundary, run `setup_first_run` and protect your proving keys — see [SECURITY.md](SECURITY.md) and [docs/cryptography/SETUP.md](docs/cryptography/SETUP.md).

## Status

**v1.1.2 (current)** — one-command onboarding (native + Docker), install-path fixes. **311 tests pass in CI** (312 collected, 1 optional Vosk skip). Prior releases: [CHANGELOG.md](CHANGELOG.md).

## Architecture

```mermaid
flowchart TB
  subgraph governance [Governance]
    Rules[rules / workflows / knowledge]
    Approval[propose → approve → apply]
  end

  subgraph runtime [APXV1 Runtime]
    API[Local API :8741]
    Cap[Signed capabilities]
    Redact[RedactionEngine v3]
    Agents[3-agent reference pipeline]
    Store[(SQLite + CAS artifacts)]
    Audit[(Chained audit logs)]
  end

  subgraph crypto [Attestation]
    ZKA[Governance ZK — apx-circuits]
    ZKB[Entity ZK — apx-zk]
    Verify[Independent verify]
  end

  Rules --> Agents
  Approval --> Rules
  Cap --> Agents
  Redact --> Agents
  Agents --> Store
  Agents --> Audit
  Agents --> ZKA
  Agents --> ZKB
  ZKA --> Verify
  ZKB --> Verify
  API --> Agents
```

| Layer | Components |
|-------|------------|
| **Privacy** | `APXRedactionEngine`, optional `APXE2EE` |
| **Deterministic core** | RuleGovernedRedactor, WorkflowOrchestrator, AttestationCoordinator |
| **Agentic layer** | `LLMBackend`, `LLMReasoner`, `ToolUser`, `AgenticContract` |
| **Governance & control** | CapabilityChecker, AuditLogger, GovernanceRegistry |
| **Cryptographic layer** | Dual Groth16 tracks over BN254 (arkworks) |

See [PROJECT-OVERVIEW.md](PROJECT-OVERVIEW.md) for repository layout and component index.

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | Install, troubleshoot, re-run onboarding |
| [docs/BUILDING.md](docs/BUILDING.md) | Custom agents, API, LLMs, deployment |
| [governance-libraries/](governance-libraries/) | Official packs and templates |
| [PROJECT-OVERVIEW.md](PROJECT-OVERVIEW.md) | Repository layout and architecture |
| [docs/DOCKER.md](docs/DOCKER.md) | Container deployment |
| [docs/LOCAL-API.md](docs/LOCAL-API.md) | API reference |
| [SECURITY.md](SECURITY.md) | Threat model |
| [CHANGELOG.md](CHANGELOG.md) | Release history |
| [ROADMAP.md](ROADMAP.md) | Where we're headed |

## Docker

See [docs/DOCKER.md](docs/DOCKER.md). Prefer `install-docker.ps1` / `install-docker.sh` for first-time setup; use **fresh volumes** for production-like deploys.

```bash
docker compose up -d --build
curl http://127.0.0.1:8741/health
```

## Backup

```bash
python -m scripts.apx_ctl backup-create
```

Back up `managed/`, `rust/apx-circuits/keys/`, and `rust/apx-zk/keys/` regularly.

## Support

APXV1 is open source (Apache 2.0).

- **Bugs and how-to:** [GitHub Issues](https://github.com/APXV-Official/APXV/issues) — include `python -m scripts.apx_doctor` output
- **Security:** [SECURITY.md](SECURITY.md) — do not post vulnerabilities in public issues
- **Contact:** [@APXVdev](https://github.com/APXVdev) · [APXVdev@protonmail.com](mailto:APXVdev@protonmail.com)

Community support is best-effort. Start with [docs/QUICKSTART.md](docs/QUICKSTART.md) and [docs/BUILDING.md](docs/BUILDING.md).

## Attribution

**APXV** is the platform; **APXV1** is the implementation line shipped from this repository. Neither is a registered trademark. If you build on APXV1, we appreciate (but do not require) a credit such as:

**Built with [APXV / APXV1](https://github.com/APXV-Official/APXV)** — *Attested Proof Execution Verified*

Please do not imply your project is an official APXV product unless you have a separate agreement with the maintainer.

## License

Copyright © 2026 [APXV Official](https://github.com/APXV-Official). Licensed under the [Apache License, Version 2.0](LICENSE). See [NOTICE](NOTICE) for redistribution attribution.