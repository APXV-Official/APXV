# Pack acceptance — AI Governance Pack

**Pack:** `apxv-pack-ai-governance` v0.1.0  
**Requires:** APXV1 v1.2.0+

## Install verification

- [ ] `pack.yaml` version recorded
- [ ] Governance applied via propose → approve → apply (optional for demo on default specs)
- [ ] `python -m scripts.apx_doctor` → HEALTHY

## Functional demo

```bash
python governance-libraries/apxv-pack-ai-governance/examples/run_pack_demo.py
```

- [ ] Exit code 0
- [ ] `final_status=ATTESTED`
- [ ] `llm_decision` is `APPROVED`, `REVIEW_REQUIRED`, or `REJECTED`
- [ ] `compliance_policy_id=4`
- [ ] `total_redactions>=1`

## LLM governance metadata

- [ ] `proposed_artifact.output.llm_governance` includes `decision`, `confidence`, `cost_usd`, `latency_ms`

## Sign-off

| Role | Date |
|------|------|
| Operator | |