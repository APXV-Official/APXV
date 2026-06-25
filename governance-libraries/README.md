# Governance libraries

Reusable governance artifacts and official agent packs for APXV1.

## Official agent pack

| Pack | Version | Description |
|------|---------|-------------|
| [apxv-pack-reference-redaction/](apxv-pack-reference-redaction/) | 0.1.0 | Reference redaction → orchestration → attestation vertical |

An **agent pack** includes governance, install steps, a runnable demo, capability notes, and an acceptance checklist. Agents for the reference pack ship in APXV1 core; the pack binds governance to those agents.

Install: see each pack's `README.md` and `ACCEPTANCE.md`.

## Governance templates (not packs)

| Template | Description |
|----------|-------------|
| [ai-governance-template/](ai-governance-template/) | Starter rules, workflow, and knowledge for LLM/tool agents |

Templates are **markdown starters** — copy into `managed/` via the governance approval workflow and customize. They do not include agents, `pack.yaml`, or acceptance tests. A future **AI Governance Pack** will add those pieces.

## Build your own

See [docs/BUILDING.md](../docs/BUILDING.md) for custom agents and governance. Official pack layout follows Pack Spec v0.1 (maintained in operator tooling, not published as a whole).