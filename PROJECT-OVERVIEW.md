# APXV1 — Project Overview & Current Status

**APXV1** — *Attested Proof Execution Verified* — **1st-generation** governed agent platform.

**Last updated:** 2026-06-18  
**Version:** 0.3.0  
**License:** Apache 2.0

Use this file as your “where am I?” map. For push gates, see [docs/PUBLISH-READINESS.md](docs/PUBLISH-READINESS.md).

---

## What APXV1 Is

**APXV1 is a local, air-gapped platform for building governed agent systems** — the first shipped generation of the APX engine (code modules still use the `APX` prefix internally).

- Rules, workflows, and knowledge live in **markdown** under `managed/`
- Agents run under a **signed capability policy** (what each agent may do)
- Every action is recorded in **chained audit logs**
- Outputs are **immutable artifacts** (SQLite + content-addressable storage)
- Rule changes go through **propose → approve → apply**
- **Groth16 ZK proofs** bind execution to rule hashes (real circuits, not mock)
- **Local HTTP API** on `127.0.0.1:8741` — no cloud, no telemetry
- **LLMs are pluggable** (Ollama example) — not bundled

**Positioning:** Platform **foundation for builders** (solo devs + small companies self-hosting). Not a finished consumer product. Not HIPAA/SOC2/GDPR certified.

---

## Where You Are Now

| Layer | Status |
|-------|--------|
| **Phase 1 — Cryptography** | Complete ([PHASE1-STATUS.md](PHASE1-STATUS.md)) |
| **Phase 2 — Governed core** | Complete ([PHASE2-STATUS.md](PHASE2-STATUS.md)) |
| **Path C — OSS onboarding** | Complete (install, doctor, quickstart, Docker, examples, CI) |
| **Release readiness** | **Technically ready** — manual steps remain before public push |
| **Git** | Pushed to `apxv1dev/APXV1` (private) |

**Bottom line:** You have a working, verifiable, documentable OSS project. You are in **“hold for launch”** mode, not **“still building core”** mode.

---

## What You Have (Inventory)

### Runtime & agents
| Piece | Location | Notes |
|-------|----------|-------|
| 3-agent reference pipeline | `agents/agent1.py` … `agent3.py` | Redact → orchestrate → attest |
| Unified runtime | `agents/runtime.py` | Store, audit, capabilities, governance |
| Local API server | `agents/local_api.py`, `scripts/apx_serve.py` | Auth, jobs, pipeline, health |
| Pluggable LLM | `agents/llm_backend.py`, `agents/llm_reasoner.py` | Ollama example in `examples/llm-ollama/` |
| Capability policy | `agents/capability_policy.py` | Ed25519-signed local policy |
| Governance approval | `agents/governance_approval.py` | Propose / approve / apply |

### Cryptography (Rust)
| Piece | Location | Notes |
|-------|----------|-------|
| Groth16 circuits (3) | `rust/circuits/` | redaction, rule-binding, pipeline |
| Prover CLI | `rust/src/main.rs` | `apx-circuits` |
| ZK keys | `rust/keys/` | `.pk`/`.vk` gitignored; `manifest.json` committed |
| Setup & verify scripts | `scripts/setup_zk.py`, `scripts/verify_attestation.py` | `--real-zk` for independent verify |

### Operator tooling
| Command | Purpose |
|---------|---------|
| `scripts/install.ps1` / `install.sh` | One-command install + setup + doctor + pipeline |
| `scripts/setup_first_run.py` | First-run setup (ZK on by default) |
| `scripts/apx_doctor.py` | Prerequisites + health check |
| `scripts/apx_ctl.py` | Integrity, API keys, governance, backups |
| `scripts/run_apx.py` | Full pipeline (`--attest` for ZK) |

### Examples & templates
| Path | Purpose |
|------|---------|
| `examples/hello-agent/` | Minimal custom governed agent |
| `examples/api-client/` | Call local API from Python |
| `examples/llm-ollama/` | Local LLM via Ollama |
| `governance-libraries/` | Reusable rule/workflow/knowledge templates |

### Deployment
| Piece | Location |
|-------|----------|
| Docker image | `Dockerfile` (Rust 1.85, ZK keys baked at build) |
| Compose | `docker-compose.yml` (port 8741, fresh volumes recommended) |
| Air-gap guide | `docs/AIR-GAP-INSTALL.md` |

### Legal & hygiene
| File | Purpose |
|------|---------|
| `LICENSE` | Apache 2.0 |
| `CONTRIBUTING.md` | How to contribute |
| `SECURITY.md` | Threat model (what APXV1 does / does not protect) |
| `CHANGELOG.md` | v0.3.0 release notes (update GitHub URLs before push) |
| `.gitignore` | Runtime state, keys, `docs/resume/`, operator key hints |

