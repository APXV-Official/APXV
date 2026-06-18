# APX — Production Roadmap
**From APX v1 Proof-of-Concept to Production-Grade System with Real Proofs**

**Date:** May 31, 2026  
**Status:** Draft for user review and direction  
**Scope:** Honest assessment and proposed path forward

---

## 1. Executive Summary

APX v1 successfully proved a core thesis with a tiny, original codebase:

> Agents can be governed at runtime by living, versioned markdown artifacts, produce auditable outputs, and have those actions cryptographically attested with real (small) zero-knowledge proofs.

However, APX v1 is **not** production-ready. It is a focused research artifact. Significant work across cryptography, security, engineering, and product dimensions is required before it could be responsibly used in any real environment.

This document outlines:
- What APX v1 actually is today
- The nature of the current "agents" (addressing the LLM question)
- The major gaps to production
- A phased roadmap with clear decision points
- Specific recommendations for achieving "real proofs"

---

## 2. Current State — What We Actually Have

APX v1 (the `APX v1/` folder) contains a complete, working, minimal implementation:

- **3 living markdown specifications** (rules, workflow, knowledge) that are read at runtime.
- **3 deterministic Python agents** that consume those specifications via the governed artifact provider.
- **SqliteArtifactStore + SqliteArtifactProvider** (Phase 2) with immutable content-addressable storage.
- **3 original Rust circuits** using arkworks 0.4 (Groth16 over BN254).
- **1 Rust integration binary** that can generate and immediately verify real Groth16 proofs for the redaction circuit.
- **3 Python scripts** that orchestrate the full pipeline and bridge to the Rust prover.
- Multiple generated attested artifacts demonstrating end-to-end flow, including governance decisions and provenance hashes.

**All code is original.** The 8-step locked plan was fully executed. Step 8 formally concluded that the small version proves the idea is worth continuing.

**What it is not:**
- Not a product
- Not secure for real data
- Not using production-grade cryptographic setup
- Not using portable proofs
- Not using any form of machine learning or generative AI

---

## 3. The Nature of the "Agents" (LLM Question)

**The three agents in APX v1 (APX-AGENT-001, 002, 003) are NOT LLM-based agents.**

They are **deterministic, rule-governed execution units** written in plain Python. Their entire behavior is defined by:

- The content of the three markdown files they read fresh on every run.
- Fixed logic in the Python code (regex-based redaction, simple if/else governance rules derived from the knowledge file).

There is **no**:
- OpenAI, Anthropic, Ollama, or any other LLM call
- Tool use / function calling
- Reasoning loops or chain-of-thought
- Generative text output
- Autonomous decision making beyond the rules explicitly written in markdown

### Why This Design for v1?

This was a deliberate and correct scoping decision:

1. **Prove the governance + attestation layer first** on top of predictable, auditable behavior.
2. **Avoid confounding variables** — if the system had used LLMs, it would have been impossible to know whether problems were caused by the governance model or by the non-determinism and hallucination risks of generative models.
3. **Keep the experiment tiny** ("exactly 3 of everything").

### Historical Context

The larger folders in this workspace (`CILAS v1.0.0/`, `AXP/`, `AXP1/`) contain earlier experiments with LLM-backed agents (Ollama bridges, agent routing, report generation, etc.). Those approaches had real value but also introduced significant complexity around non-determinism, cost, latency, and auditability.

APX v1 deliberately stripped that layer away to test the foundational "managed artifacts + cryptographic attestation" idea in isolation.

### Implications for Production

For a real production system, there are two viable paths (not mutually exclusive):

**Path A — Strong Deterministic Core (Recommended starting point)**
- Keep the current style of governed, deterministic agents for high-stakes, auditable operations (redaction, compliance, data transformation, financial logic, etc.).
- These agents are easy to attest, easy to audit, and produce consistent results.

