# APXV — Workflow AI: Governed LLM Decision Path

**Workflow ID:** APXV-WF-AI-001  
**Version:** 0.1.0  
**Effective Date:** 2026-06-28

---

## Purpose

Standard workflow for redaction followed by governed LLM review and attestation.

## Steps

### Step 1: Load governance context

Load `APXV-RULE-AI-001`, `APXV-WF-AI-001`, and `APXV-KB-AI-001`. Verify agent capabilities for APXV-AGENT-001, 002, 003, and APXV-AGENT-LLM-001.

### Step 2: Redact governed input

Run **APXV-AGENT-001** (`RuleGovernedRedactor`) on the input text. Produce entities, hashes, and redacted output.

### Step 3: LLM governance review

Run **APXV-AGENT-LLM-001** (`LLMReasoner`) under sandbox cost, latency, and timeout limits. Record decision, confidence, cost, and latency in `AgenticOutput` format.

### Step 4: Apply governance rules

If any rule would be violated (including `human_review_required`), override the LLM decision to `REVIEW_REQUIRED`.

### Step 5: Orchestrate and package

Run **APXV-AGENT-002** to package the proposed artifact. Attach `llm_governance` metadata and set `compliance_policy_id: 4`.

### Step 6: Attest

Run **APXV-AGENT-003** to produce the final attested result with full provenance.

### Step 7: Escalate if required

If the LLM decision is `REVIEW_REQUIRED`, block finalization of high-stakes actions until human review completes.