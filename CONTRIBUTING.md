# Contributing to APXV1

Thank you for your interest in **APXV1**. **APXV** (*Attested Proof Execution Verified*) is an air-gapped governed agent platform: markdown rules, signed capabilities, chained audit, Groth16 proofs, local API — bring your own LLMs. **APXV1** is the first-generation open-source implementation.

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

   For CI parity on voice paths: `APX_VOICE_MODE=simulated python -m pytest tests/ -v`

## Development Principles

- **Local-first:** No cloud dependencies, no outbound network calls in core paths.
- **Governed by default:** Agents read versioned specs; changes go through approval workflow.
- **Auditable:** Artifact and audit chains must remain verifiable.
- **Accurate documentation:** State limitations and trust assumptions clearly in docs and PR descriptions.

## Pull Requests

1. Keep changes focused — one logical change per PR.
2. Add or update tests for behavior changes.
3. Run `python -m scripts.apx_ctl integrity` before submitting.
4. Update docs when changing user-visible behavior.

## Reporting Issues

Use the **Bug report** issue template when possible. At minimum include:

- OS and Python version
- Whether Rust/ZK setup completed
- Output from `python -m scripts.apx_doctor` (preferred) or `python -m scripts.apx_ctl integrity`
- Fresh install vs reused `managed/` folder (integrity failures are common on polluted dev trees)

Do **not** include API keys, signing keys, or real PII in issue reports.

Maintainers respond on a **best-effort** basis; there is no SLA for free GitHub support.

## Security

See [SECURITY.md](SECURITY.md) for the threat model and how to report vulnerabilities.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.