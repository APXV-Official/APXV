"""
APX v1 — Cryptographically Chained Audit Logger (Phase 2)

This module provides an immutable, append-only audit log with
cryptographic chaining. Each entry contains a hash of the previous
entry, enabling tamper detection and independent verification.

This is a foundational component for Phase 2 Governed Core Hardening.

All code is original work written for APX v1.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
import hashlib
import json
import threading


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
        self._lock = threading.Lock()

        if not self.log_path.exists():
            self.log_path.write_text("", encoding="utf-8")

    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _read_raw_lines(self) -> List[str]:
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            return []
        return self.log_path.read_text(encoding="utf-8").splitlines()

    def _parse_lines(self) -> Tuple[List[Dict[str, Any]], int]:
        """Parse log lines; skip empty/corrupt lines and return corrupt count."""
        entries: List[Dict[str, Any]] = []
        corrupt_count = 0
        for line in self._read_raw_lines():
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                corrupt_count += 1
        return entries, corrupt_count

    def _get_last_entry_hash(self) -> Optional[str]:
        """Return the hash of the most recent valid log entry, or None if empty."""
        entries, _ = self._parse_lines()
        if not entries:
            return None
        return entries[-1].get("current_hash")

    def log_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Append a new immutable event to the audit log.

        Args:
            event_type: Type of event (e.g., "artifact_written", "agent_executed")
            data: Event-specific data

        Returns:
            The complete log entry that was written.
        """
        with self._lock:
            previous_hash = self._get_last_entry_hash()
            timestamp = _utc_timestamp()

            entry = {
                "timestamp": timestamp,
                "event_type": event_type,
                "data": data,
                "previous_hash": previous_hash,
            }

            entry_json = json.dumps(entry, sort_keys=True)
            current_hash = self._compute_hash(entry_json)
            entry["current_hash"] = current_hash

            with self.log_path.open("a", encoding="utf-8") as f:
                if self.json_format:
                    f.write(json.dumps(entry, sort_keys=True) + "\n")
                else:
                    f.write(
                        f"{entry['timestamp']} | {entry['event_type']} | "
                        f"{json.dumps(entry['data'])}\n"
                    )

            return entry

    def verify_chain(self) -> bool:
        """
        Verify the integrity of the entire audit log chain.

        Returns:
            True if the chain is valid, False if tampering is detected.
        """
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            return True

        lines = self._read_raw_lines()
        expected_previous = None

        for line in lines:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                return False

            entry_for_hash = {k: v for k, v in entry.items() if k != "current_hash"}
            computed_hash = self._compute_hash(json.dumps(entry_for_hash, sort_keys=True))

            if entry.get("current_hash") != computed_hash:
                return False

            if entry.get("previous_hash") != expected_previous:
                return False

            expected_previous = entry.get("current_hash")

        return True

    def get_entries(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return valid log entries (newest last). Skips corrupt lines."""
        entries, _ = self._parse_lines()
        if limit:
            return entries[-limit:]
        return entries

    def _recovery_hint(self, corrupt_count: int, chain_valid: bool, entry_count: int) -> tuple:
        """Classify degraded logs and return (issue, hint). issue is None when healthy."""
        if corrupt_count > 0:
            return (
                "corrupt_lines",
                "Unparseable audit lines detected. Back up managed/, remove affected files "
                "under managed/audit/, then run: python -m scripts.setup_first_run",
            )
        if not chain_valid and entry_count > 0:
            return (
                "chain_break",
                "Audit hash chain is broken (common on long-lived dev trees). Remove "
                "managed/audit/*.log and run: python -m scripts.setup_first_run - or "
                "python -m scripts.fresh_reset for a full local reset.",
            )
        return (None, None)

    def get_status(self) -> Dict[str, Any]:
        """Return basic status of the audit log."""
        entries, corrupt_count = self._parse_lines()
        chain_valid = self.verify_chain()
        issue, recovery_hint = self._recovery_hint(corrupt_count, chain_valid, len(entries))
        return {
            "log_path": str(self.log_path),
            "entry_count": len(entries),
            "corrupt_line_count": corrupt_count,
            "chain_valid": chain_valid,
            "degraded": corrupt_count > 0 or not chain_valid,
            "issue": issue,
            "recovery_hint": recovery_hint,
            "last_entry": entries[-1] if entries else None,
        }