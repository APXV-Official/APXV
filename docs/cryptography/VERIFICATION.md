# APXV1 — Independent Proof Verification (v1.1)

## What you need

To verify Groth16 proofs **without re-proving**:

1. The attested artifact JSON (`zk_proof_*`, `entity_proofs`, optional `voice_session`)
2. Matching verification keys for the same circuit version:
   - Published verifier bundle (recommended), or
   - `rust/apx-circuits/keys/manifest.json` + `rust/apx-zk/keys/entity-manifest.json` + `.vk` files
3. A verifier:
   - `python -m scripts.verify_attestation --real-zk [artifact.json]`
   - `python -m scripts.apx_verify_bundle <artifact.json>`
   - Rust: `apx-circuits verify` / `apx-zk verify` with proof bundle JSON

## Trust model

| Verification type | What you can confirm | What you still trust |
|-------------------|----------------------|----------------------|
| **Proof math** | Groth16 valid for public inputs under the VK | Nothing (cryptographic) |
| **VK lineage** | Transcript hashes match published manifests (Tier B) | Setup party did not swap keys after signing |
| **Setup honesty** | — | Setup entropy was discarded (unless you self-host) |

If you run your own `setup_first_run`, you verify against **your** keys and trust **your** setup. Verifying **another party's** artifacts uses **their** VKs — you trust their one-time setup.

See [CEREMONY.md](CEREMONY.md) and [ASSUMPTIONS.md](ASSUMPTIONS.md).

## What gets verified on `--real-zk`

`verify_attestation --real-zk` runs:

1. Python-side provenance and governance checks
2. VK integrity (`vk_hex` vs manifest on disk or bundle)
3. Independent Groth16 verify for:
   - **Governance (3):** `redaction`, `rule-binding`, `pipeline`
   - **Entity (present in artifact):** typically `redaction-v1`, `core-redaction`, optional `batch-merkle`, optional `voice-redaction`

Not every entity circuit in the crate appears on every artifact. See [CIRCUITS.md](CIRCUITS.md).

## Proof bundle format

Each proof entry contains:

```json
{
  "circuit": "redaction-v1",
  "circuit_version": "1.0.0",
  "vk_hash": "sha256-of-on-disk-vk-bytes",
  "proof_hex": "...",
  "vk_hex": "...",
  "public_inputs": { ... },
  "verification_result": true,
  "status": "VERIFIED"
}
```

## Verification steps

### Option A — Full APXV1 verifier (recommended)

```bash
python -m scripts.verify_attestation --real-zk
python -m scripts.verify_attestation path/to/artifact.json --real-zk
```

### Option B — Standalone bundle verifier

```bash
python -m scripts.apx_verify_bundle managed/artifacts/attested_result_pipeline_with_zk_*.json
```

### Option C — Rust binary only

```bash
cargo build --release --manifest-path rust/Cargo.toml -p apx-circuits -p apx-zk
# Proof JSON must include proof_hex, vk_hex, and circuit inputs (see apx-zk verify --inputs)
```

### Option D — Release verifier bundle

1. Obtain `apxv1-verifier-bundle` from GitHub Releases (VKs, manifests, optional signed transcript).
2. Confirm transcript `content_hash` and signature when Tier B applies.
3. Run Option A with APXV1 installed, or compare artifact `vk_hex` to bundle VK bytes.

## VK integrity

Before Groth16 verify, APXV1 checks that `vk_hex` matches the authoritative VK in the manifest. This detects stale proofs, tampered keys, or re-setup drift.

## What verification proves

See [ASSUMPTIONS.md](ASSUMPTIONS.md).

Verification confirms: *a valid Groth16 proof exists for the claimed public inputs under the published VK*. It does **not** prove Python redaction logic was semantically correct or that public inputs match real-world data.