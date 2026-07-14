# APXV Roadmap

**Last updated:** 2026-07-14

APXV is a local governed runtime. Verticals ship as **agent packs** on top. This is our direction — not a fixed timeline. See [CHANGELOG.md](CHANGELOG.md) for what has shipped.

## Shipped (v1.3.3 — current)

**v1.3.3 Windows desktop hotfix** — start/stop/restart/quit reliably manages `:8741` on Windows (Linux path largely shipped in v1.3.2).

- **Windows Python discovery** — desktop spawn finds real interpreter (not Store stub)
- **Orphan port reclaim** — foreign listeners cleared on start/restart
- **Settings Start/Restart** — resolves real install root (no literal `%LOCALAPPDATA%` path from UI)
- **Settings errors** — server control failures visible to operator

## Shipped (v1.3.2)

**v1.3 series stabilization** — connect, run, read on Windows and Linux.

- **Linux desktop jobs** — pipeline/upload via Tauri HTTP (`resolveFetch`)
- **Server lifecycle (partial)** — Linux + API path; Windows desktop completed in v1.3.3
- **Onboarding** — operator key auto-discovery, test connection
- **Jobs UI** — SSE cache tuning, optimistic queue, faster fallback polling
- **Artifacts** — markdown **Report** tab + `.md` download
- **Pack Studio on-ramp** — duplicate reference pack, templates, tutorial links
- **APXV™** notices, [downloads hub](docs/DOWNLOADS.md), operator console polish

## Shipped (v1.3.1)

Desktop connectivity hotfix after v1.3.0.

- Linux **Connect** (`resolveFetch` / Tauri HTTP) and Jobs SSE CORS
- Windows server pile-up on relaunch; tray quit kills listeners
- Four installers: MSI, NSIS, deb, AppImage

## Shipped (v1.3.0)

Platform rename, sovereign local trust, desktop app, Pack Studio, API v2, operator console. No verifier VK or circuit semantic changes since v1.1.0.

- **Sovereign bootstrap** — `apxv_bootstrap`, operator-owned ZK keys, `install.json` provenance
- **Desktop app** — Windows MSI/NSIS + Linux deb/AppImage; bootstrap wizard
- **API v2** — `/api/v2/*`; legacy v1 with `Sunset: v1.4`
- **Pack Studio** — activate and run official packs from the operator console
- **Production profile** — Ollama + Vosk or explicit disable
- Migration: [docs/MIGRATION-v1.3.md](docs/MIGRATION-v1.3.md) · Trust: [docs/SOVEREIGN-SETUP.md](docs/SOVEREIGN-SETUP.md)

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

### v1.4 — composition and advanced circuits

- **Advanced circuits (`normalization`, `threat`)** — sovereign bootstrap already generates verifier keys; default `--attest` pipelines do not invoke them yet. v1.4 decision: wire behind feature flags (pre-redaction normalization, post-redaction threat scoring) or trim from default keygen — see [CIRCUITS.md](docs/cryptography/CIRCUITS.md) when we ship.
- **Pack Studio authoring assistant** — guided pack/agent creation (v1.3.2 ships clone + templates only)
- **PDF artifact export** — deferred from v1.3.2 operator scope

### After v1.3 — depth and ecosystem

- **Community pack registry** — remote catalog beyond in-repo official packs
- **macOS desktop** — DMG follow-up release

## What we're not building

- Cloud SaaS or hosted APXV
- HIPAA / SOC2 / GDPR certification claims
- A bundled LLM or "magic compliance" product
- PDF / DOCX enterprise DLP in core packs (batch `.txt` / `.json` only today)

## Feedback

Ideas and friction reports: [GitHub Issues](https://github.com/APXV-Official/APXV/issues) · Contributions: [CONTRIBUTING.md](CONTRIBUTING.md)