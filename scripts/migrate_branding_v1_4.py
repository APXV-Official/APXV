"""Patch user-facing markdown branding: APX / APXV1 -> APXV in managed and packs."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Order matters: longer / compound patterns first.
_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"APX-governed", re.IGNORECASE), "APXV-governed"),
    (re.compile(r"APXV1\b"), "APXV"),
    (re.compile(r"\bAPX guidelines\b"), "APXV guidelines"),
    (re.compile(r"\bany APX agent\b"), "any APXV agent"),
    (re.compile(r"\bwithin APX\b"), "within APXV"),
    (re.compile(r"\bAPX agent\b"), "APXV agent"),
    (re.compile(r"\bAPX execution\b"), "APXV execution"),
    (re.compile(r"\bAPX assistant\b"), "APXV assistant"),
)

_SCAN_ROOTS = (
    "managed/rules",
    "managed/workflows",
    "managed/knowledge",
    "managed/pack-snapshots",
    "governance-libraries",
)


def resolve_base_path() -> Path:
    env = os.environ.get("APXV_ROOT") or os.environ.get("APXV_BASE_PATH")
    if env:
        return Path(env).resolve()
    return ROOT


def patch_markdown(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    updated = text
    for pattern, replacement in _REPLACEMENTS:
        updated = pattern.sub(replacement, updated)
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def migrate_branding(base_path: Path) -> dict[str, object]:
    changed: list[str] = []
    for rel in _SCAN_ROOTS:
        root = base_path / rel
        if not root.is_dir():
            continue
        for md in root.rglob("*.md"):
            if patch_markdown(md):
                changed.append(str(md.relative_to(base_path)))
    return {"changed": bool(changed), "files": changed}


def main() -> int:
    base = resolve_base_path()
    result = migrate_branding(base)
    if result.get("changed"):
        print(f"branding migration at {base}")
        for name in result["files"]:
            print(f"  patched: {name}")
    else:
        print("branding: no changes needed")
    return 0


if __name__ == "__main__":
    sys.exit(main())