# Changelog

All notable changes to APXV1 are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-06-17

First public open-source release (Apache 2.0).

### Added

- One-command install scripts: `scripts/install.ps1`, `scripts/install.sh`
- `scripts/apx_doctor.py` — prerequisite and health checker
- `scripts/setup_first_run.py` — ZK setup on by default (`--skip-zk` optional)
- `scripts/apx_ctl.py` — `api-key create|list` and operator commands
- Local HTTP API (`scripts/apx_serve.py`) with localhost binding; Docker bind via `APX_CONTAINER_BIND=1`
- Pluggable `LLMBackend` interface and `examples/llm-ollama/`
- Examples: `examples/hello-agent/`, `examples/api-client/`
- Docker image and `docker-compose.yml` with baked ZK keys at build time
- Documentation: `docs/QUICKSTART.md`, `docs/BUILDING.md`, `docs/INSTALL-RUST.md`, `docs/DOCKER.md`, `docs/DEMO-SCRIPT.md`
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
- `docs/resume/` gitignored for local-only notes

[0.3.0]: https://github.com/apxv1dev/APXV1/releases/tag/v0.3.0