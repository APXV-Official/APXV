# Publish Readiness — Path C Checklist

**Do not push until the maintainer gives explicit go-ahead.**

## Path C deliverables

### Onboarding (solo dev + company)
- [x] `scripts/install.sh` + `scripts/install.ps1` (cross-platform)
- [x] `scripts/apx_doctor.py`
- [x] `docs/QUICKSTART.md`
- [x] `docs/INSTALL-RUST.md`
- [x] `docs/DOCKER.md`
- [x] `apx_ctl api-key create|list` + hint files

### Trust & hygiene
- [x] Stale planning docs moved to `docs/archive/`
- [x] `.github/workflows/ci.yml`
- [x] `docs/DEMO-SCRIPT.md` (record before/after launch)
- [ ] Record demo video (manual — follow DEMO-SCRIPT.md)

### Runtime verification (re-run before push)
- [x] `python -m pytest tests/ -v` (51 passed)
- [ ] `python -m scripts.apx_doctor` on dev machine (may fail from polluted audit — use fresh install)
- [x] Clean fresh-clone install simulation (`%TEMP%\apx-release-rehearsal` → HEALTHY)
- [x] Examples on rehearsal (`hello-agent`, `api-client` with API key)
- [x] Docker with fresh volumes → `/health` healthy
- [x] `git add -n .` — no secrets staged
- [x] `CHANGELOG.md` drafted (update GitHub URLs before push)

## Public positioning

> APXV1 is an open-source, air-gapped platform for building governed agent systems locally. Define rules in markdown, run agents under signed capabilities, and generate real Groth16 proofs. Bring your own agents and LLMs.

## Pre-push placeholders (replace before public launch)

- [x] GitHub issue template (`.github/ISSUE_TEMPLATE/`)
- [x] README community support + professional services boundaries
- [x] GitHub URLs → `apxv1dev/APXV1` (README, CHANGELOG, pyproject, issue template)
- [x] Maintainer contact → GitHub `@apxv1dev` · `apxv1dev@protonmail.com`

## After maintainer go-ahead

1. First commit + tag `v0.3.0`
2. Push to GitHub
3. Publish demo video
4. Monitor CI on first push