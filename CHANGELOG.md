# Changelog

All notable changes to APXV are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.1] - 2026-07-09

Desktop connectivity hotfix — operators can Connect and use Jobs on **Windows and Linux** without manual API patching.

### Fixed

- **Linux desktop Connect** — `Load failed` when pairing operator key; WebKitGTK blocks HTTPS UI → HTTP API (`tauri.localhost` → `127.0.0.1:8741`). API calls now use `tauri-plugin-http` (Rust), bypassing mixed-content restrictions.
- **Jobs live updates** — SSE `/api/v2/jobs/stream` missing CORS headers; showed `Connecting… · Failed to fetch` while pipelines still ran.
- **Windows server pile-up** — duplicate `apxv_serve` on `:8741` after relaunch; spawn real `python.exe`, skip start if port reachable, stop all listeners on Quit.
- **Connect flow** — setup navigation after Connect; visible Quit on setup; CORS origins for Tauri desktop webview.

### Added

- `scripts/patch_jobs_stream_cors.py` — in-place patch for v1.3.0 runtime trees (SSE CORS only; Linux Connect still needs 1.3.1 desktop build).

### Chore

- Ship artifacts: `APXV_1.3.1_x64_en-US.msi`, `APXV_1.3.1_x64-setup.exe`, `APXV_1.3.1_amd64.deb`, `APXV_1.3.1_amd64.AppImage`

## [1.3.0] - 2026-07-09

Platform rename, **sovereign local trust**, desktop app, Pack Studio, and API v2. No Groth16 circuit semantic changes since v1.1.0 — each deployment runs its own trusted setup ceremony.

### Added

- **Sovereign bootstrap** — `python -m scripts.apxv_bootstrap`; `managed/config/install.json` with `sovereign_setup` and `vk_hashes` (11 circuits)
- **Desktop app** — Windows MSI/NSIS and Linux deb/AppImage (Tauri); first-launch bootstrap wizard; system tray
- **REST API v2** — `/api/v2/*` (Pack Studio, jobs SSE, governance, uploads); v1 endpoints retained with `Deprecation: true`, `Sunset: v1.4`
- **Pack Studio** — create, clone, activate, and run packs from the operator console
- **Operator console** — React + Tauri UI over API v2 (pipelines, artifacts, verify, governance)
- **Production profile** — Ollama + Vosk or explicit disable; no simulated LLM/voice on operator paths
- **Install paths** — `install-full.ps1` / `.sh` (native sovereign), `install-docker.*` (binaries only, keys on volumes), [INSTALL-USER.md](docs/INSTALL-USER.md) for desktop
- **Migration guide** — [MIGRATION-v1.3.md](docs/MIGRATION-v1.3.md), [SOVEREIGN-SETUP.md](docs/SOVEREIGN-SETUP.md)
- **Vendor key guard** — `apxv_doctor` rejects pre-v1.3 baked VK hashes (migration blocklist)
- **Governance seed specs** in desktop/Linux payloads (`rule1`, `workflow1`, `knowledge1`)

### Changed

- **Platform rename** — `apx` → `apxv` (Python package, CLI, Rust binaries, env vars `APXV_*`, SQLite `apxv.db`, agent IDs `APXV-AGENT-*`)
- **Docker image** — service `apxv`; ships prover binaries only (no baked proving keys)
- **Legacy shims** — `apx_serve`, `apx_ctl`, `apx_doctor`, `run_apx` warn and delegate to `apxv_*` (removed in v1.4)
- **Verifier bundle** — export name `apxv-verifier-bundle` (VK bytes unchanged since v1.1.0)
- Operator-facing docs and site aligned to v1.3 sovereign story; deprecated Control Plane branding removed from UI

### Fixed

- Linux desktop build (WSL rsync/staging); governance seeds and `docs/internal` pruning in installer payloads
- `install-docker.ps1`: suppress Docker Compose v2 progress stderr on Windows
- Desktop smoke: localhost bind for `apxv_serve` during Tauri validation

### Documentation

- New: `SOVEREIGN-SETUP.md`, `INSTALL-USER.md`; updated QUICKSTART, DOCKER, AIR-GAP, MIGRATION-v1.3, OPERATOR-GUIDE, GitHub Pages site
- Public-facing audit gate: 290+ parametrized checks (docs, web UI source, desktop payload when staged); **756** pytest tests (1 optional Vosk skip)