**Path B — Hybrid Agentic Layer (Add later)**
- Introduce LLM-powered or tool-using agents for more open-ended reasoning, research, summarization, or orchestration tasks.
- These agents would still be required to operate **under** the same governance and attestation framework (they would call the deterministic governed agents or produce artifacts that go through the same attestation pipeline).
- This is significantly harder and should be built on top of a solid Path A foundation.

**Recommendation:** Do not add LLMs until the deterministic governed core + real proofs are solid. Adding generative agents too early tends to destroy auditability.

---

## 4. Major Gap Areas to Production

### 4.1 Cryptographic Hardening (Highest Priority for "Real Proofs")

- Replace `circuit_specific_setup` with a proper trusted setup (Powers of Tau + MPC ceremony or a universal setup scheme).
- Add `ark-serialize` / `ark-serialize-derive` for real proof and verification key serialization.
- Implement independent verification (not just "re-prove and check").
- Wire the other two circuits (`rule_binding` and `pipeline_attestation`) into the production prove/verify path.
- Design a verification key distribution and versioning strategy.
- Consider proof aggregation or recursion if the number of attestations grows.
- Add formal or semi-formal circuit review / constraint soundness analysis.

### 4.2 Agent Model Evolution

- Decide on the long-term agent architecture (pure deterministic vs hybrid with LLM agents).
- If adding LLM agents: define strict boundaries, sandboxing, output validation, cost controls, and how their outputs still flow through the attestation system.
- Build a proper `IArtifactProvider` interface (the current `MinimalArtifactProvider` is intentionally tiny).
- Add support for agent versioning, capability declarations, and signed agent code/artifacts.

### 4.3 Infrastructure & Persistence

- Replace local JSON file artifacts with a real (versioned, queryable) store (PostgreSQL + object storage, or a proper artifact database).
- Add full audit logging and tamper-evidence for the managed layer.
- Implement proper artifact lifecycle (retention, redaction of artifacts themselves, legal hold).
- Build or integrate a real workflow engine (the current `APX-WF-001` is a markdown description only).

### 4.4 Security & Compliance

- Formal threat model (what are we protecting against?).
- Input validation, rate limiting, and abuse resistance.
- Secure key management for any signing or ceremony participation.
- Access control and authentication around the managed specifications.
- Data classification and handling rules (the current redaction is a toy).
- Compliance story (SOC 2, GDPR, HIPAA, etc. depending on target use cases).

### 4.5 Engineering & Operations

- Stable binary interface between Python and Rust (or move to a single language / WASM approach).
- Proper packaging, distribution, and installation story.
- Observability, metrics, tracing, and alerting.
- CI/CD, automated testing (including property-based testing of circuits), and regression harnesses.
- Error handling, retries, and graceful degradation across the entire stack.
- Performance and scalability characterization.

### 4.6 Product & Governance

- Clear product positioning and target users.
- Governance model for who can change rules/workflows/knowledge and how those changes are approved and attested.
- Multi-tenancy and isolation model.
- SLAs, support, and operational runbooks.
- Licensing, commercial model, and IP strategy.

---

## 5. Proposed Phased Roadmap

### Phase 0 — Current (APX v1)
Status: Complete.  
Purpose: Prove the core idea is viable with minimal code.  
Outcome: Successful.

### Phase 1 — Real Cryptographic Proofs (Foundation)
Goal: Make the ZK proofs production-viable and independently verifiable.

Key deliverables:
- Proper trusted setup process (or switch to a scheme with better setup properties).
- Full proof serialization + independent verification.
- All three circuits integrated and exercised in the end-to-end flow.
- Basic verification key management and distribution.
- Clear documentation of the cryptographic guarantees and limitations.

Exit criteria: A third party can take a proof + public inputs + verification key and verify it without re-running the prover.

### Phase 2 — Hardened Governed Core
Goal: Make the deterministic agent + artifact system trustworthy for real (non-public) data.

