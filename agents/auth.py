"""
APXV — Local API Key Authentication (Phase 4 / Step 1)

Air-gapped operator authentication using hashed keys in local config.
No external identity provider required.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import hashlib
import json
import secrets


class APIKeyAuth:
    """Validate operator API keys against local hashed key store."""

    def __init__(self, config_path: Path):
        self.config_path = Path(config_path)
        self._keys: List[Dict[str, Any]] = []
        self._load()

    @staticmethod
    def hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def _load(self) -> None:
        if not self.config_path.exists():
            self._keys = []
            return
        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        self._keys = data.get("keys", [])

    def list_keys(self) -> List[Dict[str, Any]]:
        """Return key metadata (never includes raw secrets)."""
        return [
            {
                "id": entry.get("id"),
                "role": entry.get("role"),
                "created_at": entry.get("created_at"),
                "description": entry.get("description"),
            }
            for entry in self._keys
        ]

    def reload(self) -> None:
        """Reload key store from disk (e.g. after external updates)."""
        self._load()

    def revoke_key(self, key_id: str) -> None:
        """Remove an API key by id. Raises if id missing or last key."""
        if len(self._keys) <= 1:
            raise ValueError("Cannot revoke the last API key")
        if not any(entry.get("id") == key_id for entry in self._keys):
            raise ValueError(f"API key id not found: {key_id}")
        remaining = [entry for entry in self._keys if entry.get("id") != key_id]
        payload = {
            "version": "1.0.0",
            "deployment": "local-airgapped",
            "keys": remaining,
        }
        self.config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._keys = remaining

    def create_key(
        self,
        key_id: str,
        *,
        description: str = "",
        role: str = "operator",
    ) -> str:
        """Create a new API key. Returns the raw key once."""
        if any(entry.get("id") == key_id for entry in self._keys):
            raise ValueError(f"API key id already exists: {key_id}")

        raw_key = secrets.token_urlsafe(32)
        entry = {
            "id": key_id,
            "key_hash": self.hash_key(raw_key),
            "role": role,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "description": description or f"Created key {key_id}",
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "1.0.0",
            "deployment": "local-airgapped",
            "keys": self._keys + [entry],
        }
        self.config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._keys.append(entry)
        return raw_key

    @staticmethod
    def write_key_hint(base_path: Path, key_id: str, raw_key: str) -> Path:
        """Write a one-time operator hint file (gitignored)."""
        hint_path = base_path / "managed" / "config" / f"OPERATOR-KEY-{key_id}.txt"
        hint_path.write_text(
            "\n".join(
                [
                    "APXV Operator API Key (save securely — delete after copying)",
                    f"Key ID: {key_id}",
                    f"API Key: {raw_key}",
                    "",
                    "Usage:",
                    f'  export APXV_API_KEY="{raw_key}"',
                    "  Authorization: Bearer <key>",
                ]
            ),
            encoding="utf-8",
        )
        return hint_path

    def ensure_default_key(self) -> Optional[str]:
        """
        Create a default operator key if none exist.
        Returns the raw key once (caller must display/save for operator).
        """
        if self._keys:
            return None

        raw_key = secrets.token_urlsafe(32)
        entry = {
            "id": "default-operator",
            "key_hash": self.hash_key(raw_key),
            "role": "operator",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "description": "Auto-generated on first server start",
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "1.0.0",
            "deployment": "local-airgapped",
            "keys": [entry],
        }
        self.config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._keys = [entry]
        return raw_key

    def validate(self, raw_key: Optional[str]) -> bool:
        if not raw_key:
            return False
        self.reload()
        key_hash = self.hash_key(raw_key)
        return any(entry.get("key_hash") == key_hash for entry in self._keys)

    @staticmethod
    def _header_value(headers: Dict[str, str], name: str) -> Optional[str]:
        target = name.lower()
        for key, value in headers.items():
            if key.lower() == target and value:
                return value.strip()
        return None

    def extract_key_from_headers(self, headers: Dict[str, str]) -> Optional[str]:
        auth = self._header_value(headers, "Authorization") or ""
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        # Canonical header (APXV branding); legacy alias kept for compatibility.
        for name in ("APXV-API-KEY", "X-APX-API-Key"):
            value = self._header_value(headers, name)
            if value:
                return value
        return None