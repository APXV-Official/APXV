# APXV1 — Cryptographic Assumptions Document

**Status:** Phase 1 Criterion #5 — Living Document  
**Date:** 2026-06-17  
**Circuit Version:** 1.1.0

---

## 1. What Each Circuit Actually Proves

### 1.1 Redaction Circuit (`redaction_proof.rs`)

**Claim:** A redaction operation changed content (original hash ≠ redacted hash) with a non-zero redaction count, and the transformation is bound to that count.

**Public Inputs:**
- `original_hash` — SHA-256 of pre-redaction data
- `redacted_hash` — SHA-256 of post-redaction data
- `redaction_count` — number of redactions applied

**Constraints enforced (v1.1.0):**
1. `redaction_count ≠ 0` (multiplicative inverse witness)
2. `original_hash ≠ redacted_hash` (diff has multiplicative inverse)
3. `(original - redacted) × count` witness binding

**Does NOT prove:**
- Redaction rules were semantically correct
- Specific fields were redacted correctly
- Python redaction code was bug-free

### 1.2 Rule Binding Circuit (`rule_binding.rs`)

**Claim:** A non-zero rule hash was in force during a non-zero-count redaction, bound to a specific redaction proof commitment.

**Public Inputs:**
- `rule_hash` — hash of APX-RULE-001
- `redaction_proof_hash` — SHA-256 commitment to the redaction proof bundle
- `redaction_count` — redactions performed

**Constraints enforced (v1.1.0):**
1. `redaction_count ≠ 0`
2. `rule_hash ≠ 0`
3. `rule_hash × count + redaction_proof_hash` witness binding

**Does NOT prove:**
- The rule was correctly authored or authorized
- Redaction logic followed the rule's semantics

### 1.3 Pipeline Attestation Circuit (`pipeline_attestation.rs`)

**Claim:** A three-agent pipeline executed under specific governance artifacts with a non-zero governance decision and non-zero provenance chain.

**Public Inputs:**
- `rule_hash`, `workflow_hash`, `knowledge_hash`
- `final_governance_decision` (32-byte hex-encoded field element)
- `agent_chain_hash` (full provenance hash)

**Constraints enforced (v1.1.0):**
1. `final_governance_decision ≠ 0`
2. `agent_chain_hash ≠ 0`
3. `rule + workflow + knowledge` witness sum binding
4. `specs_sum × governance + agent_chain_hash` attestation binding

**Does NOT prove:**
- Individual agent decisions were fair or correct
- LLM reasoning (LLM agents are not in the main pipeline)
- Governance artifacts were the latest approved versions

---

## 2. Trusted Setup Assumptions

**Model:** Single-party honest setup (Phase 1)

**Process:** See `docs/cryptography/SETUP.md`

**Assumptions:**
- Setup operator is honest and destroys toxic waste
- Persisted keys in `rust/keys/` are not tampered with after creation
- `manifest.json` accurately records VK hashes for the active circuit version
- Verifier uses the VK matching the proof bundle's `vk_hex` and manifest entry

**Limitations:**
- Not a multi-party ceremony
- Malicious setup operator could forge proofs if toxic waste is retained
- No HSM protection for proving keys

---

## 3. Known Limitations and Attack Surface

1. **Single-party setup risk** — see Section 2
2. **Public input binding only** — circuits bind supplied hashes, not real-world data
3. **No semantic enforcement** — rules/workflows are hash-bound, not logic-proven
4. **Minimal circuits** — constraints are meaningful but not full program proofs
5. **No key rotation** — compromised setup requires manual re-setup and re-attestation
6. **LLM periphery** — simulated LLM agents are outside the attested main pipeline

---

## 4. What Would Constitute a Forgery

A forgery is a verifying Groth16 proof where:

- Public inputs do not correspond to actual APX execution, but satisfy circuit constraints
- A malicious setup party uses retained toxic waste to create proofs for arbitrary inputs
- A tampered VK is substituted (detected by manifest VK integrity checks when manifest is trusted)
- An attacker replays a valid proof bundle against different claimed execution context (mitigated by binding public inputs to artifact content)

---

## 5. Phase 1 Exit Criteria Status

| Criterion | Status |
|-----------|--------|
| #1 Honest trusted setup | Implemented — `setup_zk`, persisted keys |
| #2 Circuit hardening | Implemented — v1.1.0 witness-bound constraints |
| #3 Independent verifiability | Implemented — `verify_attestation --real-zk`, `apx_verify_bundle` |
| #4 VK integrity & lifecycle | Implemented — `manifest.json`, VK hash checks |
| #5 This document | Active |
| #6 Reproducible demonstration | Verified via `run_apx --attest` + `verify_attestation --real-zk` |
| #7 No overstated claims | README and docs state research-prototype status |

---

**This is a living document.** Update when circuit version, setup model, or proof claims change.