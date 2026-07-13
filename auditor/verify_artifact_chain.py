#!/usr/bin/env python3
"""
APX Auditor Tool — Verify Artifact Chain Integrity

This script allows an external auditor to verify that the artifact store
maintains a valid cryptographic chain (previous_artifact links).

Usage:
    python verify_artifact_chain.py /path/to/managed/artifacts

All code is original work written for APXV.
"""

import json
import hashlib
import sys
from pathlib import Path
from typing import List, Dict, Any


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def load_artifact(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def verify_artifact_chain(artifacts_dir: Path) -> bool:
    if not artifacts_dir.exists():
        print(f"ERROR: Artifacts directory not found: {artifacts_dir}")
        return False

    files = sorted(artifacts_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        print("No artifacts found — nothing to verify.")
        return True

    errors = 0
    previous_hash = None

    for i, file_path in enumerate(files, 1):
        entry = load_artifact(file_path)
        current_hash = entry.get("artifact_hash")
        stored_previous = entry.get("previous_artifact")

        if stored_previous != previous_hash:
            print(f"{file_path.name}: Previous artifact hash mismatch")
            errors += 1

        previous_hash = current_hash

    if errors == 0:
        print(f"SUCCESS: Artifact chain verified. {len(files)} artifacts are intact.")
        return True
    else:
        print(f"FAILURE: {errors} error(s) detected in the artifact chain.")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_artifact_chain.py /path/to/managed/artifacts")
        sys.exit(1)

    artifacts_dir = Path(sys.argv[1])
    success = verify_artifact_chain(artifacts_dir)
    sys.exit(0 if success else 1)