### Tests & CI
| Piece | Status |
|-------|--------|
| `tests/` | **51 tests passing** |
| `.github/workflows/ci.yml` | pytest, Rust build, setup, doctor, integrity |

### Docs map (start here)
| Doc | When to read |
|-----|--------------|
| [README.md](README.md) | Public face of the project |
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | 15-minute getting started |
| [docs/BUILDING.md](docs/BUILDING.md) | How to build agents, API, LLMs on APXV1 |
| [docs/LOCAL-API.md](docs/LOCAL-API.md) | API reference |
| [docs/DOCKER.md](docs/DOCKER.md) | Company Docker deploy |
| [docs/DEMO-SCRIPT.md](docs/DEMO-SCRIPT.md) | ~2 min demo video script |
| [docs/PUBLISH-READINESS.md](docs/PUBLISH-READINESS.md) | Pre-push checklist |
| [docs/MARKET-LANDSCAPE.md](docs/MARKET-LANDSCAPE.md) | Competitors, overlap, positioning |
| [docs/open-source/README.md](docs/open-source/README.md) | OSS release tracker |

---

## What’s Been Verified

| Check | Result | Where |
|-------|--------|-------|
| pytest (51) | Pass | Source repo |
| Fresh-clone install | Pass → HEALTHY | `%TEMP%\apx-release-rehearsal` |
| `hello-agent` example | Pass | Rehearsal clone |
| `api-client` example | Pass | Rehearsal clone + API key |
| Docker fresh volumes | Pass → `"status": "healthy"` | Temp managed dir, no polluted audit |
| Secrets audit (`git add -n .`) | Clean | No keys/runtime state staged |

**Dev machine caveat:** `apx_doctor` / `apx_ctl integrity` may **fail on this folder** because `managed/audit/` has history from local testing. That is environmental — **not a release blocker**. Fresh installs pass. Recovery: remove `managed/audit/` and re-run `python -m scripts.setup_first_run` (doctor prints this hint).

---

## What’s Left To Do

### Before first public push (you)

- [ ] **Record demo video** — follow [docs/DEMO-SCRIPT.md](docs/DEMO-SCRIPT.md)
- [x] **Create GitHub repo** — `https://github.com/apxv1dev/APXV1` (private; go public after inspection)
- [x] **GitHub URLs** — `apxv1dev/APXV1` across docs and metadata
- [x] **Push + verify** — commit, tag `v0.3.0`, pushed; confirm CI green

### After push (optional, same week)

- [ ] GitHub Release notes from `CHANGELOG.md`
- [ ] GitHub issue template (“paste `apx_doctor` output”)
- [ ] Link demo video in README / release

### Not required for OSS launch (future product work)

- Vertical UI / connectors (SharePoint, email, etc.)
- Stronger PII / DLP (beyond pattern redaction)
- Multi-tenant SaaS, hosted offering
- Compliance certifications (HIPAA, SOC2, etc.)
- On-chain verification (archived planning in `docs/archive/`)

---

## How Others Build On It (Quick Reference)

1. **Custom agent** — `examples/hello-agent/` + `docs/BUILDING.md`
2. **API integration** — `apx_serve` + `examples/api-client/`
3. **Local LLM** — `LLMBackend` + `examples/llm-ollama/`
4. **Custom governance** — templates in `governance-libraries/`, apply via `apx_ctl governance-*`
5. **Company deploy** — Docker + fresh volumes per `docs/DOCKER.md`

---

## Portfolio vs Business (One Paragraph)

**Portfolio today:** Strong — rare combo of ZK, governance, audit, local API, OSS packaging. Release + demo = credible public artifact; adoption is a bonus.

**Business later:** Only if you **narrow to one vertical** (e.g. governed doc redaction for legal/health) and build product layer (UI, connectors, support) on top of APXV1 as engine IP. v0.3.0 alone is not a revenue product; it is optionality and credibility.

---

## Git State (as of last update)

```
Branch: main
Remote: apxv1dev/APXV1 (private)
Tag: v0.3.0
```

Rehearsal clone (disposable): `%TEMP%\apx-release-rehearsal`  
Docker test artifacts: `%TEMP%\apx-docker-managed-fresh` (safe to delete)

**Internal (gitignored):** `docs/internal/COMMERCIAL-RATE-SHEET.md` — US consulting rates; relocate before push if desired.

---

## One-Line Summary

**You built a real local governed-agent platform with ZK attestation; OSS packaging is done; you are one demo + GitHub URL + your go-ahead away from public v0.3.0.**