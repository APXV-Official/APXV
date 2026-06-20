# APX — Phase 1 Build Plan
**Real Cryptographic Proofs (Foundation)**

**Date:** May 31, 2026  
**Status:** Draft — Awaiting explicit user confirmation before any work begins  
**Parent Document:** PRODUCTION-ROADMAP.md (Phase 1)

---

## Purpose

Phase 1 is the first major step after the successful APX v1 proof-of-concept.

**Goal:**  
Transform the current demo-level Groth16 implementation into a foundation where the ZK proofs are **production-viable and independently verifiable**.

**Exit Criteria (must be demonstrably met):**
- A third party (or separate process) can take a serialized proof + public inputs + verification key and verify it **without re-running the prover**.
- All three circuits are integrated into the prove/verify path.
- The cryptographic setup is no longer using the insecure `circuit_specific_setup` for the main flow (or the limitations are explicitly documented and accepted).
- Clear, honest documentation exists of exactly what the proofs guarantee and what they do not.

This phase does **not** include:
- Full trusted setup ceremony infrastructure (we will do the minimum viable honest path)
- LLM/agentic layers
- Production persistence or security hardening (those are Phase 2+)

---

## Non-Negotiables for Phase 1

- All new Rust code must be original (Apache-2.0, 2026 headers).
- We study patterns only from `*-proof-system/` and other legacy folders — no copying.
- We maintain strict discipline: one focused step at a time, with explicit confirmation before proceeding to the next.
- We do not declare Phase 1 complete until the exit criteria are actually demonstrated with working code and artifacts.
- The existing APX v1 code and `BUILD-PLAN.md` remain untouched as the historical record.

---

## Current State Snapshot (as of start of Phase 1)

- Only the redaction circuit is wired into `main.rs` prove/verify commands.
- `ark-serialize` is **not** present in Cargo.toml.
- Proofs are never serialized to disk in a portable format; verification is done by immediately re-running the prover in the same process.
- All three circuits exist as minimal `ConstraintSynthesizer` implementations.
- Python side still treats the ZK output as a sidecar JSON with placeholder or error data.
- Setup uses `Groth16::<Bn254>::circuit_specific_setup`.

---

## Proposed Sequential Steps for Phase 1

The following steps are proposed in strict order. Work on a step does not begin until the user explicitly confirms "Yes — proceed with Phase 1 Step X".

### Phase 1 Step 1 — Dependency & Serialization Foundation
- Add `ark-serialize` and `ark-serialize-derive` (with `derive` feature) to Cargo.toml.
- Update the three circuit structs (`RedactionProofCircuit`, `RuleBindingCircuit`, `PipelineAttestationCircuit`) to derive `CanonicalSerialize` and `CanonicalDeserialize`.
- Add necessary imports and handle any trait bound issues.
- Verify the project still compiles cleanly (`cargo check` and `cargo build`).
- Create a small test in `main.rs` that serializes and deserializes a proof in-memory.

**Success Criteria:** Project compiles with serialize support. Basic round-trip serialization of a Groth16 proof works.

### Phase 1 Step 2 — Proper Prove + Serialize + Independent Verify in Rust
- Refactor `main.rs` to support two distinct modes:
  - `prove redaction --inputs <file>` → generates proof, serializes it, writes proof + verifying key + public inputs to disk as a portable bundle.
  - `verify redaction --proof <bundle>` → loads the bundle and performs **independent verification** using only the serialized data (no re-proving).
- Implement a simple but clear "proof bundle" format (e.g., a directory or a single file containing `proof.bin`, `vk.bin`, `public_inputs.json`, and metadata).
- Remove or clearly mark the old "immediate re-prove" verify behavior.
- Ensure the other two circuits can at least be instantiated (even if not yet fully wired).

**Success Criteria:** 
- `prove` command produces a portable artifact.
- `verify` command can verify that artifact in a completely separate invocation without access to the original proving context.

### Phase 1 Step 3 — Wire All Three Circuits
- Fully integrate `RuleBindingCircuit` and `PipelineAttestationCircuit` into the CLI.
- Add commands: `prove rule-binding`, `prove pipeline`, `verify rule-binding`, `verify pipeline`.
- Create minimal but correct public input preparation for each.
- Ensure each circuit can generate a real proof and be independently verified.

