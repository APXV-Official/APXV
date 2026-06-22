# APXV1 — ZK Ceremony Transparency (v1.1)

APXV1 uses Groth16 with a **one-time trusted setup** per circuit. This document describes ceremony tiers, transparency artifacts, and the trust model for v1.1.0.

## Trust model

| Scenario | Trust boundary |
|----------|----------------|
| **Self-hosted** — run `setup_first_run`, generate your own keys, attest your data | You trust your own setup and key handling |
| **Verify release artifacts** — use a published verifier bundle and matching VKs | You trust the publisher's one-time setup for those verification keys |

Groth16 verification checks proof validity cryptographically. Trusted-setup honesty is a separate assumption. v1.1.0 uses **single-party setup** — not a multi-party ceremony.

Tier A and Tier B document verification-key lineage. They do not provide the guarantees of collaborative trusted setup (a future Tier C capability).

## Tiers

### Tier A — Manifest commitment

- Trusted setup runs locally (`setup_first_run` or per-circuit setup).
- **Manifests** record VK and PK SHA-256 hashes and circuit versions:
  - `rust/apx-circuits/keys/manifest.json`
  - `rust/apx-zk/keys/entity-manifest.json`
- **Ceremony transcript** (`managed/config/ceremony-transcript.json`) optionally aggregates both manifests with metadata.
- **Verifier bundle** exports VK files and manifests only (no proving keys).

Provides hash-committed verification-key lineage and an auditable record of which keys were active.

### Tier B — Signed transcript

Everything in Tier A, plus:

- Transcript body signed with Ed25519 using the capability signing key from `setup_first_run`.
- If signing keys are absent, `ceremony_transcript --write` records `"signature": null` — this is **Tier A**, not Tier B.
- Signed transcripts may be distributed with release artifacts.

Adds a signature binding the transcript to a deployment identity.

### Tier C — Multi-party ceremony (future)

Collaborative MPC trusted setup is not included in v1.1.0.

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

## Generating a ceremony transcript

```bash
# After keys exist (first-run or forced re-setup)
python -m scripts.ceremony_transcript --write --tier B --note "v1.1.0"
python -m scripts.ceremony_transcript --verify

# Export verifier-only artifacts (safe to distribute)
python -m scripts.export_verifier_bundle --out dist/apxv1-verifier-bundle
```

## Verifying release artifacts

1. Obtain the attested artifact JSON.
2. Obtain the verifier bundle (VKs, manifests, and optional signed transcript).
3. Confirm transcript `content_hash` and signature when Tier B applies.
4. Run:
   ```bash
   python -m scripts.verify_attestation --real-zk path/to/artifact.json
   ```
   Or compare artifact `vk_hex` values to VK hashes in the bundle manifests.

## Limitations

- **Single-party setup** — a party that retained setup entropy could forge proofs for that circuit version.
- **Keys on disk** — no HSM integration in v1.1.0.
- **No automated rotation** — circuit version changes require re-setup and a new transcript.
- **Scope** — v1.1.0 documents VK lineage; it does not cryptographically prove setup entropy was destroyed.

## Related docs

- [CIRCUITS.md](CIRCUITS.md) — which circuits exist vs run on `--attest`
- [SETUP.md](SETUP.md) — trusted setup commands
- [VERIFICATION.md](VERIFICATION.md) — independent verification paths
- [ASSUMPTIONS.md](ASSUMPTIONS.md) — what circuits prove and do not prove