### Chore

- Ship artifacts: `APXV_1.3.0_x64_en-US.msi`, `APXV_1.3.0_x64-setup.exe`, `APXV_1.3.0_amd64.deb`, `APXV_1.3.0_amd64.AppImage`
- macOS DMG deferred to follow-up release

## [1.2.5] - 2026-07-03

Final v1.2.x consolidation — operator polish and install reliability. No verifier VK or circuit changes since v1.1.0. No APX→APXV renames (planned for v1.3.0).

### Fixed

- `install-docker.ps1`: suppress benign `docker rm -f apx-v1` stderr on Windows when container already removed (F-018)
- Document pack demo: default batch uses explicit fixture list — stray files in `examples/inputs/batch/` ignored
- `verify_attestation --real-zk`: suppress benign subprocess `RuntimeWarning` on Windows (exit code matches verification)

### Added

- BYO ML backend: optional `APX_DEV_WARNINGS=1` surfaces malformed `entities[]` at dev time (not ZK-proven)

### Changed

- Linux/WSL docs and examples: canonical `python3` / venv guidance; Windows contributor notes in CONTRIBUTING

### Documentation

- RUNBOOK-OPERATIONS: expanded audit chain-break recovery steps
- DOCKER.md: Windows second-install behavior
- Install script banners and GitHub Pages site aligned to v1.2.5 (356 tests)

No verifier VK or circuit changes since v1.1.0.

## [1.2.2] - 2026-07-02

Operator clarity and install parity patch. No verifier VK or circuit changes since v1.1.0.

### Fixed

- `install-docker.ps1` removes stale `apx-v1` container before `docker compose up -d` (parity with `.sh`)
- `install-docker.ps1` (post-release patch): suppress `docker rm -f apx-v1` stderr on Windows when the container was already removed by `compose down` — fixes second consecutive install aborting under `$ErrorActionPreference Stop`

### Added

- Audit integrity diagnostics: distinguish corrupt log lines vs hash-chain break in `apx_doctor`, `apx_ctl integrity`, and `/health`
- Upgrade runbook: recovering degraded health; API key hints for in-place upgrades from v1.2.0

### Changed

- `/health` reports per-audit-log summary (`chain_valid`, `corrupt_line_count`) when integrity is degraded

### Documentation

- QUICKSTART, LOCAL-API, DOCKER, BUILDING, RUNBOOK-UPGRADE, RUNBOOK-OPERATIONS, website, and CONTRIBUTING updated for v1.2.2

### Chore

- GitHub release template (ASCII-only); verifier bundle asset on release
- Install script banners and GitHub Pages site aligned to v1.2.2 (352 tests)

No verifier VK or circuit changes since v1.1.0.

## [1.2.1] - 2026-06-29

Stability and operator-experience patch. No verifier VK or circuit changes since v1.1.0.

### Fixed

- Audit log: file locking on append; `get_entries()` / `get_status()` tolerate corrupt lines without crashing `/status`
- Document pack tests use isolated `tmp_path` batch fixtures
- API tests bind ephemeral port (no collision with running `apx_serve`)
- Write `managed/config/OPERATOR-KEY-default-operator.txt` when default API key is created
- Reload API keys on each authenticated request (hot-reload after `apx_ctl api-key create`)
- `install-docker.sh` removes stale `apx-v1` container before `docker compose up -d`
- Configurable `APX_LLM_TIMEOUT_SECONDS` for slow local LLMs (default 120s)

### Changed

- `datetime.utcnow()` replaced with timezone-aware UTC in core agents, audit logger, and artifact provider

### Documentation

- QUICKSTART, LOCAL-API, DOCKER, BUILDING, CONTRIBUTING, README, PROJECT-OVERVIEW, ROADMAP, examples, website, and AI Governance pack README updated for v1.2.1 operator flows

### Chore

- Install script banners and GitHub Pages site aligned to v1.2.1 (343 tests)

## [1.2.0] - 2026-06-28

**APXV1 v1.2.0** — entity circuit wiring (`merkle-inclusion`, `compliance`), two new official agent packs, BYO ML redaction hook, and easier re-demo path. Verifier VKs unchanged since v1.1.0.

