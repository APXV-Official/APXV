# Contributing to APXV

Thank you for your interest in **APXV** (*Attested Proof Execution Verified*) — an air-gapped governed agent platform: markdown rules, signed capabilities, chained audit, Groth16 proofs, local API — bring your own LLMs.

## Getting Started

1. Fork the repository and clone your fork.
2. Install dependencies (include `voice` for the full test suite):

   ```bash
   pip install -e ".[dev,voice]"
   ```

3. Run first-time setup (includes ZK keys — requires Rust):

   ```bash
   python -m scripts.setup_first_run
   ```

   See [docs/BUILDING.md](docs/BUILDING.md) for extension patterns.

4. Run tests (voice tests use simulated STT/TTS unless you install a local Vosk model):

   ```bash
   python -m pytest tests/ -v
   ```

   On Linux/WSL use `python3` if `python` is not on PATH. API tests bind an ephemeral port — they can run while `apxv_serve` listens on `8741`.

   Pytest sets `APXV_PROFILE=ci` automatically (simulated LLM/voice allowed). Do not use
   `ci` in operator bootstrap, Docker entrypoint, or MSI paths.

   For explicit CI parity on voice paths: `APXV_VOICE_MODE=simulated python -m pytest tests/ -v`

### Windows vs Linux

| Task | Linux / WSL | Windows |
|------|---------------|---------|
| Python | `python3` or `.venv/bin/python` after `install.sh` | `py -3` or `python` after `install.ps1` |
| Tests | `python3 -m pytest tests/ -v` | `py -3 -m pytest tests/ -v` |
| API server | Safe to run pytest while `apxv_serve` uses port 8741 (tests use ephemeral ports) | Same |
| Docker smoke | `./scripts/install-docker.sh` | `.\scripts\install-docker.ps1` (requires Docker Desktop) |

## Development Principles

- **Local-first:** No cloud dependencies, no outbound network calls in core paths.
- **Governed by default:** Agents read versioned specs; changes go through approval workflow.
- **Auditable:** Artifact and audit chains must remain verifiable.
- **Accurate documentation:** State limitations and trust assumptions clearly in docs and PR descriptions.

## Pull Requests

1. Keep changes focused — one logical change per PR.
2. Add or update tests for behavior changes.
3. Run `python -m scripts.apxv_ctl integrity` before submitting.
4. Update docs when changing user-visible behavior.

### Release notes (maintainers)

GitHub release bodies must use **ASCII punctuation only** (`-` and `|` for bullets) to avoid mojibake in the API/UI. Extract the `[X.Y.Z]` section from `CHANGELOG.md` with `python -m scripts.publish_github_release --tag vX.Y.Z` (or paste ASCII-only text manually). Attach the verifier bundle zip on every release (VKs unchanged since v1.1.0).

## Reporting Issues

Use the **Bug report** issue template when possible. At minimum include:

- OS and Python version
- Whether Rust/ZK setup completed
- Output from `python -m scripts.apxv_doctor` (preferred) or `python -m scripts.apxv_ctl integrity`
- Fresh install vs reused `managed/` folder (integrity failures are common on polluted dev trees; v1.2.2+ reports `issue: corrupt_lines` or `chain_break` in doctor output)

Do **not** include API keys, signing keys, or real PII in issue reports.

Maintainers respond on a **best-effort** basis; there is no SLA for free GitHub support.

## Security

See [SECURITY.md](SECURITY.md) for the threat model and how to report vulnerabilities.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.