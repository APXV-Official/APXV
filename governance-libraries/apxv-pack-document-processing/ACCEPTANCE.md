# Pack acceptance — Document Processing Pack

**Pack:** `apxv-pack-document-processing` v0.1.0  
**Requires:** APXV1 v1.2.0+

## Install verification

- [ ] `pack.yaml` version recorded
- [ ] Governance applied via propose → approve → apply (optional for demo on default specs)
- [ ] `python -m scripts.apx_doctor` → HEALTHY

## Functional demo

```bash
python governance-libraries/apxv-pack-document-processing/examples/run_pack_demo.py
```

- [ ] Exit code 0
- [ ] `final_status=ATTESTED`
- [ ] `file_count=2`
- [ ] `compliance_policy_id=2`
- [ ] `total_redactions>=1`

## Batch manifest

- [ ] `proposed_artifact.output.batch_manifest.files` has one entry per input file
- [ ] Each file entry includes `original_hash`, `redacted_hash`, `entity_count`

## Sign-off

| Role | Date |
|------|------|
| Operator | |