### Added

- **`merkle-inclusion`** and **`compliance`** entity circuits on the default `--attest` path (when conditions apply)
- `agents/zk/compliance_policy.py` — compliance policy ids 1–5 resolution and witness builder
- `agents/zk/merkle_tree.py` — `build_merkle_inclusion_witness()` for per-entity inclusion proofs
- `governance-libraries/apxv-pack-document-processing/` v0.1.0 — batch `.txt` / `.json` folder ingest, manifest, compliance policy id 2
- `governance-libraries/apxv-pack-ai-governance/` v0.1.0 — redaction + `LLMReasoner` review, compliance policy id 4
- `agents/redaction/backends.py` — optional `RedactionBackend` registry for BYO ML redaction (audit only; not ZK-proven)
- `scripts/apx_demo.py`, `scripts/apx_demo.sh`, `scripts/apx_demo.ps1` — pack demo → attest → verify with artifact path
- `scripts/onboard.py --pack` — `reference`, `document`, `ai`, or `all`
- Tests: `test_document_processing_pack.py`, `test_ai_governance_pack.py`, `test_redaction_backend.py`, `test_apx_demo.py`; extended `test_zk_entity_bundle.py`

### Changed

- `agents/zk/bridge.py`, `scripts/verify_attestation.py` — per-entity `merkle_inclusion_*` keys and `compliance` verification
- `scripts/install.sh` — auto `.venv` on Linux/WSL when system pip is restricted; `build-essential` warning
- README, QUICKSTART — 5-minute `apx_demo` path; Linux/WSL prerequisites; all three official packs documented
- `docs/cryptography/CIRCUITS.md`, `VERIFICATION.md`, `SECURITY-ARCHITECTURE.md` — v1.2 entity path
- `docs/BUILDING.md`, `SECURITY.md` — BYO ML redaction honest scope

### Fixed

- Entity proof bundle includes `compliance` when pack or artifact sets `compliance_policy_id`

## [1.1.2] - 2026-06-26

**APXV1 v1.1.2** — one-command onboarding (native + Docker) and install-path fixes. Verifier VKs unchanged since v1.1.0.

> **Note:** If you tagged or downloaded **v1.1.1** expecting `install.ps1` / `install-docker.ps1`, use **v1.1.2** — onboarding shipped after the v1.1.1 tag.

### Added

- `scripts/onboard.py` — guided onboarding: setup → doctor → integrity → pack demo → attest → `verify_attestation --real-zk`
- `scripts/install.ps1` / `scripts/install.sh` — native one-command install (`-Fresh` / `--fresh` for polluted runtime state)
- `scripts/install-docker.ps1` / `scripts/install-docker.sh` — Docker-only install (no local Python/Rust)
- `scripts/fresh_reset.py` — reset runtime dirs while preserving governance templates (`managed/rules`, `workflows`, `knowledge`)
- Dockerfile: `COPY governance-libraries` for in-container pack demo

### Fixed

- `-Fresh` no longer moves entire `managed/` (Docker build requires governance templates in build context)
- Docker install seeds ZK keys from image before compose run (host volume mounts hide baked-in keys)
- `rust_bins.py` resolves `apx-zk` / `apx-circuits` from PATH (containers use `/usr/local/bin`, not `cargo run`)
- `apx_doctor` accepts baked binaries when `APX_CONTAINER_BIND=1`
- `install-docker.ps1`: `$Args` parameter shadowing, ASCII-only banners for `-File` parser
- `install.ps1`: `-Fresh`, early Rust missing exit, `$LASTEXITCODE` after pip/onboard
- `install-docker.ps1` / `.sh`: stop existing container when port 8741 is in use
- `onboard.py`: suppress noisy subprocess `RuntimeWarning`

### Changed

- README, QUICKSTART — v1.1.2-first onboarding; `-Fresh` clears runtime only

## [1.1.1] - 2026-06-25

**APXV1 v1.1.1** — first official agent pack and honest extend documentation.

### Added

- `governance-libraries/apxv-pack-reference-redaction/` — Reference Redaction Pack v0.1.0 (governance bundle, demo, acceptance)
- `governance-libraries/README.md` — index distinguishing packs vs templates
- `tests/test_reference_redaction_pack.py` — pack layout, governance hash lock, demo smoke test

