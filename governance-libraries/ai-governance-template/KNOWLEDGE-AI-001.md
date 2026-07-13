# KNOWLEDGE-AI-001 — AI Governance Knowledge Base

**Version:** 0.1.0  
**Last Updated:** 2026-06-10

## Purpose
This document defines key terms, concepts, and supporting knowledge used by the AI Governance Template (`RULE-AI-001` and `WORKFLOW-AI-001`).

## Definitions

### Agentic Component
Any LLM-powered or tool-using agent that operates within an APX-governed environment (e.g., `LLMReasoner`, `ToolUser`).

### Governance Rule
A formal, machine-readable constraint defined in a rule file that agentic components must respect.

### Human Review Trigger
A condition (confidence, cost, latency, rule violation, or decision category) that requires human oversight before a decision can be finalized.

### Confidence Score
A numeric value between 0.0 and 1.0 representing the agent’s estimated certainty in its decision.

### Sandbox
A controlled execution environment that enforces time, cost, and resource limits on agentic components.

### AgenticOutput
The mandatory structured output format defined in the `AgenticContract`. All agentic components must return this format.

### Cryptographic Attestation
A verifiable Groth16 proof that a process followed specific governance rules at the time of execution.

## Decision Categories Requiring Heightened Scrutiny

- Credit and lending decisions
- Hiring and employment-related decisions
- Medical or healthcare-related decisions
- Legal or regulatory compliance decisions
- High financial value transactions

## Escalation Principles

When a human review trigger is activated, the system must:
1. Block finalization of the decision.
2. Package the full reasoning, input context, and governance state.
3. Log the escalation event.
4. Await explicit human approval before proceeding.

---

*This knowledge base supports consistent interpretation and enforcement of AI governance rules.*