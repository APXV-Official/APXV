# APX v1 — Knowledge 1: Redaction Examples, Edge Cases & Definitions

**Knowledge ID:** APX-KB-001  
**Version:** 1.0.0  
**Effective Date:** 2026-05-31  
**Supports:** APX-RULE-001 and APX-WF-001  
**Purpose:** Provide concrete examples, clarifications, and definitions so agents can apply the redaction rules and workflow consistently and correctly.

---

## 1. Example Redactions

### Example 1 — Standard Email
**Input:**  
"Please contact john.doe@company.com for more information."

**Output (per APX-RULE-001):**  
"Please contact [REDACTED-EMAIL] for more information."

### Example 2 — Phone Number
**Input:**  
"Call me at (555) 123-4567 tomorrow."

**Output:**  
"Call me at [REDACTED-PHONE] tomorrow."

### Example 3 — SSN
**Input:**  
"Social Security Number: 123-45-6789"

**Output:**  
"Social Security Number: [REDACTED-SSN]"

### Example 4 — Credit Card
**Input:**  
"Payment with card 4111 1111 1111 1111 was successful."

**Output:**  
"Payment with card [REDACTED-CC] was successful."

### Example 5 — Mixed Sensitive Data
**Input:**  
"User Jane Smith (jane.smith@email.com, 555-987-6543, SSN 987-65-4321) used card 5555-5555-5555-4444."

**Output:**  
"User [REDACTED-NAME] ([REDACTED-EMAIL], [REDACTED-PHONE], SSN [REDACTED-SSN]) used card [REDACTED-CC]."

---

## 2. Edge Cases & Clarifications

- **Partial Matches**: If only part of a pattern appears (e.g., "john@company" without .com), do **not** redact unless it clearly matches the full pattern defined in the rule.
- **False Positives**: When in doubt, prefer **not redacting** over incorrectly redacting non-sensitive data. Log the decision in metadata.
- **International Formats**: Phone numbers in non-US formats (e.g., +44 20 7946 0958) should still be redacted if they appear to be contact numbers.
- **Names**: Only redact names when the input or workflow explicitly requests "redact personal names". Do not assume all capitalized words are names.
- **Already Redacted Text**: If input already contains `[REDACTED-...]` markers, leave them untouched.
- **Multiple Occurrences**: Redact every instance independently. Do not stop after the first match.

---

## 3. Definitions

- **Deterministic Redaction**: The same input text + same rule version must always produce identical redacted output and identical metadata.
- **Sensitive Data**: Any information that matches one of the categories explicitly listed in APX-RULE-001.
- **Artifact Metadata**: Structured data attached to every output artifact that records rule version, redactions performed, hashes, timestamps, and workflow used.
- **Attestation Package**: The minimal set of data submitted to the proof system (rule hash, input hash, output artifact ID, redactions list, workflow ID).

---

## 4. Recommended Agent Behavior

When applying this knowledge:
- Always load the latest version of this knowledge file at the start of execution.
- When uncertain about a potential match, document the uncertainty in the artifact metadata.
- Prefer explicit, conservative redaction over aggressive redaction.
- The goal is **consistent, auditable, and defensible** redaction — not maximum redaction.

---

## 5. Test Cases for Validation (APX v1 Baseline)

These cases can be used to verify that an agent correctly implements the rule + workflow:

1. Input with no sensitive data → "No redactions applied per APX-RULE-001."
2. Input with one email only.
3. Input with overlapping patterns (email inside a sentence with a phone number).
4. Input containing already-redacted markers.
5. Input that triggers all five redaction categories.

---

**End of Knowledge APX-KB-001**

This knowledge base, combined with rule1.md and workflow1.md, forms the complete active specification for redaction behavior in APX v1.
