"""Shared bootstrap constants."""

from __future__ import annotations

BOOTSTRAP_VERSION = "1.5.0"

GOVERNANCE_CIRCUITS = ("redaction", "rule-binding", "pipeline")

ENTITY_CIRCUITS = (
    "core-redaction",
    "compliance",
    "voice-redaction",
    "redaction-v1",
    "merkle-inclusion",
    "batch-merkle",
)

GOVERNANCE_SPEC_FILES = (
    ("rules", "rule1.md"),
    ("workflows", "workflow1.md"),
    ("knowledge", "knowledge1.md"),
)