### Changed

- README, BUILDING.md, PROJECT-OVERVIEW.md — packs vs governance templates; no implied vaporware for unreleased verticals
- Public repo migrated to **APXV-Official/APXV** (org APXV Official; maintainer @APXVdev)
- `docs/QUICKSTART.md` — troubleshooting for audit-chain pollution and slow first attestation

## [1.1.0] - 2026-06-22

**APXV1 v1.1.0** — voice privacy suite, Tier A/B ceremony transparency, entity propagation fix for ZK proofs.

### Added

- `agents/voice/` — voice privacy pipeline (simulated STT/TTS for CI; local Vosk + pyttsx3 via `[voice]` extras)
- `scripts/setup_voice.py`, `scripts/run_voice_demo.py` — offline Vosk model setup and standalone demo
- `run_apx.py` flags: `--voice-file`, `--voice-transcript`, `--voice-mode`, `--voice-synthesize`
- `voice-redaction` entity proof wired in dual attestation when `voice_session` is present
- `scripts/ceremony_transcript.py` — Tier A/B ceremony transcript (manifest aggregation + optional Ed25519 signature)
- `scripts/export_verifier_bundle.py` — publishable VK-only bundle for third-party verification
- `docs/cryptography/CEREMONY.md` — ceremony tiers and trust model
- Tests: `tests/test_voice_suite.py`, `tests/test_voice_e2e.py`, `tests/test_ceremony_transcript.py`

### Fixed

- Agent 2 now propagates `entities[]` into proposed artifacts (fixes `redaction-v1` proofs for multi-entity voice/text inputs)
- Entity ZK bridge skips category-only `redactions_applied` summaries when building commitments
- `apx-zk` `json_fr` parser: bare decimal Merkle roots no longer misread as hex byte blobs (fixes `batch-merkle` for two-entity documents)
- CI: run doctor/integrity before pytest to avoid audit-chain pollution on shared runners
- Linux CI: `run_with_timeout` no longer uses `signal.alarm` (breaks sub-second float timeouts on Ubuntu)
- API server tests wait for `/health` instead of a fixed sleep (fewer flakes on slow runners)
- Manifest rebuild no longer rewrites timestamps when key hashes are unchanged

### Changed

- `apx_doctor` validates ceremony transcript when `managed/config/ceremony-transcript.json` exists
- CI installs `[dev,voice]`, runs ceremony write/verify, sets `APX_VOICE_MODE=simulated`
- `scripts/rust_bins.py` — shared binary-first resolver for `apx-circuits` and `apx-zk`
- Rust `[profile.release]` moved to workspace root (removes per-crate profile warnings)

### Security

- Documented trust model: self-hosters trust themselves; verifying release artifacts trusts publisher setup (single-party Groth16)
- Verifier bundle exports VKs only; reference `.pk`/`.vk` ship in-repo for clone-and-run — re-run setup to use your own proving keys

## [1.0.1] - 2026-06-20

### Fixed

- Windows: entity ZK prove/verify no longer fails when `apx-zk.exe` is locked (use release binary instead of `cargo run`)
- `--encrypt` no longer crashes final attestation summary (`KeyError: 'output'`)
- `verify_attestation --real-zk` decrypts E2EE artifacts locally for Python-side checks

### Changed

- Re-recorded `apxv1-demo.mp4` (~2 min): dual-track ZK attestation, independent verify, optional E2EE
- Updated `docs/assets/apxv1-demo-thumb.jpg`

## [1.0.0] - 2026-06-20

**APXV1 v1.0.0** — adds native privacy layer: redaction engine v3, optional E2EE, and dual-track ZK attestation. Governance spine unchanged.

### Added

- `agents/redaction/` — APXRedactionEngine v3 with format-aware parsing, Unicode armor, and 68+ regex patterns
- `agents/encryption_engine.py` — `APXE2EE` (X25519 + XSalsa20-Poly1305); optional `--encrypt` on `run_apx.py`
- `rust/apx-zk/` — 8 entity Groth16 circuits (Poseidon Merkle, redaction-v1, compliance, threat, etc.)
- `agents/zk/` — dual ZK bridge: governance proofs (Track A) + entity proofs (Track B) in one attestation bundle
- `scripts/setup_entity_zk.py` — one-time entity circuit trusted setup
- Tests: redaction matrix, encryption round-trip, entity bundle E2E (`tests/test_zk_entity_bundle.py`)


