# APXV1 Rust Workspace

Groth16 zero-knowledge proof crates for APXV1 (BN254 / arkworks 0.4).

## Crates

| Crate | Purpose | Keys |
|-------|---------|------|
| `apx-circuits` | Governance pipeline proofs (3 circuits) | `apx-circuits/keys/manifest.json` |
| `apx-zk` | Entity-level proofs (8 circuits in crate; 3–4 + voice on default Python attest) | `apx-zk/keys/entity-manifest.json` |

See [../docs/cryptography/CIRCUITS.md](../docs/cryptography/CIRCUITS.md) for which circuits run on `run_apx --attest`.

## Build & test

```powershell
# From repository root (directory containing rust/ and pyproject.toml)
cargo test --manifest-path rust/Cargo.toml
cargo build --release --manifest-path rust/Cargo.toml -p apx-circuits -p apx-zk
```

## Governance circuits (Track A)

```powershell
rust/target/release/apx-circuits setup redaction
rust/target/release/apx-circuits prove redaction --inputs inputs.json
```

Run from `rust/apx-circuits/` (keys resolve relative to crate cwd).

## Entity circuits (Track B)

```powershell
python -m scripts.setup_entity_zk
rust/target/release/apx-zk setup redaction-v1
```

Run from `rust/apx-zk/`.