**Success Criteria:** All three circuits can produce independently verifiable proofs via the Rust binary.

### Phase 1 Step 4 — Python ↔ Rust Bridge for Real Proofs
- Update `prepare_proof_inputs.py` (or create a new helper) to produce the exact public inputs expected by the new serialized flow.
- Update `run_apx.py` `--attest` path to call the new `prove` command and collect the real serialized proof bundle.
- Update `verify_attestation.py` (or add a new mode) to call the Rust `verify` command on a bundle.
- Persist the real proof bundle (or a reference to it) inside the attested artifact JSON.

**Success Criteria:** A full Python-orchestrated run with `--attest` produces a real, independently verifiable proof bundle that can be verified later via the Rust binary.

### Phase 1 Step 5 — Setup Strategy Decision & Implementation
- Decide and document the setup approach for Phase 1:
  - Option A: Keep a controlled `circuit_specific_setup` but clearly label it as "demo only" and generate a persistent proving key + verifying key that can be reused.
  - Option B: Implement a minimal one-time Powers of Tau style setup for the specific circuits (more honest but more complex).
- Implement the chosen approach so that the same verification key can be used across multiple proof generations.
- Update the bundle format to include the verification key explicitly.

**Success Criteria:** The verification key is stable and reusable. The "setup" step is no longer hidden inside every prove call.

### Phase 1 Step 6 — End-to-End Independent Verification Demonstration
- Perform a complete demonstration:
  1. Run the full Python pipeline + attest on one machine / terminal.
  2. Copy only the proof bundle (no source code, no proving key) to a second context.
  3. Successfully verify the proof using only the Rust `verify` command + the bundle.
- Capture the exact commands, artifacts, and verification result as evidence.
- Update the Python attested artifact to reference the real proof bundle location and status.

**Success Criteria:** The exit criteria of Phase 1 are met with reproducible evidence.

### Phase 1 Step 7 — Documentation & Cryptographic Statement
- Write a clear `rust/PHASE1-CRYPTO.md` (or equivalent) that states:
  - Exactly what each circuit proves.
  - The security assumptions (trusted setup model, curve, etc.).
  - Known limitations remaining after Phase 1.
  - How a third party should perform verification.
- Update `PRODUCTION-ROADMAP.md` and `README.md` with Phase 1 status.
- Add usage examples for the new prove/verify flows.

**Success Criteria:** A non-expert reader can understand what the proofs actually deliver and how to verify them independently.

### Phase 1 Step 8 — Review, Evidence, and Lock
- Collect all evidence (commands, artifacts, verification results, documentation).
- Perform an internal review against the exit criteria.
- Update this `PHASE1-PLAN.md` with actual outcomes, dates, and any deviations.
- Explicitly mark Phase 1 as complete or document what remains.
- Ask the user for final confirmation that Phase 1 goals have been met before moving to any Phase 2 discussion.

---

## Order of Operations & Discipline

- Steps are executed **strictly in order**.
- After each step, a short summary of what was done + evidence is recorded here.
- The user must give an explicit "Yes — proceed with Phase 1 Step X" before the next step begins.
- If a step reveals that the plan needs adjustment, the change is discussed and recorded before continuing.
- No scope creep into Phase 2 topics (persistence, security hardening, LLM agents, etc.) during Phase 1.

---

## Risks Specific to Phase 1

- ark-serialize integration can be non-trivial with arkworks 0.4 (feature flags, version alignment).
- Trusted setup is the most politically and technically sensitive part of any ZK system.
- The current circuits are very small and simplified — making them "real" may require strengthening the constraints themselves (not just the proving infrastructure).
- Python ↔ Rust ergonomics may need iteration.

---

## Current Proposed First Action

If the user approves this plan, the first action will be:

**"Yes — proceed with Phase 1 Step 1"**

At that point, work will begin on adding ark-serialize support and making the circuits serializable.

---

**This document is now the active control document for Phase 1.**

No code changes for Phase 1 have been made yet. All work awaits explicit confirmation.

---

*End of Phase 1 Draft Plan*