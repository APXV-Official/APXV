# APXV — Workflow 1: Rule-Governed Text Processing & Attestation

**Workflow ID:** APXV-WF-001  
**Version:** 1.0.0  
**Effective Date:** 2026-05-31  
**Depends On:** APXV-RULE-001 (Controlled Redaction)  
**Purpose:** Define the exact sequence any APXV-governed agent must follow when processing text under governance.

---

## 1. Workflow Overview

This workflow enforces a strict, auditable process for handling sensitive text:

1. Load the current active rule set from markdown.
2. Receive and validate input.
3. Apply redactions exactly as defined in the rule set.
4. Produce a structured output artifact.
5. Record full processing metadata.
6. Request cryptographic attestation for the entire operation.

Agents **must** execute these steps in order. Skipping or reordering steps is not permitted in APXV.

---

## 2. Detailed Steps

### Step 1: Load Active Rules
- Read the file `managed/rules/rule1.md` (or the current active rule file as specified by the artifact provider).
- Parse the Rule ID, Version, and all redaction categories.
- Store the rule hash for later attestation.
- If the rule file cannot be read or parsed, the workflow **must fail** with a clear error.

### Step 2: Receive Input
- Accept input text (from command line, API call, or previous artifact).
- Record the input hash (SHA-256) in metadata.
- Validate that input is text-based. Reject binary or malformed input.

### Step 3: Apply Redactions
- Strictly follow every rule defined in the loaded rule set (APXV-RULE-001 in this baseline).
- Perform redactions in the exact order listed in the rule file.
- Do **not** apply any redactions not explicitly listed.
- Count and categorize every redaction performed.

### Step 4: Generate Output
- Create a clean redacted version of the text.
- Build a structured result containing:
  - `original_hash`
  - `redacted_text`
  - `redactions_applied` (list with category and count)
  - `rule_id` and `rule_version` used
  - `rule_file_hash` at time of execution
  - `timestamp`
  - `agent_id` (to be filled by the executing agent)

### Step 5: Write Output Artifact
- Use the APXV artifact layer to write the result as a new governed artifact.
- The artifact must include both the redacted text and the full metadata block.
- Return the artifact ID to the caller.

### Step 6: Request Attestation
- Package the following for the attestation system:
  - Rule ID + Version + file hash
  - Input hash
  - Output artifact ID
  - List of redactions performed
  - Workflow ID + Version (`APXV-WF-001 v1.0.0`)
- Submit this package to the proof system for cryptographic attestation.
- The resulting proof must be stored alongside the output artifact.

---

## 3. Determinism & Audit Requirements

- This workflow must be fully deterministic given the same input + same rule version.
- Every execution must produce an auditable trail (via artifacts + attestation).
- Agents must never cache rule content across runs — they must re-read the markdown file each time.

---

## 4. Error Handling

- Any failure in Steps 1–6 must result in:
  - No output artifact being written
  - A clear error artifact being created instead
  - No attestation request being made for a failed run

---

## 5. Governance Notes

- This workflow can only be changed by editing this file and incrementing the version.
- Future agents must always load the latest version of this workflow from the markdown file at runtime.
- This workflow takes precedence over any agent-specific logic that would bypass redaction or attestation.

---

**End of Workflow APXV-WF-001**

This file, together with `rule1.md`, forms the active behavioral contract for text processing in APXV.
