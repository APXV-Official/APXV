"""
APXV — Redaction engine public API.

Backward-compatible facade over agents.redaction.APXVRedactionEngine (v3).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from agents.redaction import APXVRedactionEngine
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
    """Deterministic governed redaction engine for APXV-RULE-001."""

    def __init__(self, audit_logger: Any = None) -> None:
        self._engine = APXVRedactionEngine(audit_logger=audit_logger)

    def register_backend(self, name: str, handler: Any) -> str:
        return self._engine.register_backend(name, handler)

    def apply(
        self,
        text: str,
        *,
        redact_names: bool = False,
        backend_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._engine.apply(
            text,
            redact_names=redact_names,
            backend_id=backend_id,
        )