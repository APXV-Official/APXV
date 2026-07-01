# APXV Roadmap

**Last updated:** 2026-07-01

APXV1 is a local governed runtime. Verticals ship as **agent packs** on top. This is our direction — not a fixed timeline. See [CHANGELOG.md](CHANGELOG.md) for what has shipped.

## Shipped today (v1.2.1 — current)

Stability and operator-experience patch on v1.2.0. No verifier VK or circuit changes since v1.1.0.

- Audit log file locking; corrupt-line tolerance (health degrades instead of crashing `/status`)
- API key hint files (`managed/config/OPERATOR-KEY-*.txt`); hot-reload keys without restarting `apx_serve`
- Docker install removes stale `apx-v1` container automatically
- Configurable `APX_LLM_TIMEOUT_SECONDS` (default 120s)

## Shipped (v1.2.0)

- Governed runtime: rules, audit, artifacts, dual-track Groth16, local API
- **Official agent packs:** [Reference Redaction](governance-libraries/apxv-pack-reference-redaction/), [Document Processing](governance-libraries/apxv-pack-document-processing/), [AI Governance](governance-libraries/apxv-pack-ai-governance/)
- Entity circuits on default attest path: `merkle-inclusion`, `compliance` (plus existing `redaction-v1`, `core-redaction`, `batch-merkle`, optional `voice-redaction`)
- One-command install: `install.ps1` / `install-docker.ps1`; quick re-demo: `apx_demo.sh` / `apx_demo.ps1`
- Optional BYO ML redaction backend hook (audit envelope; not ZK-proven)

## Where we're headed

### Through v1.3 — platform and catalog

- **Pack catalog** — curated index to discover official and community packs (listings, docs, install paths)
- Remaining **platform depth** already sketched in the codebase (`normalization`, `threat` circuits, stronger ceremony story) as modules mature

### After v1.3 — local control plane UI

- Browse governance, run pipelines, inspect artifacts and health
- CLI/API and packs come first; UI follows once the foundation through v1.3 is solid

## What we're not building

- Cloud SaaS or hosted APXV
- HIPAA / SOC2 / GDPR certification claims
- A bundled LLM or "magic compliance" product
- PDF / DOCX enterprise DLP in core packs (batch `.txt` / `.json` only today)

## Feedback

Ideas and friction reports: [GitHub Issues](https://github.com/APXV-Official/APXV/issues) · Contributions: [CONTRIBUTING.md](CONTRIBUTING.md)