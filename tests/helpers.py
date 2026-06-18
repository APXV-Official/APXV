"""Shared helpers for APXV1 integration tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scripts.setup_first_run import run_setup


def seed_test_instance(target: Path) -> str | None:
    """Bootstrap an isolated APX instance for tests (no ZK, no gitignored local files).

    Returns the raw API key when first-run setup creates one.
    """
    managed = target / "managed"
    for sub in (
        "config",
        "store",
        "audit",
        "rules",
        "workflows",
        "knowledge",
        "artifacts",
        "governance",
    ):
        (managed / sub).mkdir(parents=True, exist_ok=True)

    for rel in ("rules/rule1.md", "workflows/workflow1.md", "knowledge/knowledge1.md"):
        src = ROOT / "managed" / rel
        dst = managed / rel
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    report = run_setup(target, setup_zk=False)
    if not report["healthy"]:
        raise RuntimeError(f"Test instance setup unhealthy: {report}")
    return report["steps"]["api_key"].get("api_key")