# Capability policy — Reference Redaction Pack

Fresh APXV1 instances created with `setup_first_run` already include this pack's agent IDs in the signed capability policy.

## Agent IDs

| Agent ID | Grants (default policy) |
|----------|-------------------------|
| APX-AGENT-001 | `execute_agent`, `read_specification`, `write_artifact` |
| APX-AGENT-002 | `execute_agent`, `read_specification`, `write_artifact` |
| APX-AGENT-003 | `execute_agent`, `read_specification`, `write_artifact`, `verify_attestation` |

## Verify after install

```bash
python -m scripts.apx_ctl policy-verify
python -m scripts.apx_ctl capabilities
```

## Re-sign only if needed

If you stripped or replaced the default policy, add the agent IDs above to `managed/config/capabilities.json`, then:

```bash
python -m scripts.apx_ctl policy-sign --description "Reference Redaction Pack agents"
```

See `policy-delta.json` for documentation (not auto-applied).