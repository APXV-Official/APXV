# Governance libraries

Reusable governance artifacts and official agent packs for APXV.

**Catalog:** [docs/PACK-CATALOG.md](../docs/PACK-CATALOG.md) · **Tutorial:** [docs/BUILD-YOUR-FIRST-PACK.md](../docs/BUILD-YOUR-FIRST-PACK.md)

## Official agent pack

| Pack | Version | Description |
|------|---------|-------------|
| [apxv-pack-reference-redaction/](apxv-pack-reference-redaction/) | 0.1.0 | Reference redaction → orchestration → attestation vertical |
| [apxv-pack-document-processing/](apxv-pack-document-processing/) | 0.1.0 | Batch `.txt` / `.json` folder ingest, manifest, compliance policy 2 |
| [apxv-pack-ai-governance/](apxv-pack-ai-governance/) | 0.1.0 | Redaction + `LLMReasoner` review, compliance policy 4 |

An **agent pack** includes governance, install steps, a runnable demo, capability notes, and an acceptance checklist. Agents ship in APXV core; each pack binds governance and pipeline logic to those agents.

Install: see each pack's `README.md` and `ACCEPTANCE.md`.

## Governance templates (not packs)

| Template | Description |
|----------|-------------|
| [ai-governance-template/](ai-governance-template/) | Starter rules, workflow, and knowledge for LLM/tool agents |

Templates are **markdown starters** — copy into `managed/` via the governance approval workflow and customize. They do not include agents, `pack.yaml`, or acceptance tests. For a full installable pack, use [apxv-pack-ai-governance/](apxv-pack-ai-governance/).

## Build your own

See [docs/BUILDING.md](../docs/BUILDING.md) for custom agents and governance. Official pack layout follows Pack Spec v0.1 (maintained in operator tooling, not published as a whole).