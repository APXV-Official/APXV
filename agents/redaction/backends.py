"""Optional bring-your-own (BYO) redaction backends — envelope + audit only."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

RedactionBackendHandler = Callable[..., Dict[str, Any]]


def _slug_backend_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    if not slug:
        raise ValueError("backend name must contain at least one alphanumeric character")
    return slug


@dataclass
class RegisteredRedactionBackend:
    backend_id: str
    name: str
    handler: RedactionBackendHandler


@dataclass
class RedactionBackendRegistry:
    """In-memory registry of optional external redaction backends."""

    _entries: Dict[str, RegisteredRedactionBackend] = field(default_factory=dict)

    def register(self, name: str, handler: RedactionBackendHandler) -> str:
        if not callable(handler):
            raise TypeError("handler must be callable")
        backend_id = _slug_backend_id(name)
        if backend_id in self._entries:
            raise ValueError(f"backend already registered: {backend_id}")
        self._entries[backend_id] = RegisteredRedactionBackend(
            backend_id=backend_id,
            name=name,
            handler=handler,
        )
        return backend_id

    def get(self, backend_id: str) -> RegisteredRedactionBackend:
        if backend_id not in self._entries:
            raise KeyError(f"unknown redaction backend: {backend_id}")
        return self._entries[backend_id]

    def list_ids(self) -> List[str]:
        return sorted(self._entries.keys())

    def invoke(
        self,
        backend_id: str,
        *,
        text: str,
        input_format: str,
    ) -> Dict[str, Any]:
        entry = self.get(backend_id)
        result = entry.handler(text=text, input_format=input_format)
        if not isinstance(result, dict):
            raise TypeError(f"backend {backend_id} must return a dict")
        if "redacted_text" not in result:
            raise ValueError(f"backend {backend_id} result missing redacted_text")
        entities = result.get("entities", [])
        if not isinstance(entities, list):
            raise TypeError(f"backend {backend_id} entities must be a list")
        payload = {
            "redacted_text": result["redacted_text"],
            "entities": entities,
            "backend_id": backend_id,
            "input_hash": hashlib.sha256(text.encode()).hexdigest(),
        }
        if "redactions_applied" in result:
            payload["redactions_applied"] = result["redactions_applied"]
        if "total_redactions" in result:
            payload["total_redactions"] = result["total_redactions"]
        return payload