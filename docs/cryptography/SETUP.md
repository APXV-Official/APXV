# APX v1 — Trusted Setup Process (Phase 1)

**Status:** Active — Phase 1 Criterion #1  
**Circuit Version:** 1.1.0

## Overview

APX uses Groth16 over BN254 (arkworks 0.4). Each circuit requires a **one-time trusted setup** that produces a ProvingKey (PK) and VerifyingKey (VK). These keys are persisted and reused for all subsequent proofs.

## When Setup Is Required

Run setup when:
- First deploying APX v1
- Circuit code changes (version bump in `rust/circuits/*.rs`)
- Keys are missing from `rust/keys/`
- Verification fails with VK mismatch errors

## Commands

```bash
# Auto-setup (runs only for missing keys)
python -m scripts.setup_zk

# Force re-setup after circuit changes
python -m scripts.setup_zk --force

# Manual per-circuit setup (Rust)
cd rust
cargo run -- setup redaction
cargo run -- setup rule-binding
cargo run -- setup pipeline
```

## What Happens During Setup

1. `StdRng::from_entropy()` provides cryptographic randomness (via `getrandom` on `ark-std`)
2. `Groth16::<Bn254>::circuit_specific_setup` runs **once** per circuit
3. PK and VK are serialized with `ark-serialize` (compressed) to `rust/keys/<circuit>.pk` and `.vk`
4. `rust/keys/manifest.json` is updated with VK/PK SHA-256 hashes and circuit version
5. The setup RNG ("toxic waste") is discarded — it is **not** written to disk

## Entropy Source

- **Library:** `ark_std::rand::rngs::StdRng::from_entropy()`
- **Backend:** `getrandom` crate (OS CSPRNG: `/dev/urandom`, `BCryptGenRandom`, etc.)
- **Limitation:** Single-party setup. A malicious operator who retains toxic waste could forge proofs.

## Key Files

| File | Purpose |
|------|---------|
| `rust/keys/redaction.pk` | Proving key (operator-only) |
| `rust/keys/redaction.vk` | Verifying key (distributable) |
| `rust/keys/rule-binding.pk` / `.vk` | Rule-binding circuit keys |
| `rust/keys/pipeline.pk` / `.vk` | Pipeline circuit keys |
| `rust/keys/manifest.json` | VK hashes, circuit version, setup timestamps |

## Phase 1 Limitations

- **Single-party honest setup** — not a multi-party computation (MPC) ceremony
- **No public ceremony** — setup is local to the operator
- **No HSM integration** — keys stored as files on disk
- **No automated key rotation** — manual re-setup required after circuit changes

## Future (Post-Phase 1)

- Multi-party trusted setup ceremony
- HSM-backed key storage
- Automated key rotation and revocation
- Public audit trail of ceremony participants