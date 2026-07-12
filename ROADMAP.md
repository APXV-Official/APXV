# APXV Roadmap

**Last updated:** 2026-07-09

APXV is a local governed runtime. Verticals ship as **agent packs** on top. Operators compose agents, rules, and workflows on their own infrastructure and obtain **proof of what actually ran** — not proof of what an LLM suggested.

This is our direction — not a fixed timeline. See [CHANGELOG.md](CHANGELOG.md) for what has shipped.

## Shipped today (v1.3.1 — current)

Desktop connectivity hotfix on the v1.3 platform. No verifier VK or circuit semantic changes since v1.1.0.

- **Linux desktop Connect** — API calls via `tauri-plugin-http` (WebKit mixed-content bypass)
- **Jobs live stream** — SSE CORS for `/api/v2/jobs/stream` in the operator console
- **Windows lifecycle** — single `apxv_serve` on `:8741`; clean stop on Quit
- **Connect flow** — setup navigation, desktop CORS origins, visible Quit on bootstrap

## Shipped (v1.3.0)

Platform rename, sovereign local trust, desktop app, Pack Studio, API v2, operator console.

- **Sovereign bootstrap** — `apxv_bootstrap`, operator-owned ZK keys, `install.json` provenance
- **Desktop app** — Windows MSI/NSIS + Linux deb/AppImage; bootstrap wizard
- **API v2** — `/api/v2/*`; legacy v1 with `Sunset: v1.4`
- **Pack Studio** — create, clone, activate, and run packs from the operator console
- **Production profile** — Ollama + Vosk or explicit disable
- Migration: [docs/MIGRATION-v1.3.md](docs/MIGRATION-v1.3.md) · Trust: [docs/SOVEREIGN-SETUP.md](docs/SOVEREIGN-SETUP.md)

## In progress (v1.3.2)

Patch release from operator dogfood on installed v1.3.1 — **reliability and clarity**, not new platform features.

- **Linux jobs** — pipeline execution on Linux desktop
- **Onboarding / API key** — smoother connect path (surface key, test connection)
- **Server lifecycle** — reliable stop/start and single listener on `:8741` (Windows + Linux)
- **Jobs UI** — reduce API↔UI delay (SSE / cache tuning)
- **Artifacts** — human-readable markdown summary (JSON remains under “Raw”)
- **Pack Studio on-ramp** — templates and guided copy (full assistant → v1.5)
- **APXV™** notices in README, NOTICE, app About, website
- **Downloads hub** — one canonical release URL linked from README and site
- **Circuits** — document `normalization` / `threat` as reserved (full wire-up deferred to v1.4 — see Platform and ecosystem)

**Deferred from v1.3.2:** PDF export, wire unused circuits to attest path, governed authoring assistant.

See [CHANGELOG.md](CHANGELOG.md) `## [1.3.2]` when tagged.

## Shipped (v1.2.5)

Final v1.2.x consolidation — operator polish and install reliability.

- Windows Docker: suppress benign `docker rm` stderr on second consecutive `install-docker.ps1` run
- Document pack demo uses explicit batch fixtures (stray files in demo dir ignored)
- `APX_DEV_WARNINGS=1` for BYO ML backend entity shape advisories
- `verify_attestation --real-zk` exit code matches verification on Windows
- Linux/WSL `python3` guidance and CONTRIBUTING Windows vs Linux table

## Shipped (v1.2.2)

Operator clarity and install parity patch on v1.2.1.

- Audit integrity diagnostics: `corrupt_lines` vs `chain_break` in `apxv_doctor`, `apxv_ctl integrity`, and `/health`
- Windows Docker install parity: `install-docker.ps1` removes stale containers from prior installs before `compose up -d`
- Upgrade runbooks and QUICKSTART recovery flows for degraded health and missing API key hint files
- ASCII-safe GitHub release notes via `scripts/publish_github_release.py`

## Shipped (v1.2.1)

Stability and operator-experience patch on v1.2.0.

- Audit log file locking; corrupt-line tolerance (health degrades instead of crashing `/status`)
- API key hint files (`managed/config/OPERATOR-KEY-*.txt`); hot-reload keys without restarting `apxv_serve`
- Docker install removes stale containers automatically (bash; extended to PowerShell in v1.2.2)
- Configurable `APX_LLM_TIMEOUT_SECONDS` (default 120s)

## Shipped (v1.2.0)

- Governed runtime: rules, audit, artifacts, dual-track Groth16, local API
- **Official agent packs:** [Reference Redaction](governance-libraries/apxv-pack-reference-redaction/), [Document Processing](governance-libraries/apxv-pack-document-processing/), [AI Governance](governance-libraries/apxv-pack-ai-governance/)
- Entity circuits on default attest path: `merkle-inclusion`, `compliance` (plus existing `redaction-v1`, `core-redaction`, `batch-merkle`, optional `voice-redaction`)
- One-command install: `install.ps1` / `install-docker.ps1`; quick re-demo: `apxv_demo.sh` / `apxv_demo.ps1`
- Optional BYO ML redaction backend hook (audit envelope; not ZK-proven)

## Where we're headed

### Self-serve composition (v1.4+)

Make APXV a place where anyone can build and run their own governed data processes on local infrastructure:

- **Mix and match** — combine agents and packs across jobs in a pipeline; switch active governance per workflow
- **Pack Studio depth** — clearer create/clone flows, templates, and guided “first pack” paths without hand-editing install runbooks
- **Governance as product** — rules, workflows, and knowledge remain propose → approve → apply; proofs attach to **execution**, not drafts

### Governed authoring assistant (v1.5+)

A chat-style page in the operator console that helps users **design** agents, packs, rules, and workflows — separate from the pipeline that **runs** them.

| Plane | Role | LLM | Network | Proof |
|-------|------|-----|---------|-------|
| **Authoring** (assistant UI) | Draft packs, rules, agent chains; explain governance | BYO — local Ollama default, optional cloud API key the operator supplies | Only what the operator configures for the assistant | None — design help only |
| **Execution** (pipeline) | Process data under approved governance | Only where an approved pack explicitly allows it (e.g. AI governance pack) | Local / air-gapped by default | Attestations + ZK where applicable |

**Design principles (non-negotiable):**

- The assistant **does not** call the pipeline, read customer batch data, or auto-approve governance
- Model output is **untrusted** — schema validation, diff review, then human approve before apply
- **BYO LLM** — APXV does not host models or send pipeline data to a vendor; the operator chooses local vs cloud for *authoring* only
- Pack Studio and raw governance APIs stay first-class for power users; the assistant is an on-ramp, not a replacement

**Positioning:** *BYO AI to design your governed agents; local execution with proof that your data process ran as approved.*

### Platform and ecosystem (ongoing)

- **Community pack registry** — remote catalog beyond in-repo official packs
- **Platform depth** — `normalization`, `threat` circuits, stronger ceremony story as modules mature
- **macOS desktop** — DMG follow-up release
- **API v1 sunset** — complete migration to v2 per v1.3 deprecation window

## What we're not building

- Cloud SaaS or hosted APXV
- HIPAA / SOC2 / GDPR certification claims
- A bundled LLM or "magic compliance" product
- An autonomous agent with pipeline access or silent governance changes
- PDF / DOCX enterprise DLP in core packs (batch `.txt` / `.json` only today)

## Feedback

Ideas and friction reports: [GitHub Issues](https://github.com/APXV-Official/APXV/issues) · Contributions: [CONTRIBUTING.md](CONTRIBUTING.md)