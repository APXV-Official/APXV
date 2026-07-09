# Pack acceptance — Reference Redaction Pack

Run on a **fresh** APXV instance (`setup_first_run` complete). Use a gold clone or isolated `managed/` when validating handoff.

**Pack:** `apxv-pack-reference-redaction` v0.1.0

## Install verification

- [ ] `pack.yaml` version recorded in instance notes
- [ ] Governance applied via propose → approve → apply (not hand-edited live files)
- [ ] `python -m scripts.apxv_ctl policy-verify` → valid
- [ ] `python -m scripts.apxv_ctl capabilities` lists APXV-AGENT-001, 002, 003
- [ ] `python -m scripts.apxv_doctor` → HEALTHY

## Functional demo

From APXV root:

```bash
python governance-libraries/apxv-pack-reference-redaction/examples/run_pack_demo.py
```

- [ ] Exit code 0
- [ ] Output includes `final_status=ATTESTED` and `total_redactions=4`
- [ ] Artifacts written under `managed/`
- [ ] Audit events present in `managed/audit/` (agent1/2/3 logs)

## Attestation

```bash
python -m scripts.run_apxv --attest
python -m scripts.verify_attestation --real-zk
```

- [ ] `run_apx --attest` exit code 0
- [ ] `verify_attestation --real-zk` reports OK

## Sign-off

| Role | Date |
|------|------|
| Operator | |