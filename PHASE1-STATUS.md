# APXV1 Phase 1 — Cryptographic Credibility Status

**Goal:** Real, independently verifiable proofs with honest setup assumptions.  
**Circuit Version:** 1.1.0  
**Last verified:** 2026-06-17

## Exit Criteria Checklist

- [x] **#1 Honest Trusted Setup** — `scripts/setup_zk.py`, persisted `rust/keys/`, no per-proof `circuit_specific_setup`
- [x] **#2 Circuit Hardening** — v1.1.0 witness-bound constraints in all three circuits
- [x] **#3 Independent Verifiability** — `verify_attestation --real-zk`, `apx_verify_bundle`, Rust `verify` command
- [x] **#4 VK Integrity & Lifecycle** — `rust/keys/manifest.json`, VK hash checks at verification
- [x] **#5 Cryptographic Assumptions** — `docs/cryptography/ASSUMPTIONS.md`
- [x] **#6 Reproducible Demonstration** — `run_apx --attest` + `verify_attestation --real-zk` (see commands below)
- [x] **#7 No Overstated Claims** — README states research-prototype status

## Verification Commands

```bash
pip install -e ".[dev]"
python -m scripts.setup_zk --force    # after circuit changes
python -m scripts.run_apx --attest
python -m scripts.verify_attestation --real-zk
python -m scripts.apx_verify_bundle managed/artifacts/<latest_with_zk>.json
python -m pytest tests/ -v
```

## Phase 1 Complete — Phase 2 Next

Phase 1 establishes cryptographic credibility for the **proof machinery**. Phase 2 (Governed Core Hardening) covers production artifact store, audit logging, access control, and security review of the redaction/governance logic.