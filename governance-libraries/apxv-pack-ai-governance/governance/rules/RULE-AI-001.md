# APXV1 — Rule Set AI: Governed Agentic Decisions

**Rule ID:** APX-RULE-AI-001  
**Version:** 0.1.0  
**Effective Date:** 2026-06-28  
**Purpose:** Mandatory constraints for LLM-powered and tool-using agents in APX-governed pipelines.

---

## 1. Scope

Applies to **APX-AGENT-LLM-001** (`LLMReasoner`) and hybrid workflows that delegate reasoning to agentic components.

## 2. Human review

- **human_review_required** for all high-stakes categories (credit, hiring, legal, medical).
- Decisions with confidence below **0.75** must be escalated to `REVIEW_REQUIRED`.

## 3. Cost and latency

- No single agentic decision may exceed **$0.05 USD** without explicit human approval.
- No agentic decision may exceed **5,000 ms** execution time; timeouts escalate to human review.

## 4. Governance enforcement

- Agents must load and respect the active governance rule set before making decisions.
- Any decision that would violate a loaded governance rule must be blocked or overridden to the safest compliant action (`REVIEW_REQUIRED`).

## 5. Audit and provenance

- Every agentic action must be logged via `AuditLogger`.
- All outputs must be written through `FileArtifactProvider` with full provenance metadata.

## 6. Compliance policy

- AI-governed redaction pipelines must set **compliance policy id 4** (AI governance / regulated metadata) on the attested artifact.