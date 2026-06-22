# APXV1 v1.1.0 Release Notes

**Date:** 2026-06-22  
**Tag:** `v1.1.0`

## Summary

Public launch bar: voice privacy suite, Tier B ceremony transparency, and entity ZK fixes on top of v1.0.x dual-track attestation.

## Highlights

- **Voice:** STT → redact → attest with `voice-redaction` proof (simulated in CI; local Vosk + pyttsx3 via `[voice]` extras)
- **Ceremony:** Tier B transcript tooling + publishable verifier bundle (VKs only, no PKs)
- **Fixes:** Entity propagation for multi-entity proofs; `apx-zk` `json_fr` decimal Merkle root parsing (`batch-merkle` for two-entity documents)

## Artifacts

| Artifact | How to obtain |
|----------|----------------|
| Source | `git checkout v1.1.0` |
| Verifier bundle | GitHub Release asset `apxv1-verifier-bundle-v1.1.0.zip`, or `python -m scripts.export_verifier_bundle --out dist/apxv1-verifier-bundle-v1.1.0` after `setup_first_run` |

## Verify a published attestation

```bash
# After pip install -e ".[dev]"
python -m scripts.verify_attestation --real-zk /path/to/attested_artifact.json
```

Confirm `vk_hex` in proofs matches VK hashes in the verifier bundle / ceremony transcript.

## Trust model

- **Self-host:** run `setup_first_run` on your machine — you trust your own setup.
- **Verify our artifacts:** use our verifier bundle — you trust our setup honesty for those VKs (not MPC/PoT).

See [cryptography/CEREMONY.md](cryptography/CEREMONY.md) and [cryptography/ASSUMPTIONS.md](cryptography/ASSUMPTIONS.md).

## Demo

- **Video (v1.0.x):** `apxv1-demo.mp4` — text attest, dual ZK, E2EE
- **v1.1 walkthrough:** [DEMO-SCRIPT-V1.1.md](DEMO-SCRIPT-V1.1.md) — voice + ceremony (canonical scripted demo)

## Quality

- **307** pytest tests (1 optional Vosk skip), CI green
- Rust: apx-circuits + apx-zk workspace tests pass

## Publish GitHub Release (operator)

If the Release page is not created yet:

```bash
pip install -e ".[dev]"
python -m scripts.export_verifier_bundle --out dist/apxv1-verifier-bundle-v1.1.0
# zip dist/apxv1-verifier-bundle-v1.1.0 for upload, or:
set GITHUB_TOKEN=ghp_...
python -m scripts.publish_github_release --tag v1.1.0
```