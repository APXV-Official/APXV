# Changelog

All notable changes to APXV1 are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-06-22

**APXV1 v1.1.0** — public launch: voice privacy suite, Tier B ceremony transparency, entity propagation fix for ZK proofs.

### Added

- `agents/voice/` — voice privacy pipeline (simulated STT/TTS for CI; local Vosk + pyttsx3 via `[voice]` extras)
- `scripts/setup_voice.py`, `scripts/run_voice_demo.py` — offline Vosk model setup and standalone demo
- `run_apx.py` flags: `--voice-file`, `--voice-transcript`, `--voice-mode`, `--voice-synthesize`
- `voice-redaction` entity proof wired in dual attestation when `voice_session` is present
- `scripts/ceremony_transcript.py` — Tier A/B ceremony transcript (manifest aggregation + optional Ed25519 signature)
- `scripts/export_verifier_bundle.py` — publishable VK-only bundle for third-party verification
- `docs/cryptography/CEREMONY.md` — ceremony tiers, trust model, operator workflow
- Tests: `tests/test_voice_suite.py`, `tests/test_voice_e2e.py`, `tests/test_ceremony_transcript.py`

### Fixed

- Agent 2 now propagates `entities[]` into proposed artifacts (fixes `redaction-v1` proofs for multi-entity voice/text inputs)
- Entity ZK bridge skips category-only `redactions_applied` summaries when building commitments
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

- Documented trust model: self-hosters trust themselves; verifying operator releases trusts operator setup (not MPC/PoT)
- Verifier bundle exports VKs only — proving keys remain operator-local

## [1.0.1] - 2026-06-20

### Fixed

- Windows: entity ZK prove/verify no longer fails when `apx-zk.exe` is locked (use release binary instead of `cargo run`)
- `--encrypt` no longer crashes final attestation summary (`KeyError: 'output'`)
- `verify_attestation --real-zk` decrypts E2EE artifacts locally for Python-side checks

### Changed

- Re-recorded `apxv1-demo.mp4` (~2 min): dual-track ZK attestation, independent verify, optional E2EE
- Updated `docs/assets/apxv1-demo-thumb.jpg`

## [1.0.0] - 2026-06-20

**APXV1 v1.0.0** — privacy migration complete (Phases 0–4). Governance spine unchanged; native redaction, optional E2EE, and dual-track ZK attestation added.

### Added

- `agents/redaction/` — APXRedactionEngine v3 with format-aware parsing, Unicode armor, and 68+ regex patterns
- `agents/encryption_engine.py` — `APXE2EE` (X25519 + XSalsa20-Poly1305); optional `--encrypt` on `run_apx.py`
- `rust/apx-zk/` — 8 entity Groth16 circuits (Poseidon Merkle, redaction-v1, compliance, threat, etc.)
- `agents/zk/` — dual ZK bridge: governance proofs (Track A) + entity proofs (Track B) in one attestation bundle
- `scripts/setup_entity_zk.py` — one-time entity circuit trusted setup
- Tests: redaction matrix, encryption round-trip, entity bundle E2E (`tests/test_zk_entity_bundle.py`)
- Migration plan and baseline docs under `docs/migration/`

### Changed

- Rust layout: workspace with `apx-circuits` (governance) and `apx-zk` (entity) sibling crates
- `run_apx.py --attest` produces dual proofs; `verify_attestation.py --real-zk` verifies both tracks
- Governance keys: `rust/apx-circuits/keys/`; entity keys: `rust/apx-zk/keys/`
- CI: workspace `cargo build` + `cargo test` for both crates; full pytest suite
- Version bump from 0.3.0 → 1.0.0 across package and operator docs

### Security

- Legacy vendor naming removed from tracked source; reference folders remain gitignored
- E2EE keypair at `managed/config/e2ee-keypair.json` (gitignored)
- Separate VK manifests for governance and entity circuits

## [0.3.0] - 2026-06-17

First public open-source release of **APXV1** (*Attested Proof Execution Verified*, 1st generation) — Apache 2.0.

### Added

- One-command install scripts: `scripts/install.ps1`, `scripts/install.sh`
- `scripts/apx_doctor.py` — prerequisite and health checker
- `scripts/setup_first_run.py` — ZK setup on by default (`--skip-zk` optional)
- `scripts/apx_ctl.py` — `api-key create|list` and operator commands
- Local HTTP API (`scripts/apx_serve.py`) with localhost binding; Docker bind via `APX_CONTAINER_BIND=1`
- Pluggable `LLMBackend` interface and `examples/llm-ollama/`
- Examples: `examples/hello-agent/`, `examples/api-client/`
- Docker image and `docker-compose.yml` with baked ZK keys at build time
- Documentation: `docs/QUICKSTART.md`, `docs/BUILDING.md`, `docs/INSTALL-RUST.md`, `docs/DOCKER.md`, operator runbooks
- CI workflow: `.github/workflows/ci.yml` (pytest, Rust build, setup, doctor, integrity)
- Legal and hygiene: `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, expanded `.gitignore`

### Changed

- README repositioned as an air-gapped **platform foundation** for builders (not a finished consumer product)
- Stale planning docs archived under `docs/archive/`
- `agents/llm_reasoner.py` refactored to use `LLMBackend`

### Fixed

- `apx_serve.py` no longer starts the server twice when `--bind` / `--port` are passed (Docker crash loop)
- Docker Rust toolchain bumped to 1.85 for Cargo.lock v4 compatibility
- ZK keys generated in Rust build stage and copied into runtime image
- `examples/api-client/run_pipeline.py` health check uses `status` / `integrity.healthy`

### Security

- Runtime secrets (API keys, signing keys, ZK `.pk`/`.vk`) excluded from version control via `.gitignore`
- Maintainer-only paths gitignored (`docs/internal/`, `docs/resume/`)

[1.1.0]: https://github.com/apxv1dev/APXV1/releases/tag/v1.1.0
[1.0.1]: https://github.com/apxv1dev/APXV1/releases/tag/v1.0.1
[1.0.0]: https://github.com/apxv1dev/APXV1/releases/tag/v1.0.0
[0.3.0]: https://github.com/apxv1dev/APXV1/releases/tag/v0.3.0