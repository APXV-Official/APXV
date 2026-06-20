"""
APX v1 — Redaction engine public API.

Backward-compatible facade over agents.redaction.APXRedactionEngine (v3).
"""

from __future__ import annotations

from typing import Any, Dict

from agents.redaction import APXRedactionEngine
from agents.redaction.engine import (
    REDACTION_ENGINE_VERSION,
    _luhn_valid,
    _ssn_parts_valid,
)

# Re-export helpers used by tests
__all__ = [
    "RedactionEngine",
    "REDACTION_ENGINE_VERSION",
    "_luhn_valid",
    "_ssn_parts_valid",
]


class RedactionEngine:
    """Deterministic governed redaction engine for APX-RULE-001."""

    def __init__(self) -> None:
        self._engine = APXRedactionEngine()

    def apply(self, text: str, *, redact_names: bool = False) -> Dict[str, Any]:
        return self._engine.apply(text, redact_names=redact_names)