### Changed

- Rust layout: workspace with `apx-circuits` (governance) and `apx-zk` (entity) sibling crates
- `run_apx.py --attest` produces dual proofs; `verify_attestation.py --real-zk` verifies both tracks
- Governance keys: `rust/apx-circuits/keys/`; entity keys: `rust/apx-zk/keys/`
- CI: workspace `cargo build` + `cargo test` for both crates; full pytest suite
- Version bump from 0.3.0 → 1.0.0 across package and documentation

### Security

- Repository naming and public docs aligned with APXV1; local-only reference material stays out of tracked source
- E2EE keypair at `managed/config/e2ee-keypair.json` (gitignored)
- Separate VK manifests for governance and entity circuits

## [0.3.0] - 2026-06-17

First public open-source release of **APXV1** (*Attested Proof Execution Verified*, 1st generation) — Apache 2.0.

### Added

- One-command install scripts: `scripts/install.ps1`, `scripts/install.sh`
- `scripts/apx_doctor.py` — prerequisite and health checker
- `scripts/setup_first_run.py` — ZK setup on by default (optional skip removed in v1.3.0)
- `scripts/apx_ctl.py` — `api-key create|list` and administration commands
- Local HTTP API (`scripts/apx_serve.py`) with localhost binding; Docker bind via `APX_CONTAINER_BIND=1`
- Pluggable `LLMBackend` interface and `examples/llm-ollama/`
- Examples: `examples/hello-agent/`, `examples/api-client/`
- Docker image and `docker-compose.yml` (pre-v1.3.0: image-embedded ZK keys; removed in v1.3.0 sovereign trust)
- Documentation: `docs/QUICKSTART.md`, `docs/BUILDING.md`, `docs/INSTALL-RUST.md`, `docs/DOCKER.md`, deployment runbooks
- CI workflow: `.github/workflows/ci.yml` (pytest, Rust build, setup, doctor, integrity)
- Legal and hygiene: `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, expanded `.gitignore`

### Changed

- README repositioned as an air-gapped **platform foundation** for builders (not a finished consumer product)

- `agents/llm_reasoner.py` refactored to use `LLMBackend`

### Fixed

- `apx_serve.py` no longer starts the server twice when `--bind` / `--port` are passed (Docker crash loop)
- Docker Rust toolchain bumped to 1.85 for Cargo.lock v4 compatibility
- ZK keys generated in Rust build stage and copied into runtime image
- `examples/api-client/run_pipeline.py` health check uses `status` / `integrity.healthy`

### Security

- Runtime secrets (API keys, signing keys, E2EE keypair, ceremony transcript) excluded from version control via `.gitignore`
- Reference ZK `.pk`/`.vk` committed for out-of-box attest; re-run setup to use your own keys

[1.3.1]: https://github.com/APXV-Official/APXV/releases/tag/v1.3.1
[1.3.0]: https://github.com/APXV-Official/APXV/releases/tag/v1.3.0
[1.2.5]: https://github.com/APXV-Official/APXV/releases/tag/v1.2.5
[1.2.2]: https://github.com/APXV-Official/APXV/releases/tag/v1.2.2
[1.2.1]: https://github.com/APXV-Official/APXV/releases/tag/v1.2.1
[1.2.0]: https://github.com/APXV-Official/APXV/releases/tag/v1.2.0
[1.1.2]: https://github.com/APXV-Official/APXV/releases/tag/v1.1.2
[1.1.1]: https://github.com/APXV-Official/APXV/releases/tag/v1.1.1
[1.1.0]: https://github.com/APXV-Official/APXV/releases/tag/v1.1.0
[1.0.1]: https://github.com/APXV-Official/APXV/releases/tag/v1.0.1
[1.0.0]: https://github.com/APXV-Official/APXV/releases/tag/v1.0.0
[0.3.0]: https://github.com/APXV-Official/APXV/releases/tag/v0.3.0