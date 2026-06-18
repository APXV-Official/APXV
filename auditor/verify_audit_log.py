#!/usr/bin/env python3
"""
APX Auditor Tool — Verify Audit Log Integrity

This script allows an external auditor to verify that an APX audit log
has not been tampered with by checking the cryptographic chain.

Usage:
    python verify_audit_log.py /path/to/audit.log

All code is original work written for APX v1.
"""

import json
import hashlib
import sys
from pathlib import Path


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def verify_audit_log(log_path: Path) -> bool:
    if not log_path.exists():
        print(f"ERROR: Log file not found: {log_path}")
        return False

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        print("Log file is empty — nothing to verify.")
        return True

    expected_previous_hash = None
    errors = 0

    for i, line in enumerate(lines, 1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            print(f"Line {i}: Invalid JSON")
            errors += 1
            continue

        # Recompute hash without the stored current_hash
        entry_for_hash = {k: v for k, v in entry.items() if k != "current_hash"}
        computed_hash = compute_hash(json.dumps(entry_for_hash, sort_keys=True))

        if entry.get("current_hash") != computed_hash:
            print(f"Line {i}: Hash mismatch (tampering detected)")
            errors += 1

        if entry.get("previous_hash") != expected_previous_hash:
            print(f"Line {i}: Previous hash mismatch (chain broken)")
            errors += 1

        expected_previous_hash = entry.get("current_hash")

    if errors == 0:
        print(f"SUCCESS: Audit log verified. {len(lines)} entries are intact.")
        return True
    else:
        print(f"FAILURE: {errors} error(s) detected in the audit log.")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_audit_log.py /path/to/audit.log")
        sys.exit(1)

    log_path = Path(sys.argv[1])
    success = verify_audit_log(log_path)
    sys.exit(0 if success else 1)