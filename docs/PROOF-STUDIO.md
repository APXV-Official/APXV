# APXV Proof Studio

Operators customize **what runs prove** using Proof Profiles. They do **not** author Groth16 circuits.

## Loop (same as Agents / Packs)

1. **Studio → Proofs** — pick catalog predicates (or a template)
2. **Save** — writes `managed/studio/proofs/<id>/` (`intent.md`, `proof-spec.json`, `manifest.json`)
3. **Test** — runs a real reference composition on the runtime and evaluates the claim
4. **Promote** — appears on Workbench shelf **Proofs**
5. **Workbench** — click a proof profile to set `defaults.proof_profile`, Save, Run
6. **Runs / Trust** — job result includes `proof_claim` (English + per-predicate results)

## Honesty

| You customize | You do not customize |
|---------------|----------------------|
| Intent language | R1CS / circuit equations |
| Predicate selection + thresholds | Trusted setup ceremony params |
| Fail-closed | Arbitrary free-form computation ZK |

### Bindings (real)

| Binding | Meaning |
|---------|---------|
| `existing-dual-track` | Evaluate claim against run artifacts; dual-track proofs when `attest` |
| `universal-predicate-v1` | Same claim evaluation **plus** a real Groth16 proof in `apxv-zk` |

Setup:

```bash
python -m scripts.setup_universal_zk
# or from rust/apxv-zk:
cargo run --release -p apxv-zk -- setup universal-predicate-v1
```

When keys exist, successful claims auto-attach `universal_predicate_proof` (prove + independent verify).

## API (v2)

| Method | Path |
|--------|------|
| GET | `/api/v2/studio/proofs` |
| POST | `/api/v2/studio/proofs` |
| GET | `/api/v2/studio/proofs/catalog` |
| GET | `/api/v2/studio/proofs/templates` |
| POST | `/api/v2/studio/proofs/from-template` |
| POST | `/api/v2/studio/proofs/compile-intent` |
| POST | `/api/v2/studio/proofs/from-intent` |
| GET | `/api/v2/studio/proofs/status` |
| POST | `/api/v2/studio/proofs/export-claim` |
| POST | `/api/v2/studio/proofs/{id}/test` |
| POST | `/api/v2/studio/proofs/{id}/promote` |
| GET | `/api/v2/studio/shelf` → includes `proofs[]` |

### Intent (P2)

Type English in Studio → **Compile intent** / **Save from intent**. Deterministic keyword rules map to the catalog only (fail closed outside catalog).

Run with profile:

```http
POST /api/v2/pipelines/{id}/run
{ "input_text": "...", "proof_profile": "APXV-PROOF-REDACTION-CORE" }
```

Or set on the pipeline document:

```yaml
defaults:
  attest: false
  proof_profile: APXV-PROOF-REDACTION-CORE
```

## Templates

- `APXV-PROOF-REDACTION-CORE` — redaction + rule + chain + attested + governance
- `APXV-PROOF-ENTITY-MIN` — entity count and categories
- `APXV-PROOF-FULL-ATTEST` — structural + governance/entity ZK present (`require_attest`)

## Fail closed

If any selected predicate fails and `fail_closed: true` (default), the run’s `final_status` is `failed` with a clear `proof_claim.failed_predicates` list. No silent success.
