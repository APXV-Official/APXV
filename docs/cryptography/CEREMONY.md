# APXV1 — ZK Ceremony Transparency (v1.1)

APXV1 uses Groth16 with a **one-time trusted setup** per circuit. This document defines what we mean by "ceremony" for v1.1 releases and how operators publish verifiable transparency artifacts.

## Trust model (read this first)

| Scenario | Who you trust |
|----------|----------------|
| **Self-host** — clone APXV1, run `setup_first_run`, attest your own data | Yourself (your setup, your keys) |
| **Verify our release** — our artifacts + verifier bundle from GitHub Releases | Our one-time setup honesty + published VK lineage |

Tier B ceremony does **not** replace multi-party setup. It commits verification-key hashes and signs that commitment when operator Ed25519 signing keys exist (created by default in `setup_first_run`). Without signing keys, you have Tier A (hash-committed manifests only). Anyone can verify Groth16 proofs mathematically; setup honesty for **our** keys still requires trust or self-hosting.

## Tiers

### Tier A — Transparent single-party (v1.1 minimum)

- Operator runs setup locally (`setup_first_run` or per-circuit setup).
- **Manifests** record VK/PK SHA-256 hashes and circuit versions:
  - `rust/apx-circuits/keys/manifest.json`
  - `rust/apx-zk/keys/entity-manifest.json`
- **Ceremony transcript** (`managed/config/ceremony-transcript.json`) aggregates both manifests with metadata.
- **Verifier bundle** exports VK files + manifests only (no proving keys).

**Public claim:** "Proofs are verifiable against published verification keys; setup was operator-run with an auditable transcript."

### Tier B — Attested ceremony (v1.1 when signing keys exist)

Everything in Tier A, plus:

- Transcript body signed with Ed25519 using the operator capability signing key (from `setup_first_run`).
- If signing keys are absent, `ceremony_transcript --write` records `"signature": null` — treat as **Tier A**, not Tier B.
- Transcript may be published alongside GitHub Releases (operator choice).
- `python -m scripts.ceremony_transcript --verify` passes in CI after setup.

**Public claim (Tier B only):** "Verification key lineage is hash-committed and signed by the operator identity."

### Tier C — Multi-party ceremony (v1.2+, optional)

- Collaborative MPC setup (e.g. Powers of Tau + per-circuit phase 2).
- Not required for v1.1.

**Do not imply Tier C unless implemented.**

## Ceremony transcript schema

```json
{
  "transcript_version": "1.0.0",
  "ceremony_tier": "B",
  "generated_at": "ISO-8601 UTC",
  "operator_note": "optional human-readable note",
  "governance": { "...": "contents of manifest.json" },
  "entity": { "...": "contents of entity-manifest.json" },
  "content_hash": "sha256 of canonical body without signature",
  "signature": {
    "algorithm": "Ed25519",
    "signer_id": "default-capability-signer",
    "value": "base64..."
  }
}
```

## Operator workflow

```bash
# After keys exist (first-run or forced re-setup)
python -m scripts.ceremony_transcript --write --tier B --note "v1.1.0 release"
python -m scripts.ceremony_transcript --verify

# Publish verifier-only artifacts (safe to distribute)
python -m scripts.export_verifier_bundle --out dist/apxv1-verifier-bundle
```

## Third-party verification

1. Obtain attested artifact JSON (from operator).
2. Obtain verifier bundle (VKs + manifests + optional signed transcript).
3. Confirm transcript `content_hash` and signature (Tier B).
4. Run:
   ```bash
   python -m scripts.verify_attestation --real-zk path/to/artifact.json
   ```
   Or use manifests to confirm `vk_hex` in proof bundles matches on-disk VK hashes.

## Limitations (state plainly in launch materials)

- Single-party setup: a malicious operator who retained toxic waste could forge proofs for that circuit version.
- Keys on disk: no HSM integration in v1.1.
- No automated rotation: circuit version bump requires re-setup and new transcript.
- Not Powers of Tau / MPC unless Tier C is implemented.

## Related docs

- [CIRCUITS.md](CIRCUITS.md) — which circuits exist vs run on `--attest`
- [SETUP.md](SETUP.md) — trusted setup commands
- [VERIFICATION.md](VERIFICATION.md) — third-party verify paths and trust model
- [ASSUMPTIONS.md](ASSUMPTIONS.md) — what circuits prove and do not prove