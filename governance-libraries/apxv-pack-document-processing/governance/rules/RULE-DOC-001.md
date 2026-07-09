# APXV — Rule Set DOC: Batch Document Redaction

**Rule ID:** APXV-RULE-DOC-001  
**Version:** 0.1.0  
**Effective Date:** 2026-06-28  
**Purpose:** Extend APXV-RULE-001 redaction categories to batch `.txt` and `.json` document folders.

---

## 1. Scope

- Input: a directory of `.txt` plain-text files and `.json` files with a `content`, `text`, `body`, or `message` field.
- Output: per-file redaction using the same deterministic categories as APXV-RULE-001 (email, phone, SSN, card).
- Not in scope: PDF, DOCX, images, or enterprise DLP.

## 2. Batch requirements

- Process **every** supported file in the batch directory.
- Record per-file `original_hash`, `redacted_hash`, `entity_count`, and `total_redactions` in the batch manifest.
- Set **compliance policy id 2** (batch document handling) on the combined artifact.

## 3. Redaction behavior

Inherit all behavior from APXV-RULE-001 (Controlled Redaction). Each file is redacted independently before manifest aggregation.