Key deliverables:
- Production-grade `IArtifactProvider` + persistence layer.
- Full audit trail and tamper-evidence for specifications and artifacts.
- Security review of the redaction logic and governance rules.
- Agent capability model and versioning.
- Basic access control and authentication.

Exit criteria: The system can be run against real internal data with acceptable risk under a defined threat model.

### Phase 3 — Agentic / LLM Layer (Optional but Likely)
Goal: Add more powerful reasoning agents without destroying auditability.

Key deliverables:
- Sandboxed LLM agent runtime with strict output contracts.
- Integration points where LLM agents must call governed deterministic agents or produce attestable artifacts.
- Cost, latency, and quality controls.
- Governance rules specifically for agentic behavior (what LLMs are allowed to decide vs what must be escalated to deterministic governed paths).

Exit criteria: LLM-powered workflows can be used safely for appropriate tasks while high-stakes operations remain under strong deterministic governance + attestation.

### Phase 4 — Production Hardening & Packaging
Goal: Make the system operable, supportable, and distributable.

Key deliverables:
- Packaging, deployment, and upgrade story.
- Full observability stack.
- Operational tooling (key ceremony tools, artifact inspection, governance change tooling).
- Compliance documentation and controls.
- Performance and scalability work.

### Phase 5 — Ecosystem & Scale (Future)
- Multi-party attestation / shared proofs.
- On-chain verification options.
- External auditor / regulator tooling.
- Marketplace or shared rule libraries (with their own attestation).

---

## 6. Specific Recommendations for "Real Proofs"

If the immediate priority is moving from "demo Groth16" to "real, usable proofs":

1. **Add ark-serialize** to Cargo.toml and implement proper `Proof` and `VerifyingKey` serialization for BN254 Groth16.
2. **Decide on setup strategy** — either:
   - Run a real (even if small) Powers of Tau ceremony for the specific circuits, or
   - Move to a universal setup scheme (Plonk, Marlin, etc.) if the circuit set is expected to grow.
3. **Implement independent verification** in both the Rust binary and a Python verifier (using `ark-groth16` verify on deserialized data).
4. **Wire rule_binding and pipeline_attestation** circuits into the CLI and Python orchestration.
5. **Design a simple verification key + proof bundle format** (e.g., a small JSON + binary artifact) that can be handed to an auditor.
6. **Document the exact security model** (what the proofs actually prove and what they do not).

This work alone is probably 4–8 weeks for an experienced Rust + ZK engineer, assuming no major changes to the circuit designs.

---

## 7. Risks & Open Questions

- How much cryptographic rigor is actually required for the intended use cases?
- Will the primary value be in the deterministic governed core or in the future agentic/LLM capabilities?
- What is the target deployment model (internal tool, SaaS, on-prem appliance, embedded in other systems)?
- Who will perform the trusted setup / ceremony, and how will it be audited?
- How will governance changes to the living markdown specifications be controlled and attested in production?
- Is there a desire to keep the "tiny and understandable in one sitting" philosophy, or is the system allowed to grow significantly more complex?

---

## 8. Next Decision Points

This document is intentionally a **roadmap proposal**, not a locked build plan.

Before any substantial work begins, the following decisions are needed:

1. **Priority** — Is the next focus "make the proofs real" (Phase 1), "harden the governed core" (Phase 2), or "explore the LLM/agentic layer"?
2. **Scope philosophy** — Do we want to keep future slices relatively small and sequential (like the v1 approach), or move to a more traditional large project structure?
3. **Team / ownership** — Who will do the cryptographic work? The security review? The infrastructure?
4. **Success criteria** — What does "good enough for production use" actually mean for the first real deployment?

---

**End of Draft Roadmap**

This document is ready for review and discussion. No work described here has been started. All further action requires explicit user direction and confirmation.

---

*APX v1 remains the clean, minimal reference implementation. This roadmap is additive and does not modify the historical record in `BUILD-PLAN.md`.*
