# APXV Roadmap

**Last updated:** 2026-07-20

This is our **direction** — not a fixed calendar. Shipped detail lives in [CHANGELOG.md](CHANGELOG.md).

---

## North star

**APXV™ is a local workshop where you build agents, packs, and proofs into pipelines — and compose those pipelines into swarms — with attestations you can verify without re-running.**

| Layer | What it means |
|-------|----------------|
| **Atoms** | **Agents** (workers), **packs** (governance + vertical logic), **proof profiles** (what a run must claim) |
| **Pipeline** | Ordered composition of atoms — run locally, artifacts + optional claim/attest |
| **Composition** | Pipelines that call or hand off to other pipelines (multi-pack, multi-stage jobs) |
| **Swarm** | A system of linked pipelines treated as one governed unit to run and audit |
| **Ecosystem** | Optional share/import path (signed packs, later registry) — **not** required for local endgame |

Everything stays **on your machine**: sovereign keys, air-gapped API, no telemetry, no cloud trust boundary.

---

## Composition ladder (honest status)

| Stage | Operator can… | Status |
|-------|----------------|--------|
| **1 — Atoms** | Install/run official packs; attest + verify | **Shipped** (v1.3+) |
| **2 — Author packs** | Create packs via wizard without editing core Python | **Shipped** (v1.4) |
| **3 — Workshop** | Author agents, packs, and proof profiles in **Studio**; assemble and run on **Workbench**; **Trust** hub | **Shipped** (v1.5 — current) |
| **4 — Composition** | First-class pipeline→pipeline wiring, deeper multi-pack, stronger Workbench composition | **Next** |
| **5 — Swarms** | First-class swarms: group pipelines, run/monitor as one system, audit/proof across the set | **Later** (after composition is solid) |
| **6 — Ecosystem** | Publish guide + optional community registry tier | **Later** (parallel or after 4–5) |

Early runtime support for nested pipelines / swarm-shaped APIs may exist; the **product story and operator UX** for composition and swarms are not “done” until the table says so.

---

## Shipped (v1.5.0 — current)

**Workshop foundation** — one operator loop from authoring to verified claims.

- **Studio** — Agents, Packs, Proof Profiles (Save → Test → Promote)
- **Workbench** — shelf, board, proof profile bind, Run
- **Trust hub** — Verify, Audit, Governance
- **Proof Profiles** — catalog predicates; optional **universal-predicate-v1** Groth16 when keys exist
- Pack wizard remains **advanced** at `/packs?wizard=1`
- Desktop installers: Windows MSI/NSIS, Linux deb/AppImage; first launch runs **sovereign bootstrap**

Migration: [docs/MIGRATION-v1.5.md](docs/MIGRATION-v1.5.md) · Proofs: [docs/PROOF-STUDIO.md](docs/PROOF-STUDIO.md)

### Earlier releases

| Version | Theme |
|---------|--------|
| **v1.4.0** | Pack authoring wizard, on-ramp, legacy cut, entity circuit trim |
| **v1.3.x** | Sovereign bootstrap, desktop, API v2, Pack Studio run/clone, three official packs |

Full history: [CHANGELOG.md](CHANGELOG.md).

---

## Where we're headed

### Next (composition depth)

- Pipeline→pipeline composition as a first-class operator path (not only examples)
- Multi-pack clarity when a job spans more than one pack
- Workbench and API polish for multi-step / nested runs
- Broader Proof Profile catalog where packs need it
- Packaging polish; **macOS DMG** if bandwidth allows

### Later (swarms + ecosystem)

- **Swarms** — systems of pipelines: define, run, monitor, and audit as a unit
- Community pack **registry** tier and publishing guide (“Built with APXV”)
- Optional LLM-assisted intent mapping (catalog remains fail-closed; never the only path)

### Deferred circuits

- `normalization` / `threat` entity modules — only if a shipped pack requires them ([CIRCUITS.md](docs/cryptography/CIRCUITS.md))

---

## What we're not building

- Cloud SaaS or hosted multi-tenant APXV
- HIPAA / SOC2 / GDPR **certification claims**
- A bundled LLM or “magic compliance” product
- Proofs that LLM output was “correct” (proofs bind **policy + hashes**, not model truth)
- Arbitrary user-authored R1CS circuits in the operator UI
- Free-form cyclic agent graphs with no governance model (composition stays governed)

---

## Links

- [CHANGELOG.md](CHANGELOG.md) · [README.md](README.md) · [docs/MIGRATION-v1.5.md](docs/MIGRATION-v1.5.md) · [docs/DOWNLOADS.md](docs/DOWNLOADS.md) · [ui/docs/OPERATOR-GUIDE.md](ui/docs/OPERATOR-GUIDE.md)
