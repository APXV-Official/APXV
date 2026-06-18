# APX v1 — Open Source Release

This document tracks OSS release readiness for APX v1.

## Positioning

> Open-source, air-gapped governed agent runtime with cryptographic attestation.

APX is a **platform foundation** for developers and companies to build local, privacy-preserving agent systems — not a certified compliance product.

## Release Checklist

### Legal & Hygiene
- [x] `LICENSE` (Apache 2.0)
- [x] `.gitignore` (runtime state, keys, secrets)
- [x] `CONTRIBUTING.md`
- [x] `SECURITY.md` (threat model)
- [x] `CHANGELOG.md`

### Usability (Path C)
- [x] `scripts/install.ps1` + `scripts/install.sh`
- [x] `scripts/apx_doctor.py`
- [x] `scripts/setup_first_run.py` (ZK on by default)
- [x] `docs/QUICKSTART.md`
- [x] `docs/INSTALL-RUST.md`
- [x] `docs/DOCKER.md`
- [x] `docs/BUILDING.md`
- [x] `apx_ctl api-key create|list` + hint files
- [x] `examples/hello-agent/`
- [x] `examples/api-client/`
- [x] `examples/llm-ollama/` + `LLMBackend` interface

### Verification (re-run before push)
- [x] `python -m pytest tests/` (51 tests)
- [x] Clean fresh-clone install (`install.ps1` → HEALTHY)
- [x] Examples on fresh install (hello-agent, api-client)
- [x] Docker fresh volumes → `/health` returns `"status": "healthy"`
- [x] `git add -n .` — no secrets staged
- [ ] Record demo video (manual — follow `docs/DEMO-SCRIPT.md`)

### CI
- [x] `.github/workflows/ci.yml`

### Pre-Publish (Manual)
- [ ] Update `pyproject.toml` + `CHANGELOG.md` GitHub URLs to your repo
- [ ] GitHub repository + `v0.3.0` tag
- [ ] Maintainer go-ahead → first commit and push

## Quickstart

**Windows:** `.\scripts\install.ps1`  
**macOS/Linux:** `./scripts/install.sh`

Or step by step:

```bash
pip install -e ".[dev]"
python -m scripts.setup_first_run
python -m scripts.apx_doctor
python -m scripts.apx_serve
```

On Windows, prefer `python -m scripts.*` if `scripts` are not on PATH.

## What to Back Up

- `managed/`
- `rust/keys/`

## License

Apache License 2.0