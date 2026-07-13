# APXV — Trusted Setup Process

**Circuit Version:** see `rust/apxv-circuits/keys/manifest.json` (governance) and `rust/apxv-zk/keys/entity-manifest.json` (entity)

## Overview

APXV uses Groth16 over BN254 (arkworks 0.4). Each circuit requires a **one-time trusted setup** that produces a ProvingKey (PK) and VerifyingKey (VK). These keys are persisted and reused for all subsequent proofs.

APXV v1.1.0 has **two key directories**:

| Track | Crate | Keys directory | Manifest |
|-------|-------|----------------|----------|
| Governance (Track A) | `apxv-circuits` | `rust/apxv-circuits/keys/` | `manifest.json` |
| Entity (Track B) | `apxv-zk` | `rust/apxv-zk/keys/` | `entity-manifest.json` |

## When Setup Is Required

Run setup when:
- First deploying APXV
- Circuit code changes (version bump in manifest)
- Keys are missing from either key directory
- Verification fails with VK mismatch errors

## Commands

```bash
# First-run: governance + entity setup (recommended)
python -m scripts.setup_first_run

# Governance circuits only
python -m scripts.setup_zk
python -m scripts.setup_zk --force

# Entity circuits only
python -m scripts.setup_entity_zk
python -m scripts.setup_entity_zk --force

# Manual per-circuit setup (prefer pre-built release binaries)
rust/target/release/apxv-circuits setup redaction
rust/target/release/apxv-zk setup redaction-v1
```

Run manual setup from the respective crate directory (`rust/apxv-circuits/` or `rust/apxv-zk/`) after `cargo build --release`.

## What Happens During Setup

1. `StdRng::from_entropy()` provides cryptographic randomness (via `getrandom` on `ark-std`)
2. `Groth16::<Bn254>::circuit_specific_setup` runs **once** per circuit
3. PK and VK are serialized with `ark-serialize` (compressed) to the crate's `keys/` directory
4. The appropriate manifest is updated with VK/PK SHA-256 hashes and circuit version
5. The setup RNG ("toxic waste") is discarded — it is **not** written to disk

## Entropy Source

- **Library:** `ark_std::rand::rngs::StdRng::from_entropy()`
- **Backend:** `getrandom` crate (OS CSPRNG: `/dev/urandom`, `BCryptGenRandom`, etc.)
- **Limitation:** Single-party setup. A party that retained setup entropy could forge proofs.

## Shipped reference keys (v1.1.0)

The repository includes pre-generated `.pk` and `.vk` files under both key directories so install → attest works without an immediate setup step. These are **reference keys** for evaluation and CI.

For an isolated trust boundary, run `setup_first_run` (or `--force` per-circuit setup) and protect the resulting `.pk` files locally. Distribute only `.vk` material via `export_verifier_bundle` (proving keys are excluded from the bundle).

## Key Files (Governance)

| File | Purpose |
|------|---------|
| `rust/apxv-circuits/keys/redaction.pk` | Proving key (confidential on your deployment) |
| `rust/apxv-circuits/keys/redaction.vk` | Verifying key (distributable) |
| `rust/apxv-circuits/keys/rule-binding.pk` / `.vk` | Rule-binding circuit keys |
| `rust/apxv-circuits/keys/pipeline.pk` / `.vk` | Pipeline circuit keys |
| `rust/apxv-circuits/keys/manifest.json` | VK hashes, circuit version, setup timestamps |

## Key Files (Entity)

| File | Purpose |
|------|---------|
| `rust/apxv-zk/keys/<circuit>.pk` / `.vk` | Per-circuit entity proving/verification keys |
| `rust/apxv-zk/keys/entity-manifest.json` | Entity VK hashes and circuit version |

## Ceremony transparency (v1.1)

After setup, generate auditable VK lineage:

```bash
python -m scripts.ceremony_transcript --write --tier B
python -m scripts.ceremony_transcript --verify
python -m scripts.export_verifier_bundle --out dist/apxv-verifier-bundle
```

See [CEREMONY.md](CEREMONY.md) for tiers, trust model, and limitations. See [CIRCUITS.md](CIRCUITS.md) for which circuits run on `--attest`.

## Limitations

- **Single-party setup** — multi-party ceremony is a future capability (Tier C)
- **Tier B** adds signed transcript and verifier bundle — does not cryptographically prove setup entropy was destroyed
- **No HSM integration** — keys stored as files on disk
- **No automated key rotation** — manual re-setup required after circuit changes