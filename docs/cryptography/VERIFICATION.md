# APXV1 — Independent Proof Verification (Phase 1)

**Status:** Active — Phase 1 Criterion #3

## What a Third Party Needs

To verify an APXV1 attestation **without trusting the operator** and **without re-proving**:

1. The attested artifact JSON (contains `zk_proof_*` bundles)
2. The `rust/keys/manifest.json` from the same circuit version (for VK integrity)
3. Either:
   - The APXV1 Python verifier: `python -m scripts.verify_attestation --real-zk`
   - The standalone verifier: `python -m scripts.apx_verify_bundle <artifact.json>`
   - The compiled Rust binary: `apx-circuits verify <circuit> --proof <bundle.json>`

## Proof Bundle Format

Each `zk_proof_*` entry in an attested artifact contains:

```json
{
  "circuit": "redaction",
  "circuit_version": "1.1.0",
  "vk_hash": "sha256-of-on-disk-vk-bytes",
  "proof_hex": "...",
  "vk_hex": "...",
  "public_inputs": { ... },
  "verification_result": true,
  "status": "VERIFIED"
}
```

## Verification Steps

### Option A — Full APXV1 verifier (recommended)

```bash
python -m scripts.verify_attestation --real-zk
python -m scripts.verify_attestation path/to/artifact.json --real-zk
```

This runs:
1. Python-side provenance/governance checks
2. VK integrity check against manifest
3. Independent Groth16 verification for all three circuits

### Option B — Standalone bundle verifier

```bash
python -m scripts.apx_verify_bundle managed/artifacts/attested_result_pipeline_with_zk_*.json
```

### Option C — Rust binary only (no Python runtime)

```bash
# Build once
cargo build --release --manifest-path rust/Cargo.toml

# Export a proof bundle (must include proof_hex, vk_hex, public_inputs)
apx-circuits verify redaction --proof proof_bundle.json
```

## VK Integrity (Wrong Key Detection)

Before cryptographic verification, APXV1 checks that the `vk_hex` in the proof bundle matches the authoritative VK on disk listed in `manifest.json`. This detects:

- Stale proofs from an older circuit version
- Tampered verification keys
- Accidental key mismatch after re-setup

## What Verification Proves

See `docs/cryptography/ASSUMPTIONS.md` for the precise cryptographic claims and limitations.

Verification confirms: *a valid Groth16 proof exists for the claimed public inputs under the published VK*. It does **not** prove the public inputs accurately represent real-world execution.