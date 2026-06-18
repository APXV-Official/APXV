# Installing Rust (Required for ZK)

APXV1 uses Groth16 proofs. The Rust toolchain builds `apx-circuits` and runs trusted setup.

## Windows

1. Download and run [rustup-init.exe](https://win.rustup.rs/x86_64)
2. Open a **new** PowerShell window
3. Verify:

```powershell
rustc --version
cargo --version
```

4. Build APXV1 circuits (from project root):

```powershell
cd rust
cargo build --release
```

The binary is at `rust\target\release\apx-circuits.exe`.

## macOS

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
rustc --version
cargo --version
cd rust && cargo build --release
```

## Linux

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
cd rust && cargo build --release
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
| ZK setup slow first time | Normal — trusted setup for 3 circuits |
| `apx-circuits` not found | Run `cargo build --release` in `rust/` |