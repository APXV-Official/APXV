# APXV — Knowledge Base AI: Agentic Governance

**Knowledge ID:** APXV-KB-AI-001  
**Version:** 0.1.0  
**Effective Date:** 2026-06-28

---

## Compliance policy ids (entity circuit)

| ID | Name | When to use |
|----|------|-------------|
| 1 | Standard redaction | Single-document reference pipeline |
| 2 | Batch document handling | Document Processing Pack |
| 3 | Voice redaction | Voice privacy pipeline |
| 4 | AI governance / regulated metadata | **This pack** — LLM review on redacted content |
| 5 | Custom enterprise | Reserved |

This pack sets **policy id 4** on `output.compliance_policy_id` and the attested result.

## Definitions

### Agentic component

Any LLM-powered or tool-using agent operating within APX (e.g. `LLMReasoner`, `ToolUser`).

### Human review trigger

Confidence below 0.75, cost above $0.05, latency timeout, governance rule violation, or high-stakes decision category.

### AgenticOutput

Mandatory structured output from the `AgenticContract`. All agentic components return this format.

## High-stakes categories

- Credit and lending
- Hiring and employment
- Medical or healthcare
- Legal or regulatory compliance
- High financial value transactions

## Acceptance

A successful AI governance demo must report `final_status=ATTESTED`, `llm_decision` in (`APPROVED`, `REVIEW_REQUIRED`, `REJECTED`), `compliance_policy_id=4`, and `total_redactions>=1`.