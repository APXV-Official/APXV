# APXV Roadmap

**Last updated:** 2026-07-20

APXV is a local governed runtime. Verticals ship as **agent packs** on top. This is our direction — not a fixed timeline. See [CHANGELOG.md](CHANGELOG.md) for what has shipped.

## Shipped (v1.5.0 — current)

**v1.5.0 — Studio, Workbench, and Proof Profiles** — one operator loop from authoring to verified claims.

- **Studio** — author Agents, Packs, and Proof Profiles (Save → Test → Promote)
- **Workbench** — freeform board, building-block shelf, optional wires, Run
- **Trust hub** — Verify, Audit, and Governance in one place
- **Proof Profiles** — catalog predicates for run claims; optional **universal-predicate-v1** Groth16 when keys are configured
- **Honest scope** — customize *what is proven*, not free-form circuit equations in the browser
- Migration: [docs/MIGRATION-v1.5.md](docs/MIGRATION-v1.5.md) · Proofs: [docs/PROOF-STUDIO.md](docs/PROOF-STUDIO.md)

## Shipped (v1.4.0)

**v1.4.0 — author packs + cut legacy** — Pack Studio authoring wizard, on-ramp copy, remove pre-v1.3 shims, trim unused entity circuits from default keygen.

- Pack wizard (`/packs?wizard=1`); still available as an **advanced** path in v1.5
- Legacy cut — `apxv_*` / `APXV_*` only; [MIGRATION-v1.4.md](docs/MIGRATION-v1.4.md)
- ZK trim — `normalization` + `threat` removed from default sovereign entity keygen (sources retained); [CIRCUITS.md](docs/cryptography/CIRCUITS.md)

## Shipped (v1.3.3)

**v1.3.3 Windows desktop hotfix** — start/stop/restart/quit reliably manages `:8741` on Windows (Linux path largely shipped in v1.3.2).

## Shipped (v1.3.2 – v1.3.0)

Sovereign bootstrap, desktop installers (Windows + Linux), API v2, jobs SSE, artifact reports, three official packs. See [CHANGELOG.md](CHANGELOG.md).

## Where we're headed

### Next

- Broader Proof Profile catalog where packs need it
- Packaging polish (desktop installers, docs front door)
- macOS DMG if bandwidth allows

### Later

- Community pack registry tier and publishing guide
- Optional LLM-assisted intent mapping (catalog remains fail-closed; never the only path)

### Deferred circuits

- `normalization` / `threat` entity modules — only if a shipped pack needs them ([CIRCUITS.md](docs/cryptography/CIRCUITS.md))

## What we're not building

- Cloud SaaS or hosted APXV
- HIPAA / SOC2 / GDPR certification claims
- A bundled LLM or "magic compliance" product
- Proofs that the LLM output was "correct" (proofs bind policy + hashes)
- Arbitrary user-authored R1CS circuits in the operator UI

## Links

- [CHANGELOG.md](CHANGELOG.md) · [docs/MIGRATION-v1.5.md](docs/MIGRATION-v1.5.md) · [docs/DOWNLOADS.md](docs/DOWNLOADS.md)
