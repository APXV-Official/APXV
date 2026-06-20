# APXV1 Rust Workspace

Groth16 zero-knowledge proof crates for APXV1 (BN254 / arkworks 0.4).

## Crates

| Crate | Purpose | Keys |
|-------|---------|------|
| `apx-circuits` | Governance pipeline proofs (3 circuits) | `apx-circuits/keys/manifest.json` |
| `apx-zk` | Entity-level proofs (8 circuits) | `apx-zk/keys/entity-manifest.json` |

## Build & test

```powershell
cd C:\APXV1
cargo test --manifest-path rust/Cargo.toml
cargo build --release --manifest-path rust/Cargo.toml -p apx-circuits -p apx-zk
```

## Governance circuits (Track A)

```powershell
cargo run --release --manifest-path rust/Cargo.toml -p apx-circuits -- setup redaction
cargo run --release --manifest-path rust/Cargo.toml -p apx-circuits -- prove redaction --inputs inputs.json
```

Run from `rust/apx-circuits/` (keys resolve relative to crate cwd).

## Entity circuits (Track B)

```powershell
python -m scripts.setup_entity_zk
cargo run --release --manifest-path rust/Cargo.toml -p apx-zk -- setup redaction-v1
```

Run from `rust/apx-zk/`.