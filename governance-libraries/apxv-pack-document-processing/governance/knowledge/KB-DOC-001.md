# APXV — Knowledge Base DOC: Batch Documents & Compliance Policies

**Knowledge ID:** APXV-KB-DOC-001  
**Version:** 0.1.0  
**Effective Date:** 2026-06-28

---

## Compliance policy ids (entity circuit)

| ID | Name | When to use |
|----|------|-------------|
| 1 | Standard redaction | Single-document reference pipeline |
| 2 | Batch document handling | **This pack** — folder batch manifest |
| 3 | Voice redaction | Voice privacy pipeline |
| 4 | AI governance / regulated metadata | AI Governance Pack |
| 5 | Custom enterprise | Reserved |

This pack sets **policy id 2** on `batch_manifest` and artifact `output.compliance_policy_id`.

## JSON field extraction

For `.json` inputs, read text from the first present field among: `content`, `text`, `body`, `message`, `document`. Otherwise serialize the JSON object deterministically.

## Acceptance

A successful batch demo must report `final_status=ATTESTED`, `file_count>=2`, and `total_redactions>=1`.