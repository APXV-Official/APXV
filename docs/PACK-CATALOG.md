# APXV Pack Catalog

Curated index of **official** agent packs shipped with APXV, plus guidance for **community** packs (documentation links only in v1.3 — no remote registry). Operator console v1.3.2 adds a **Build your first pack** on-ramp (duplicate reference pack + templates).

**Platform:** APXV runtime (`apxv` pip package, Docker image `apxv`)  
**Pack spec:** Pack Spec v0.1 (`pack.yaml` in each pack directory)  
**Catalog API:** `GET /api/v2/packs` · **CLI:** `python -m scripts.apxv_ctl pack list`

---

## Official packs (shipped in-repo)

These packs live under `governance-libraries/`. Core agents ship in APXV; each pack supplies governance, pipeline logic, demos, and acceptance tests.

| Pack ID | Name | Requires | Compliance (attest) | Summary |
|---------|------|----------|---------------------|---------|
| [`apxv-pack-reference-redaction`](../governance-libraries/apxv-pack-reference-redaction/) | Reference Redaction Pack | APXV ≥ 1.1.0 | Default (policy 1) | Governed text redaction → orchestration → attestation using core agents `APXV-AGENT-001` … `003` |
| [`apxv-pack-document-processing`](../governance-libraries/apxv-pack-document-processing/) | Document Processing Pack | APXV ≥ 1.2.0 | Policy **2** (batch ingest) | Batch `.txt` / `.json` folder processing, manifest, `compliance_policy_id=2` |
| [`apxv-pack-ai-governance`](../governance-libraries/apxv-pack-ai-governance/) | AI Governance Pack | APXV ≥ 1.2.0 | Policy **4** (LLM review) | Redaction + `LLMReasoner` review path, `compliance_policy_id=4` |

### Quick commands

```bash
# List packs (catalog + paths)
python -m scripts.apxv_ctl pack list

# Activate governance profile for a pack (rewrites managed/ rules, workflows, knowledge)
python -m scripts.apxv_ctl pack activate apxv-pack-document-processing

# Run pipeline for active or named pack
python -m scripts.apxv_ctl pack run --pack document --input-text "Contact alice@example.com" --attest

# One-shot demo (all official packs + attest + ZK verify)
python -m scripts.apxv_demo --pack all
```

**API (v2):**

```bash
curl -H "APXV-API-KEY: $APXV_API_KEY" http://127.0.0.1:8741/api/v2/packs
curl -X POST -H "APXV-API-KEY: $APXV_API_KEY" -H "Content-Type: application/json" \
  -d '{}' http://127.0.0.1:8741/api/v2/packs/apxv-pack-document-processing/activate
curl -H "APXV-API-KEY: $APXV_API_KEY" http://127.0.0.1:8741/api/v2/packs/active
```

See [LOCAL-API-V2.md](LOCAL-API-V2.md) and the operator console [OPERATOR-GUIDE.md](../../ui/docs/OPERATOR-GUIDE.md).

---

## Pack anatomy (Pack Spec v0.1)

Every pack directory includes:

| Artifact | Purpose |
|----------|---------|
| `pack.yaml` | Manifest: `pack_id`, agents, governance file lists, `policy_delta` |
| `governance/rules|workflows|knowledge/` | Markdown specs applied on activate |
| `agents/` | Pack pipeline (`run_pack_pipeline` or pack-specific agents) |
| `capabilities/policy-delta.json` | Optional capability grants for pack agents |
| `examples/run_pack_demo.py` | Runnable acceptance path |
| `ACCEPTANCE.md` | Operator checklist |

Official packs reuse **core agent IDs** (`APXV-AGENT-001` … `003`, `LLM-001`, etc.). Custom packs use `APXV-AGENT-CUSTOM-001` or pack-scoped module agents.

---

## Active pack profile (one at a time)

v1.3.0 enforces **one active governance profile** per instance (decision D8):

1. **Activate** copies pack governance into `managed/rules`, `managed/workflows`, `managed/knowledge`.
2. A **snapshot** of the previous profile is stored under `managed/pack-snapshots/<pack_id>/`.
3. `managed/config/active_pack.json` records the active pack, governance hashes, and activation time.

Switch packs via CLI, API, or **Pack Studio** in the operator console.

---

## Community packs (v1.3.0)

v1.3.0 does **not** ship a remote pack registry or download mechanism (air-gap aligned). Community packs are:

- Built and installed **locally** (copy into `governance-libraries/` or create via API/UI).
- Listed in **your** documentation or internal catalog — not pulled from APXV servers.

To publish a community pack:

1. Follow [BUILD-YOUR-FIRST-PACK.md](BUILD-YOUR-FIRST-PACK.md).
2. Keep `pack_id` prefixed with `apxv-pack-<slug>`.
3. Document install/activate steps in your pack `README.md` and `ACCEPTANCE.md`.
4. Optionally link your repo from your operator docs (not from this catalog until a community tier exists in v1.4+).

**Templates (not full packs):** [ai-governance-template](../governance-libraries/ai-governance-template/) — markdown starters only; copy via governance propose → approve → apply.

---

## Agent registry

Discover agents bound to packs and core runtime agents:

```bash
curl -H "APXV-API-KEY: $APXV_API_KEY" http://127.0.0.1:8741/api/v2/agents
curl -H "APXV-API-KEY: $APXV_API_KEY" \
  http://127.0.0.1:8741/api/v2/agents/APXV-AGENT-001/chain?pack=reference
```

---

## Related

| Doc | Topic |
|-----|--------|
| [BUILD-YOUR-FIRST-PACK.md](BUILD-YOUR-FIRST-PACK.md) | Create, activate, and run a custom pack |
| [BUILDING.md](BUILDING.md) | Custom agents and API integration |
| [MIGRATION-v1.3.md](MIGRATION-v1.3.md) | Upgrade from v1.2.5 (rename, API v2) |
| [governance-libraries/README.md](../governance-libraries/README.md) | In-repo pack index |