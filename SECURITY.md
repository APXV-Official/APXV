# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.3.x   | Yes       |

## Reporting a Vulnerability

Open a private security advisory on GitHub, or email the maintainer via the contact listed in the repository profile. Do not post exploit details in public issues.

Include:
- Affected version
- Steps to reproduce
- Impact assessment
- Suggested fix (if any)

## Threat Model (Plain Language)

APX is designed for **local, self-hosted, air-gapped** use. It is a **research foundation**, not a certified compliance product.

### APX Protects Against

- **Casual tampering** with artifacts and audit logs (hash chains detect modification)
- **Unaudited rule changes** (governance approval workflow required)
- **Unsigned capability policy changes** (Ed25519-signed local policy)
- **Accidental data egress via APX itself** (localhost-only API, no built-in telemetry)
- **Unverifiable processing claims** (optional Groth16 proofs bind execution to rule hashes)

### APX Does NOT Protect Against

- **Malicious operators** with filesystem and key access
- **Compromised host OS** (malware, root access)
- **Physical access** to the machine
- **Advanced insider attacks** that steal signing keys from `managed/config/`
- **All PII leakage** (redaction is pattern-based, not full DLP)
- **Regulatory certification** (not HIPAA, SOC2, or GDPR certified)

## Operator Responsibilities

1. **Back up** `managed/` and `rust/keys/` regularly.
2. **Restrict filesystem access** to the APX host.
3. **Bind API to localhost** only (default; do not expose to LAN/internet without additional controls).
4. **Rotate keys** if compromise is suspected.
5. **Change governance specs** only through the approval workflow, not direct file edits.

## Key Locations

| Path | Purpose |
|------|---------|
| `managed/config/api_keys.json` | Hashed operator API keys |
| `managed/config/capability_signing.key` | Capability policy signing key |
| `managed/config/governance_signing.key` | Governance approval signing key |
| `rust/keys/` | ZK circuit proving/verification keys |

Treat these as secrets. They are gitignored by default.

## Disclaimer

APX v1 is provided as-is under the Apache License 2.0. Use at your own risk for sensitive data until you have independently assessed fit for your environment.