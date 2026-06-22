# Installing Rust (Required for ZK)

APXV1 uses Groth16 proofs. The Rust toolchain builds `apx-circuits` (governance) and `apx-zk` (entity) and runs trusted setup.

## Windows

1. Download and run [rustup-init.exe](https://win.rustup.rs/x86_64)
2. Open a **new** PowerShell window
3. Verify:

```powershell
rustc --version
cargo --version
```

4. Build APXV1 Rust workspace (from project root):

```powershell
cargo build --release --manifest-path rust/Cargo.toml -p apx-circuits -p apx-zk
```

Binaries: `rust\target\release\apx-circuits.exe` and `rust\target\release\apx-zk.exe`.

## macOS

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
rustc --version
cargo --version
cargo build --release --manifest-path rust/Cargo.toml -p apx-circuits -p apx-zk
```

## Linux

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
cargo build --release --manifest-path rust/Cargo.toml -p apx-circuits -p apx-zk
```

## After Rust is installed

```bash
python -m scripts.setup_first_run
python -m scripts.apx_doctor
```

## Docker users

Rust is **not** required on the host if you only use Docker — ZK keys are generated during `docker compose build`.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `cargo: command not found` | Restart terminal after rustup install |
| ZK setup slow first time | Normal — trusted setup for 3 governance + 8 entity circuits (see [cryptography/CIRCUITS.md](cryptography/CIRCUITS.md) for attest-path subset) |
| `apx-circuits` / `apx-zk` not found | Run `cargo build --release --manifest-path rust/Cargo.toml -p apx-circuits -p apx-zk` |