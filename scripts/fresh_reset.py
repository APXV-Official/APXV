"""
Reset APXV runtime state for a clean onboarding run.

Preserves governance templates (managed/rules, workflows, knowledge) required
for Docker builds and pack demos. Clears runtime dirs that setup_first_run
recreates (audit, config, store, ZK keys, etc.).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RUNTIME_REL_PATHS = (
    "managed/artifacts",
    "managed/audit",
    "managed/backups",
    "managed/config",
    "managed/store",
    "rust/apxv-circuits/keys",
    "rust/apxv-zk/keys",
)

GOVERNANCE_REL_PATHS = (
    "managed/rules",
    "managed/workflows",
    "managed/knowledge",
)

PACK_GOVERNANCE = (
    (
        "governance-libraries/apxv-pack-reference-redaction/governance/rules/RULE-RED-001.md",
        "managed/rules/rule1.md",
    ),
    (
        "governance-libraries/apxv-pack-reference-redaction/governance/workflows/WORKFLOW-RED-001.md",
        "managed/workflows/workflow1.md",
    ),
    (
        "governance-libraries/apxv-pack-reference-redaction/governance/knowledge/KB-RED-001.md",
        "managed/knowledge/knowledge1.md",
    ),
)


def _remove_runtime_paths(base: Path) -> None:
    for rel in RUNTIME_REL_PATHS:
        path = base / rel
        if path.exists():
            print(f"Removing {rel}")
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()


def _git_restore_templates(base: Path) -> bool:
    if not (base / ".git").exists():
        return False
    try:
        subprocess.run(
            [
                "git",
                "checkout",
                "--",
                "managed/rules",
                "managed/workflows",
                "managed/knowledge",
                "managed/config/.gitkeep",
            ],
            cwd=base,
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def _copy_pack_templates(base: Path) -> None:
    for src_rel, dst_rel in PACK_GOVERNANCE:
        src = base / src_rel
        dst = base / dst_rel
        if not src.is_file():
            raise FileNotFoundError(f"Pack template missing: {src_rel}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def ensure_governance_templates(base: Path) -> None:
    missing = [rel for rel in GOVERNANCE_REL_PATHS if not (base / rel).is_dir()]
    if not missing:
        return

    print("Restoring governance templates...")
    if _git_restore_templates(base):
        still_missing = [rel for rel in GOVERNANCE_REL_PATHS if not (base / rel).is_dir()]
        if not still_missing:
            return

    _copy_pack_templates(base)


def reset_runtime(base: Path | None = None) -> None:
    base = base or ROOT
    _remove_runtime_paths(base)
    ensure_governance_templates(base)


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset APXV runtime state for fresh onboarding")
    parser.add_argument(
        "--ensure-templates-only",
        action="store_true",
        help="Only ensure governance templates exist (no runtime cleanup)",
    )
    args = parser.parse_args()

    if args.ensure_templates_only:
        ensure_governance_templates(ROOT)
    else:
        reset_runtime(ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())