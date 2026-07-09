# APXV — Rust ZK Circuits (Step 5)

This directory contains the three small, original Rust circuits for the APXV reference implementation.

## Scope (Locked)

- Exactly **three** small circuits.
- Written fresh for APXV.
- **Reference only**: Legacy proof-system circuit sources (gitignored `*-proof-system/`) were studied for patterns (arkworks 0.4 + BN254 + Groth16 structure, ConstraintSynthesizer usage, public vs witness allocation, basic constraint patterns). No code was copied.
- These circuits are intentionally minimal to match the "3 of everything" tiny build.

## The Three Circuits

1. **redaction_proof.rs**  
   Proves basic redaction correctness: that a redacted document hash is consistent with an original hash under a known redaction count and categories. Binds the redaction operation.

2. **rule_binding.rs**  
   Binds the redaction proof to a specific rule set. Takes the `rule_file_hash` (from APX-RULE-001) as a public input and enforces that the redaction was performed under that exact rule version.

3. **pipeline_attestation.rs**  
   Top-level aggregation circuit for the full 3-agent pipeline.  
   Public inputs include hashes from all three agents + the final governance decision.  
   This is the circuit that would be used to produce the final verifiable attestation for an `AttestedResult`.

## Technology

- arkworks 0.4 (BN254 curve, Groth16)
- R1CS constraint system
- Designed to be compiled to WASM later (in Step 6/7)

## Current Status

These are structural implementations with real constraint logic where practical for the tiny scope. Full proving/verification integration happens in Step 7 (end-to-end).

## Build Notes

A minimal original `Cargo.toml` (Apache-2.0) has been added in Step 5 for the three circuits.

When we reach Step 6/7 we will expand the Rust side to support:
- Generating proving/verifying keys
- Producing proofs from the Python agent outputs
- Verifying proofs end-to-end

The three circuit files are the core deliverable of Step 5.

---

**All circuits in this directory are original work for APXV.**

---

## Step 7 — Integration Binary (`src/main.rs`)

In Step 7 we added the original integration binary `rust/src/main.rs` (Apache-2.0, 2026).

### Usage (after `cargo build`)

```bash
# From the APXV project root
cargo run --manifest-path rust/Cargo.toml -- prove redaction --inputs <prepared_inputs.json>

cargo run --manifest-path rust/Cargo.toml -- verify redaction --inputs <prepared_inputs.json>
```

- `prove` generates a **real Groth16 proof** over BN254 for the `RedactionProofCircuit` (and immediately verifies it for the tiny demo scope).
- Output includes `"status": "VERIFIED"` when successful.
- Python scripts (`run_apxv.py --attest` and `verify_attestation.py --zk`) call these commands via subprocess.

This completes the "verifiable proof" requirement for the APXV reference pipeline.

**Note:** For the absolute smallest scope we use `circuit_specific_setup` + immediate verify. Full trusted setup + serialized proof transport is deferred to a later slice.
