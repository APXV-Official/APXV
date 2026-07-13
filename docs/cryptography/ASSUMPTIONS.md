# APXV — Cryptographic Assumptions

**Circuit version:** 1.1.0  
**Ceremony:** Tier A/B (manifest transcript + verifier bundle; Ed25519 signature when signing keys exist)

---

## 1. What Each Circuit Proves

### 1.1 Redaction Circuit (`redaction_proof.rs`)

**Proves:** A redaction operation changed content (original hash ≠ redacted hash) with a non-zero redaction count, and the transformation is bound to that count.

**Public inputs:**
- `original_hash` — SHA-256 of pre-redaction data
- `redacted_hash` — SHA-256 of post-redaction data
- `redaction_count` — number of redactions applied

**Constraints enforced (v1.1.0):**
1. `redaction_count ≠ 0` (multiplicative inverse witness)
2. `original_hash ≠ redacted_hash` (diff has multiplicative inverse)
3. `(original - redacted) × count` witness binding

**Does not prove:**
- Redaction rules were semantically correct
- Specific fields were redacted correctly
- Python redaction code was bug-free

### 1.2 Rule Binding Circuit (`rule_binding.rs`)

**Proves:** A non-zero rule hash was in force during a non-zero-count redaction, bound to a specific redaction proof commitment.

**Public inputs:**
- `rule_hash` — hash of APX-RULE-001
- `redaction_proof_hash` — SHA-256 commitment to the redaction proof bundle
- `redaction_count` — redactions performed

**Constraints enforced (v1.1.0):**
1. `redaction_count ≠ 0`
2. `rule_hash ≠ 0`
3. `rule_hash × count + redaction_proof_hash` witness binding

**Does not prove:**
- The rule was correctly authored or authorized
- Redaction logic followed the rule's semantics

### 1.3 Pipeline Attestation Circuit (`pipeline_attestation.rs`)

**Proves:** A three-agent pipeline executed under specific governance artifacts with a non-zero governance decision and non-zero provenance chain.

**Public inputs:**
- `rule_hash`, `workflow_hash`, `knowledge_hash`
- `final_governance_decision` (32-byte hex-encoded field element)
- `agent_chain_hash` (full provenance hash)

**Constraints enforced (v1.1.0):**
1. `final_governance_decision ≠ 0`
2. `agent_chain_hash ≠ 0`
3. `rule + workflow + knowledge` witness sum binding
4. `specs_sum × governance + agent_chain_hash` attestation binding

**Does not prove:**
- Individual agent decisions were fair or correct
- LLM reasoning (LLM agents are not in the main pipeline)
- Governance artifacts were the latest approved versions

---

## 2. Trusted Setup Assumptions

**Model:** Single-party setup with Tier A/B transparency (v1.1.0)

**Process:** See [SETUP.md](SETUP.md) and [CEREMONY.md](CEREMONY.md)

### Trust boundaries

| Deployment | Setup trust |
|------------|-------------|
| You run `setup_first_run` on your own host | You trust your own setup |
| You verify artifacts from a published release | You trust the publisher's one-time setup for those VKs |

Tier A commits VK hashes in manifests and an optional ceremony transcript. Tier B adds an Ed25519 signature on that transcript when signing keys exist. A verifier bundle lets third parties check VK lineage. None of this cryptographically proves setup entropy was destroyed.

**Assumptions:**
- The setup party was honest and discarded setup entropy
- Persisted keys in `rust/apxv-circuits/keys/` and `rust/apxv-zk/keys/` are not tampered with after creation
- Manifests accurately record VK hashes for the active circuit version
- Verifiers use the VK matching the proof bundle's `vk_hex` and manifest entry
- Ceremony transcript `content_hash` matches on-disk manifests when a transcript is used

**Limitations:**
- Single-party setup only in v1.1.0 (multi-party ceremony is a future capability)
- A dishonest setup party could forge proofs if setup entropy was retained
- No HSM protection for proving keys

---

## 3. Known Limitations and Attack Surface

1. **Single-party setup risk** — see Section 2
2. **Public input binding only** — circuits bind supplied hashes, not real-world data
3. **No semantic enforcement** — rules and workflows are hash-bound, not logic-proven
4. **Minimal circuits** — constraints are meaningful but not full program proofs
5. **No key rotation** — compromised setup requires manual re-setup and re-attestation
6. **LLM periphery** — simulated LLM agents are outside the attested main pipeline

---

## 4. What Would Constitute a Forgery

A forgery is a verifying Groth16 proof where:

- Public inputs do not correspond to actual APX execution, but satisfy circuit constraints
- A setup party used retained setup entropy to create proofs for arbitrary inputs
- A tampered VK is substituted (detected by manifest VK integrity checks when the manifest is trusted)
- An attacker replays a valid proof bundle against different claimed execution context (mitigated by binding public inputs to artifact content)

---

For which entity circuits run on the default attest path, see [CIRCUITS.md](CIRCUITS.md).

Update this document when circuit version, setup model, or proof claims change.