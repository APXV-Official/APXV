# APXV — Workflow DOC: Batch Document Processing & Attestation

**Workflow ID:** APXV-WF-DOC-001  
**Version:** 0.1.0  
**Effective Date:** 2026-06-28  
**Depends On:** APXV-RULE-DOC-001  
**Purpose:** Govern batch ingestion of text/json documents through redaction, manifest, and attestation.

---

## 1. Workflow steps

1. Discover supported files (`.txt`, `.json`) in the batch directory.
2. For each file: load governance specs, hash input, apply redactions per APXV-RULE-DOC-001.
3. Build `batch_manifest` with per-file hashes and counts.
4. Merge entities and redaction metadata for orchestration.
5. Package proposed artifact with `compliance_policy_id: 2`.
6. Coordinate attestation via APXV-AGENT-003.

## 2. Manifest schema

The batch manifest must include:

- `batch_id` (UUID)
- `file_count`
- `compliance_policy_id` (2 for this pack)
- `files[]` with `path`, `original_hash`, `redacted_hash`, `entity_count`, `total_redactions`

Agents must not skip manifest creation for multi-file batches.