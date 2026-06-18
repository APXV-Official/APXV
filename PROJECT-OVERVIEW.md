# APXV1 — Project Guide

**APXV1** — *Attested Proof Execution Verified* — **1st-generation** governed agent platform.

**Version:** 0.3.0 · **License:** Apache 2.0

This guide describes the repository layout, core components, and where to find operator documentation. For a quick start, see [README.md](README.md) and [docs/QUICKSTART.md](docs/QUICKSTART.md).

---

## What APXV1 Provides

APXV1 is a **local, air-gapped platform** for building governed agent systems. Code modules use the `APX` prefix internally; the product name is **APXV1**.

| Capability | Description |
|------------|-------------|
| **Governance specs** | Rules, workflows, and knowledge as markdown under `managed/` |
| **Signed capabilities** | Per-agent permissions in `managed/config/capabilities.json` |
| **Audit chain** | Chained logs for system and agent events |
| **Artifact store** | SQLite index + content-addressable blobs |
| **Approval workflow** | Propose → approve → apply for governance changes |
| **ZK attestation** | Groth16 proofs binding execution to rule hashes |
| **Local API** | HTTP on `127.0.0.1:8741` — no cloud, no telemetry |
| **Pluggable LLMs** | Optional backends (Ollama example included) |

APXV1 is a **foundation for builders** — not a finished consumer product and not HIPAA/SOC2/GDPR certified. See [SECURITY.md](SECURITY.md) for the threat model.

---

## Release Status

| Milestone | Status |
|-----------|--------|
| Cryptography & ZK attestation | Complete |
| Governed runtime core | Complete |
| Onboarding & packaging | Complete (install scripts, doctor, Docker, examples, CI) |
| Current release | **v0.3.0** |

The reference 3-agent pipeline (redact → orchestrate → attest) and Groth16 verification path are implemented and covered by automated tests.

---

## Repository Layout

### Runtime (`agents/`)

| Component | File(s) | Role |
|-----------|---------|------|
| Reference pipeline | `agent1.py` … `agent3.py` | Redaction, orchestration, attestation |
| Runtime | `runtime.py` | Store, audit, capabilities, governance |
| Local API | `local_api.py` | Auth, jobs, pipeline, health |
| LLM integration | `llm_backend.py`, `llm_reasoner.py` | Pluggable model backends |
| Policy & governance | `capability_policy.py`, `governance_approval.py` | Signed policy and spec approval |

### Cryptography (`rust/`)

| Component | Role |
|-----------|------|
| `circuits/` | Groth16 circuits: redaction, rule-binding, pipeline |
| `src/main.rs` | `apx-circuits` prover CLI |
| `keys/` | Per-deployment `.pk`/`.vk` (gitignored); `manifest.json` committed |

### Operator tooling (`scripts/`)

| Command | Purpose |
|---------|---------|
| `install.ps1` / `install.sh` | Cross-platform install |
| `setup_first_run.py` | First-run setup (ZK enabled by default) |
| `apx_doctor.py` | Prerequisites and health check |
| `apx_ctl.py` | Integrity, API keys, governance, backups |
| `run_apx.py` | Full pipeline (`--attest` for ZK) |
| `apx_serve.py` | Local HTTP API |

### Examples & templates

| Path | Purpose |
|------|---------|
| `examples/hello-agent/` | Minimal custom governed agent |
| `examples/api-client/` | Python API client |
| `examples/llm-ollama/` | Local LLM via Ollama |
| `governance-libraries/` | Reusable governance templates |

### Deployment

| Asset | Notes |
|-------|-------|
| `Dockerfile` | Rust 1.85; ZK keys baked at build |
| `docker-compose.yml` | Port 8741; use fresh volumes for clean deploys |
| `docs/AIR-GAP-INSTALL.md` | Offline installation |

---

## Quality Assurance

| Check | Coverage |
|-------|----------|
| Unit & integration tests | `tests/` (51 tests) |
| CI | `.github/workflows/ci.yml` — pytest, Rust build, setup, doctor, integrity |
| Independent ZK verify | `python -m scripts.verify_attestation --real-zk` |

If `apx_doctor` reports a broken audit chain on a long-lived dev tree, reset local audit state and re-run setup:

```bash
# Remove polluted audit logs, then:
python -m scripts.setup_first_run
```

Fresh installs and CI environments should report **HEALTHY** without this step.

---

## Documentation Index

| Document | Audience |
|----------|----------|
| [README.md](README.md) | Overview and quick links |
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | First install and verify |
| [docs/BUILDING.md](docs/BUILDING.md) | Custom agents, API, LLMs |
| [docs/LOCAL-API.md](docs/LOCAL-API.md) | HTTP API reference |
| [docs/DOCKER.md](docs/DOCKER.md) | Container deployment |
| [docs/AIR-GAP-INSTALL.md](docs/AIR-GAP-INSTALL.md) | Offline install |
| [docs/INSTALL-RUST.md](docs/INSTALL-RUST.md) | Rust toolchain |
| [docs/cryptography/](docs/cryptography/) | ZK setup and verification |
| [SECURITY.md](SECURITY.md) | Threat model |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |
| [CHANGELOG.md](CHANGELOG.md) | Release history |
| [RUNBOOKS/](RUNBOOKS/) | Deployment and operations |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Bug reports should include output from `python -m scripts.apx_doctor` and steps to reproduce.