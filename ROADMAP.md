# APXV Roadmap

**Last updated:** 2026-07-16

APXV is a local governed runtime. Verticals ship as **agent packs** on top. This is our direction — not a fixed timeline. See [CHANGELOG.md](CHANGELOG.md) for what has shipped.

## Shipped (v1.4.0 — current)

**v1.4.0 — author the workshop + cut legacy** — Pack Studio authoring wizard, **Build your pipeline** on-ramp, remove pre-v1.3 shims, trim unused entity circuits from default keygen.

- **Pack Studio wizard** — template → name → governance → activate → test run (`/packs?wizard=1`)
- **Build your pipeline** — Dashboard / Pack Studio entry; full agent/step composer planned for v1.5
- **Legacy cut** — `apxv_*` / `APXV_*` only; [MIGRATION-v1.4.md](docs/MIGRATION-v1.4.md)
- **ZK trim** — `normalization` + `threat` removed from default sovereign entity keygen (sources retained); [CIRCUITS.md](docs/cryptography/CIRCUITS.md)
- **UI polish** — onboarding, jobs, verify deep links, empty states
- **Branding** — product name **APXV** on operator surfaces

## Shipped (v1.3.3)

**v1.3.3 Windows desktop hotfix** — start/stop/restart/quit reliably manages `:8741` on Windows (Linux path largely shipped in v1.3.2).

- **Windows Python discovery** — desktop spawn finds real interpreter (not Store stub)
- **Orphan port reclaim** — foreign listeners cleared on start/restart
- **Settings Start/Restart** — resolves real install root
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
- **API v2** — `/api/v2/*`
- **Pack Studio** — activate and run official packs from the operator console
- **Production profile** — Ollama + Vosk or explicit disable
- Migration: [docs/MIGRATION-v1.3.md](docs/MIGRATION-v1.3.md) · Trust: [docs/SOVEREIGN-SETUP.md](docs/SOVEREIGN-SETUP.md)

## Shipped (v1.2.5)

Final v1.2.x consolidation — operator polish and install reliability.

## Where we're headed

### v1.5 — Workshop v1 (planned)

- **Workflow spec** — named steps, agent bindings, pack governance
- **Build your pipeline** step picker (beyond wizard templates)
- Agent scaffold; signed pack import from file; optional LLM integration packs
- macOS DMG / PDF export if bandwidth allows

### v1.6 — Workshop v2 (planned)

- Visual pipeline composer; multi-pack governance; proof module picker in UI

### v1.7 — Ecosystem (planned)

- Community pack registry tier; publishing guide; integration kits

### Later / optional

- **Deferred circuits** (`normalization`, `threat`) — only if a shipped pack needs them
- v1.8+ scale, ceremony depth, enterprise adjacency (demand-driven)

## What we're not building

- Cloud SaaS or hosted APXV
- HIPAA / SOC2 / GDPR certification claims
- A bundled LLM or "magic compliance" product
- Proofs that the LLM output was "correct" (proofs bind policy + hashes)

## Links

- [CHANGELOG.md](CHANGELOG.md) · [docs/MIGRATION-v1.4.md](docs/MIGRATION-v1.4.md) · [docs/DOWNLOADS.md](docs/DOWNLOADS.md)
