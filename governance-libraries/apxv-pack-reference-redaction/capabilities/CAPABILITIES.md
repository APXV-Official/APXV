# Capability policy — Reference Redaction Pack

Fresh APXV instances created with `setup_first_run` already include this pack's agent IDs in the signed capability policy.

## Agent IDs

| Agent ID | Grants (default policy) |
|----------|-------------------------|
| APXV-AGENT-001 | `execute_agent`, `read_specification`, `write_artifact` |
| APXV-AGENT-002 | `execute_agent`, `read_specification`, `write_artifact` |
| APXV-AGENT-003 | `execute_agent`, `read_specification`, `write_artifact`, `verify_attestation` |

## Verify after install

```bash
python -m scripts.apxv_ctl policy-verify
python -m scripts.apxv_ctl capabilities
```

## Re-sign only if needed

If you stripped or replaced the default policy, add the agent IDs above to `managed/config/capabilities.json`, then:

```bash
python -m scripts.apxv_ctl policy-sign --description "Reference Redaction Pack agents"
```

See `policy-delta.json` for documentation (not auto-applied).