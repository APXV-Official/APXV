# APXV Roadmap

**Last updated:** 2026-06-26

APXV1 is a local governed runtime. Verticals ship as **agent packs** on top. This is our direction — not a fixed timeline. See [CHANGELOG.md](CHANGELOG.md) for what has shipped.

## Shipped today (v1.1.2)

- Governed runtime: rules, audit, artifacts, dual-track Groth16, local API
- [Reference Redaction Pack](governance-libraries/apxv-pack-reference-redaction/) — first official pack
- One-command install: `install.ps1` / `install-docker.ps1`

## Where we're headed

### Through v1.3 — platform and packs

- More **official agent packs** (e.g. AI governance, document processing)
- **Pack catalog** — a curated index to discover official and community packs (not a paid app store on day one; listings, docs, and install paths first)
- Remaining **platform depth** already sketched in the codebase (extra ZK circuits, stronger ceremony story) as modules mature

### After v1.3 — local control plane UI

- Browse governance, run pipelines, inspect artifacts and health
- CLI/API and packs come first; UI follows once the foundation through v1.3 is solid

## What we're not building

- Cloud SaaS or hosted APXV
- HIPAA / SOC2 / GDPR certification claims
- A bundled LLM or “magic compliance” product

## Feedback

Ideas and friction reports: [GitHub Issues](https://github.com/APXV-Official/APXV/issues) · Contributions: [CONTRIBUTING.md](CONTRIBUTING.md)