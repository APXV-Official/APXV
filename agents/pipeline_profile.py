"""
Temporary pack governance profile for composition steps (v1.7).

Applies a pack's governance markdown into managed/ for the duration of a step,
then restores prior files and approval baselines. Does not permanently rewrite
active_pack.json unless requested.
"""

from __future__ import annotations

import hashlib
import shutil
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .pack_catalog import pack_dir_for, parse_pack_manifest
from .pack_install import MANAGED_SPECS, PackInstallError
from .store import SqliteArtifactStore

# managed path key -> pack governance list key
_SPEC_MAP = {
    "rules/rule1.md": "rules",
    "workflows/workflow1.md": "workflows",
    "knowledge/knowledge1.md": "knowledge",
}

_REL_TO_SPEC = {
    "rules/rule1.md": "rule",
    "workflows/workflow1.md": "workflow",
    "knowledge/knowledge1.md": "knowledge",
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _snapshot_managed_specs(base_path: Path) -> Dict[str, Optional[str]]:
    snap: Dict[str, Optional[str]] = {}
    for rel in MANAGED_SPECS:
        path = base_path / "managed" / rel
        snap[rel] = path.read_text(encoding="utf-8") if path.is_file() else None
    return snap


def _snapshot_approvals(base_path: Path) -> Dict[str, Optional[Dict[str, Any]]]:
    store = SqliteArtifactStore(base_path)
    out: Dict[str, Optional[Dict[str, Any]]] = {}
    for spec_type in ("rule", "workflow", "knowledge"):
        out[spec_type] = store.get_active_approval(spec_type)
    return out


def _restore_managed_specs(base_path: Path, snap: Dict[str, Optional[str]]) -> None:
    for rel, content in snap.items():
        path = base_path / "managed" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if content is None:
            if path.is_file():
                path.unlink()
        else:
            path.write_text(content, encoding="utf-8")


def _restore_approvals(
    base_path: Path, snap: Dict[str, Optional[Dict[str, Any]]]
) -> None:
    store = SqliteArtifactStore(base_path)
    now = _utcnow()
    for spec_type, active in snap.items():
        if not active:
            continue
        store.set_active_approval(
            spec_type=spec_type,
            content_hash=active["content_hash"],
            proposal_id=active.get("proposal_id") or f"profile-restore-{spec_type}",
            approved_at=active.get("approved_at") or now,
            applied_at=active.get("applied_at") or now,
        )


def _align_approvals_to_current_files(base_path: Path) -> None:
    """After swapping governance files, re-baseline approvals so agents can read."""
    store = SqliteArtifactStore(base_path)
    now = _utcnow()
    for rel, spec_type in _REL_TO_SPEC.items():
        path = base_path / "managed" / rel
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        store.set_active_approval(
            spec_type=spec_type,
            content_hash=_content_hash(content),
            proposal_id=f"pack-profile-{spec_type}",
            approved_at=now,
            applied_at=now,
        )


def apply_pack_governance_files(base_path: Path, pack_id: str) -> List[str]:
    """Copy first governance file of each type from pack into managed specs."""
    pack_dir = pack_dir_for(base_path, pack_id)
    if not pack_dir:
        raise PackInstallError(f"Pack not found for profile: {pack_id}")
    manifest = parse_pack_manifest(pack_dir)
    gov = manifest.get("governance") or {}
    applied: List[str] = []
    for managed_rel, list_key in _SPEC_MAP.items():
        rels = gov.get(list_key) or []
        if not rels:
            continue
        src = pack_dir / rels[0]
        if not src.is_file():
            raise PackInstallError(f"Pack profile missing governance file: {src}")
        dst = base_path / "managed" / managed_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        applied.append(managed_rel)
    if not applied:
        raise PackInstallError(f"Pack {pack_id} has no governance files for profile")
    return applied


@contextmanager
def pack_profile_context(base_path: Path, pack_id: Optional[str]) -> Iterator[Optional[str]]:
    """
    Temporarily apply pack governance. Restores previous managed specs and
    governance approval baselines on exit.
    """
    if not pack_id:
        yield None
        return
    snap_files = _snapshot_managed_specs(base_path)
    snap_approvals = _snapshot_approvals(base_path)
    try:
        apply_pack_governance_files(base_path, pack_id)
        _align_approvals_to_current_files(base_path)
        yield pack_id
    finally:
        _restore_managed_specs(base_path, snap_files)
        _restore_approvals(base_path, snap_approvals)
