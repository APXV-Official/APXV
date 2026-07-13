"""Shared bootstrap constants."""

from __future__ import annotations

BOOTSTRAP_VERSION = "1.3.2"

GOVERNANCE_CIRCUITS = ("redaction", "rule-binding", "pipeline")

ENTITY_CIRCUITS = (
    "normalization",
    "core-redaction",
    "compliance",
    "threat",
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