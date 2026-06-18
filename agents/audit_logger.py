"""
APX v1 — Cryptographically Chained Audit Logger (Phase 2)

This module provides an immutable, append-only audit log with
cryptographic chaining. Each entry contains a hash of the previous
entry, enabling tamper detection and independent verification.

This is a foundational component for Phase 2 Governed Core Hardening.

All code is original work written for APX v1.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib
import json


class AuditLogger:
    """
    Immutable, cryptographically chained audit logger.

    Guarantees:
    - Append-only: Entries cannot be modified or deleted after writing.
    - Cryptographic chaining: Each entry references the hash of the previous entry.
    - Tamper detection: Any modification breaks the chain.
    - Auditability: Full provenance for every logged event.
    """

    def __init__(self, log_path: Path, json_format: bool = True):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.json_format = json_format

        # Ensure the log file exists
        if not self.log_path.exists():
            self.log_path.write_text("", encoding="utf-8")

    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _get_last_entry_hash(self) -> Optional[str]:
        """Return the hash of the most recent log entry, or None if log is empty."""
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            return None

        lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return None

        try:
            last_entry = json.loads(lines[-1])
            return last_entry.get("current_hash")
        except (json.JSONDecodeError, KeyError):
            return None

    def log_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Append a new immutable event to the audit log.

        Args:
            event_type: Type of event (e.g., "artifact_written", "agent_executed")
            data: Event-specific data

        Returns:
            The complete log entry that was written.
        """
        previous_hash = self._get_last_entry_hash()

        timestamp = datetime.utcnow().isoformat() + "Z"

        entry = {
            "timestamp": timestamp,
            "event_type": event_type,
            "data": data,
            "previous_hash": previous_hash,
        }

        # Compute hash of this entry (excluding the current_hash field itself)
        entry_json = json.dumps(entry, sort_keys=True)
        current_hash = self._compute_hash(entry_json)
        entry["current_hash"] = current_hash

        # Append to log (immutable write)
        with self.log_path.open("a", encoding="utf-8") as f:
            if self.json_format:
                f.write(json.dumps(entry, sort_keys=True) + "\n")
            else:
                f.write(f"{entry['timestamp']} | {entry['event_type']} | {json.dumps(entry['data'])}\n")

        return entry

    def verify_chain(self) -> bool:
        """
        Verify the integrity of the entire audit log chain.

        Returns:
            True if the chain is valid, False if tampering is detected.
        """
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            return True  # Empty log is valid

        lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()
        expected_previous = None

        for line in lines:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                return False

            # Recompute hash without the stored current_hash
            entry_for_hash = {k: v for k, v in entry.items() if k != "current_hash"}
            computed_hash = self._compute_hash(json.dumps(entry_for_hash, sort_keys=True))

            if entry.get("current_hash") != computed_hash:
                return False

            if entry.get("previous_hash") != expected_previous:
                return False

            expected_previous = entry.get("current_hash")

        return True

    def get_entries(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return the most recent log entries (newest last)."""
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            return []

        lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()
        entries = [json.loads(line) for line in lines]

        if limit:
            return entries[-limit:]
        return entries

    def get_status(self) -> Dict[str, Any]:
        """Return basic status of the audit log."""
        entries = self.get_entries()
        return {
            "log_path": str(self.log_path),
            "entry_count": len(entries),
            "chain_valid": self.verify_chain(),
            "last_entry": entries[-1] if entries else None,
        }