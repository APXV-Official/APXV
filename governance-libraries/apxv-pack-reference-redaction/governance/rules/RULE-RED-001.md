# APXV — Rule Set 1: Controlled Redaction

**Rule ID:** APXV-RULE-001  
**Version:** 1.0.0  
**Effective Date:** 2026-05-31  
**Purpose:** Define the minimum redaction behavior that any APXV agent must follow when processing sensitive text.

---

## 1. Core Redaction Rules

When processing any input text, the agent **must** apply the following redactions in order:

1. **Email Addresses**  
   - Pattern: Any string matching standard email format (e.g., `user@domain.com`)
   - Replacement: `[REDACTED-EMAIL]`

2. **Phone Numbers**  
   - Pattern: Sequences of 10+ digits that resemble phone numbers (with or without formatting)
   - Replacement: `[REDACTED-PHONE]`

3. **Social Security Numbers (SSN)**  
   - Pattern: `XXX-XX-XXXX` or any 9-digit sequence that appears to be an SSN
   - Replacement: `[REDACTED-SSN]`

4. **Credit Card Numbers**  
   - Pattern: 13–19 digit sequences that pass basic Luhn-like structure
   - Replacement: `[REDACTED-CC]`

5. **Names in Context** (when explicitly flagged)  
   - If the input or workflow indicates "redact personal names", replace full names with `[REDACTED-NAME]`

---

## 2. Redaction Behavior Requirements

- Redactions must be **deterministic** — the same input + same rule version must always produce the same redacted output.
- The agent **must not** invent additional redaction categories beyond this rule set unless a higher-priority workflow explicitly authorizes it.
- All redactions must be **logged** in the output artifact metadata (see Workflow 1).
- If the input contains no sensitive data matching these rules, the agent must explicitly state: "No redactions applied per APXV-RULE-001."

---

## 3. Governance & Override

- This rule set can only be modified by updating this markdown file and incrementing the version.
- Agents must re-read this file on every execution (no caching of rules across runs in APXV).
- If a workflow or knowledge file conflicts with this rule set, **this rule set takes precedence** unless the workflow carries an explicit "RULE-OVERRIDE" marker (not supported in APXV baseline).

---

## 4. Verification Notes (for Attestation)

When generating cryptographic attestation for an output, the proof system should be able to reference:
- The exact Rule ID and Version used (`APXV-RULE-001 v1.0.0`)
- The list of redaction categories that were actually triggered
- The hash of this rule file at the time of execution (to prove the agent followed this specific version)

---

**End of Rule Set APXV-RULE-001**

This file is the active source of truth for redaction behavior in APXV.
