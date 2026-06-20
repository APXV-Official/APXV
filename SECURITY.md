# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |
| 0.3.x   | No        |

## Reporting a Vulnerability

Open a private security advisory on GitHub, or email the maintainer via the contact listed in the repository profile. Do not post exploit details in public issues.

Include:
- Affected version
- Steps to reproduce
- Impact assessment
- Suggested fix (if any)

## Threat Model (Plain Language)

APXV1 (*Attested Proof Execution Verified*, 1st generation) is designed for **local, self-hosted, air-gapped** use. It is a **research foundation**, not a certified compliance product.

### APXV1 Protects Against

- **Casual tampering** with artifacts and audit logs (hash chains detect modification)
- **Unaudited rule changes** (governance approval workflow required)
- **Unsigned capability policy changes** (Ed25519-signed local policy)
- **Accidental data egress via APXV1 itself** (localhost-only API, no built-in telemetry)
- **Unverifiable processing claims** (Groth16 proofs bind execution to rule hashes; use `run_apx --attest` and `verify_attestation --real-zk`)

### APXV1 Does NOT Protect Against

- **Malicious operators** with filesystem and key access
- **Compromised host OS** (malware, root access)
- **Physical access** to the machine
- **Advanced insider attacks** that steal signing keys from `managed/config/`
- **All PII leakage** (redaction is pattern-based, not full DLP)
- **Regulatory certification** (not HIPAA, SOC2, or GDPR certified)

## Operator Responsibilities

1. **Back up** `managed/`, `rust/apx-circuits/keys/`, and `rust/apx-zk/keys/` regularly.
2. **Restrict filesystem access** to the APXV1 host.
3. **Bind API to localhost** only (default; do not expose to LAN/internet without additional controls).
4. **Rotate keys** if compromise is suspected.
5. **Change governance specs** only through the approval workflow, not direct file edits.

## Key Locations

| Path | Purpose |
|------|---------|
| `managed/config/api_keys.json` | Hashed operator API keys |
| `managed/config/capability_signing.key` | Capability policy signing key |
| `managed/config/governance_signing.key` | Governance approval signing key |
| `rust/apx-circuits/keys/` | Governance ZK proving/verification keys |
| `rust/apx-zk/keys/` | Entity ZK proving/verification keys |
| `managed/config/e2ee-keypair.json` | Optional E2EE keypair (when `--encrypt` is used) |

Treat these as secrets. They are gitignored by default.

## Disclaimer

APXV1 is provided as-is under the Apache License 2.0. Use at your own risk for sensitive data until you have independently assessed fit for your environment.