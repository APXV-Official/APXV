# Build Your First Agent Pack

A hands-on path from zero to a **runnable custom pack** on APXV v1.3.0. Time: ~30 minutes after `setup_first_run` is complete.

**You will:**

1. Scaffold a pack from the reference template
2. Implement `run_pack_pipeline` in `agents/custom_agents.py`
3. Activate the pack (governance profile switch)
4. Run the pipeline and inspect artifacts

**Prerequisites:** APXV installed (`pip install -e .` or `install.ps1`), `python -m scripts.setup_first_run` done, `python -m scripts.apxv_doctor` → HEALTHY.

---

## 1. Choose a pack ID

Pack IDs must match `apxv-pack-<slug>` (lowercase letters, numbers, hyphens):

```
apxv-pack-my-first-pack
```

---

## 2. Create the pack

### Option A — Operator console (recommended)

1. Start the runtime: `python -m scripts.apxv_serve`
2. Start the UI: from `ui/`, run `pnpm dev` → http://localhost:5173
3. Complete onboarding with your operator API key
4. Open **Agent packs** → **Create pack**
5. Choose **Reference** or **Minimal** template, enter pack ID and display name

### Option B — API v2

```bash
export APXV_API_KEY="<your-key>"

curl -X POST http://127.0.0.1:8741/api/v2/packs \
  -H "APXV-API-KEY: $APXV_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "pack_id": "apxv-pack-my-first-pack",
    "name": "My First Pack",
    "description": "Tutorial pack for governed redaction",
    "template": "reference"
  }'
```

### Option C — Clone an official pack (CLI)

```bash
python -m scripts.apxv_ctl pack clone apxv-pack-reference-redaction \
  apxv-pack-my-first-pack \
  --name "My First Pack" \
  --description "Cloned from reference pack"
```

The pack appears under `governance-libraries/apxv-pack-my-first-pack/`.

---

## 3. Edit pipeline logic

Open:

```
governance-libraries/apxv-pack-my-first-pack/agents/custom_agents.py
```

Implement `run_pack_pipeline(input_text, runtime, **kwargs)` — the entry point the runtime calls when this pack is active.

**Reference template** delegates to core agents (`RuleGovernedRedactor`, `WorkflowOrchestrator`, `AttestationCoordinator`). **Minimal template** includes a stub you replace.

Example (keep it simple for the tutorial):

```python
def run_pack_pipeline(input_text, runtime, **kwargs):
    from agents.agent1 import RuleGovernedRedactor
    from agents.agent2 import WorkflowOrchestrator
    from agents.agent3 import AttestationCoordinator

    redactor = RuleGovernedRedactor(runtime=runtime)
    orchestrator = WorkflowOrchestrator(runtime=runtime)
    coordinator = AttestationCoordinator(runtime=runtime)

    r1 = redactor.process_text(input_text or "")
    r2 = orchestrator.orchestrate(r1)
    attest = bool(kwargs.get("attest", False))
    return coordinator.coordinate(r2, attest=attest)
```

Adjust governance markdown under `governance/` if your vertical needs different rules (then use **Governance** in the UI or `apxv_ctl governance-*` to propose → approve → apply).

---

## 4. Activate the pack

Activation applies pack governance to `managed/` and records the active profile.

```bash
python -m scripts.apxv_ctl pack activate apxv-pack-my-first-pack
```

Or API:

```bash
curl -X POST http://127.0.0.1:8741/api/v2/packs/apxv-pack-my-first-pack/activate \
  -H "APXV-API-KEY: $APXV_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Verify:

```bash
curl -H "APXV-API-KEY: $APXV_API_KEY" http://127.0.0.1:8741/api/v2/packs/active
```

---

## 5. Run the pipeline

### CLI

```bash
python -m scripts.apxv_ctl pack run \
  --pack my-first-pack \
  --input-text "Email me at user@example.com" \
  --attest
```

(`--pack` accepts short keys like `reference`, `document`, `ai`, or full `apxv-pack-*` ids.)

### API v2

```bash
curl -X POST http://127.0.0.1:8741/api/v2/pipeline/run \
  -H "APXV-API-KEY: $APXV_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "pack": "apxv-pack-my-first-pack",
    "input_text": "Email me at user@example.com",
    "attest": true,
    "async": false
  }'
```

### Pack demo script

```bash
python governance-libraries/apxv-pack-my-first-pack/examples/run_pack_demo.py
```

---

## 6. Verify and accept

1. **Artifacts:** `managed/artifacts/` or **Artifacts** in the operator console
2. **Audit:** `python -m scripts.apxv_ctl integrity` or **System → Doctor**
3. **ZK (if attested):** `python -m scripts.verify_attestation --real-zk <artifact-path>`
4. **Acceptance:** copy checklist from [apxv-pack-reference-redaction/ACCEPTANCE.md](../governance-libraries/apxv-pack-reference-redaction/ACCEPTANCE.md) into your pack

---

## 7. Capability policy (if you add new agent IDs)

Custom agents need grants in `managed/config/capabilities.json`:

```bash
python -m scripts.apxv_ctl policy-sign --description "Added my-first-pack agents"
```

Re-sign after editing policy. See [BUILDING.md](BUILDING.md) § capabilities.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Pack not found` | Check `governance-libraries/apxv-pack-<slug>/pack.yaml` exists |
| `unapproved change detected` on run | Governance edited outside approve workflow — run `apxv_ctl integrity` hints or re-activate pack |
| `401` from API | Set `APXV_API_KEY`; legacy `APX_API_KEY` works until v1.4 |
| Pack activate warns non-official | Expected for custom packs; use `--confirm` on CLI if prompted |

---

## Next steps

| Doc | Topic |
|-----|--------|
| [PACK-CATALOG.md](PACK-CATALOG.md) | Official packs and community tier |
| [BUILDING.md](BUILDING.md) | Custom agents, LLM backends, API clients |
| [OPERATOR-GUIDE.md](../../ui/docs/OPERATOR-GUIDE.md) | Operator console daily operations |
| [LOCAL-API-V2.md](LOCAL-API-V2.md) | Full HTTP contract |