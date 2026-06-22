# APXV1 — Trusted Setup Process

**Circuit Version:** see `rust/apx-circuits/keys/manifest.json` (governance) and `rust/apx-zk/keys/entity-manifest.json` (entity)

## Overview

APXV1 uses Groth16 over BN254 (arkworks 0.4). Each circuit requires a **one-time trusted setup** that produces a ProvingKey (PK) and VerifyingKey (VK). These keys are persisted and reused for all subsequent proofs.

APXV1 v1.1.0 has **two key directories**:

| Track | Crate | Keys directory | Manifest |
|-------|-------|----------------|----------|
| Governance (Track A) | `apx-circuits` | `rust/apx-circuits/keys/` | `manifest.json` |
| Entity (Track B) | `apx-zk` | `rust/apx-zk/keys/` | `entity-manifest.json` |

## When Setup Is Required

Run setup when:
- First deploying APXV1
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
rust/target/release/apx-circuits setup redaction
rust/target/release/apx-zk setup redaction-v1
```

Run manual setup from the respective crate directory (`rust/apx-circuits/` or `rust/apx-zk/`) after `cargo build --release`.

## What Happens During Setup

1. `StdRng::from_entropy()` provides cryptographic randomness (via `getrandom` on `ark-std`)
2. `Groth16::<Bn254>::circuit_specific_setup` runs **once** per circuit
3. PK and VK are serialized with `ark-serialize` (compressed) to the crate's `keys/` directory
4. The appropriate manifest is updated with VK/PK SHA-256 hashes and circuit version
5. The setup RNG ("toxic waste") is discarded — it is **not** written to disk

## Entropy Source

- **Library:** `ark_std::rand::rngs::StdRng::from_entropy()`
- **Backend:** `getrandom` crate (OS CSPRNG: `/dev/urandom`, `BCryptGenRandom`, etc.)
- **Limitation:** Single-party setup. A malicious operator who retains toxic waste could forge proofs.

## Key Files (Governance)

| File | Purpose |
|------|---------|
| `rust/apx-circuits/keys/redaction.pk` | Proving key (operator-only) |
| `rust/apx-circuits/keys/redaction.vk` | Verifying key (distributable) |
| `rust/apx-circuits/keys/rule-binding.pk` / `.vk` | Rule-binding circuit keys |
| `rust/apx-circuits/keys/pipeline.pk` / `.vk` | Pipeline circuit keys |
| `rust/apx-circuits/keys/manifest.json` | VK hashes, circuit version, setup timestamps |

## Key Files (Entity)

| File | Purpose |
|------|---------|
| `rust/apx-zk/keys/<circuit>.pk` / `.vk` | Per-circuit entity proving/verification keys |
| `rust/apx-zk/keys/entity-manifest.json` | Entity VK hashes and circuit version |

## Ceremony transparency (v1.1)

After setup, operators can publish auditable VK lineage:

```bash
python -m scripts.ceremony_transcript --write --tier B
python -m scripts.ceremony_transcript --verify
python -m scripts.export_verifier_bundle --out dist/apxv1-verifier-bundle
```

See [CEREMONY.md](CEREMONY.md) for tiers, trust model, and limitations. See [CIRCUITS.md](CIRCUITS.md) for which circuits run on `--attest`.

## Limitations

- **Single-party honest setup** — not MPC or Powers of Tau (Tier C is v1.2+)
- **Tier B** adds signed transcript + verifier bundle — not proof that toxic waste was destroyed
- **No HSM integration** — keys stored as files on disk
- **No automated key rotation** — manual re-setup required after circuit changes