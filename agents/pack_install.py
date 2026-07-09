"""Pack install, activate, clone, and active-pack tracking for Pack Studio."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .capability_policy import CapabilityPolicyError
from .pack_catalog import (
    GOVERNANCE_LIST_KEYS,
    get_pack,
    is_official_pack,
    pack_dir_for,
    parse_pack_manifest,
    resolve_apx_root,
)
from .pack_scaffold import _validate_pack_id, _rewrite_custom_agents, _rewrite_pack_identity
from .runtime import APXRuntime
from .store import SqliteArtifactStore
from .governance_approval import SPEC_TYPES

ACTIVE_PACK_REL = Path("managed") / "config" / "active_pack.json"
SNAPSHOTS_REL = Path("managed") / "pack-snapshots"
MANAGED_SPECS = (
    "rules/rule1.md",
    "workflows/workflow1.md",
    "knowledge/knowledge1.md",
)


class PackInstallError(Exception):
    """Raised when pack install/activate/clone fails."""


def load_pack_manifest(pack_dir: Path) -> Dict[str, Any]:
    """Load pack manifest; raises PackInstallError when pack.yaml is missing."""
    try:
        return parse_pack_manifest(pack_dir)
    except FileNotFoundError as exc:
        raise PackInstallError(str(exc)) from exc


def read_active_pack(base_path: Path) -> Optional[Dict[str, Any]]:
    path = base_path / ACTIVE_PACK_REL
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_active_pack(base_path: Path, record: Dict[str, Any]) -> Dict[str, Any]:
    path = base_path / ACTIVE_PACK_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def snapshot_governance(base_path: Path, pack_id: str) -> str:
    """Snapshot managed governance specs (and active_pack.json) for a pack id."""
    snap_root = base_path / SNAPSHOTS_REL / pack_id
    snap_root.mkdir(parents=True, exist_ok=True)

    for rel in MANAGED_SPECS:
        src = base_path / "managed" / rel
        if not src.exists():
            continue
        dst = snap_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    active = read_active_pack(base_path)
    if active:
        (snap_root / "active_pack.json").write_text(
            json.dumps(active, indent=2),
            encoding="utf-8",
        )
    return str(snap_root.relative_to(base_path)).replace("\\", "/")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pack_dir(base_path: Path, pack_id: str) -> Path:
    pack_dir = pack_dir_for(base_path, pack_id)
    if not pack_dir:
        raise PackInstallError(f"Pack not found: {pack_id}")
    return pack_dir


def _read_governance_content(pack_dir: Path, rel_paths: List[str]) -> str:
    if not rel_paths:
        raise PackInstallError(f"Pack {pack_dir.name} has no governance file for activation")
    target = pack_dir / rel_paths[0]
    if not target.exists():
        raise PackInstallError(f"Governance file missing: {target}")
    return target.read_text(encoding="utf-8")


def _governance_hashes(runtime: APXRuntime) -> Dict[str, str]:
    approval = runtime.governance.approval
    hashes: Dict[str, str] = {}
    for spec_type in SPEC_TYPES:
        try:
            content = approval._read_spec_content(spec_type)
        except FileNotFoundError:
            continue
        hashes[spec_type] = approval._content_hash(content)
    return hashes


def apply_policy_delta(
    runtime: APXRuntime,
    pack_dir: Path,
    *,
    activated_by: str = "operator",
) -> Dict[str, Any]:
    manifest = load_pack_manifest(pack_dir)
    rel = manifest.get("policy_delta") or "capabilities/policy-delta.json"
    delta_path = pack_dir / rel
    if not delta_path.exists():
        return {"applied": False, "reason": "no_policy_delta"}

    delta = json.loads(delta_path.read_text(encoding="utf-8"))
    agents_to_add = delta.get("agents_to_add") or {}
    if not agents_to_add:
        return {"applied": False, "reason": "empty_agents_to_add"}

    for agent_id, caps in agents_to_add.items():
        for cap in caps:
            runtime.capability_checker.grant_capability(agent_id, cap, persist=False)

    try:
        signed = runtime.capability_checker.publish_policy(
            issued_by=activated_by,
            description=f"Pack policy delta from {pack_dir.name}",
        )
    except CapabilityPolicyError as exc:
        raise PackInstallError(f"Policy delta publish failed: {exc}") from exc

    return {
        "applied": True,
        "agents": sorted(agents_to_add.keys()),
        "policy_version": signed.get("policy_version"),
    }


def _apply_governance_spec(
    runtime: APXRuntime,
    spec_type: str,
    content: str,
    *,
    pack_id: str,
    activated_by: str,
) -> Dict[str, Any]:
    governance = runtime.governance
    approval = governance.approval
    current_hash: Optional[str] = None
    try:
        current_hash = approval._content_hash(approval._read_spec_content(spec_type))
    except FileNotFoundError:
        pass

    content_hash = approval._content_hash(content)
    if current_hash == content_hash:
        return {
            "spec_type": spec_type,
            "status": "unchanged",
            "content_hash": content_hash,
        }

    proposal = governance.propose_change(
        spec_type,
        content,
        proposed_by=activated_by,
        summary=f"Pack activate: {pack_id}",
    )
    governance.approve_proposal(proposal["id"], approved_by=activated_by)
    applied = governance.apply_proposal(proposal["id"])
    return {
        "spec_type": spec_type,
        "status": "applied",
        "proposal_id": proposal["id"],
        "content_hash": applied.get("applied_content_hash") or content_hash,
    }


def activate_pack(
    runtime: APXRuntime,
    pack_id: str,
    *,
    confirm: bool = False,
    activated_by: str = "operator",
) -> Dict[str, Any]:
    """Activate a pack: snapshot prior governance, apply pack specs, write active_pack.json."""
    entry = get_pack(runtime.base_path, pack_id)
    if not entry:
        raise PackInstallError(f"Pack not found: {pack_id}")

    resolved_id = entry["id"]
    official = is_official_pack(resolved_id)
    if not official and not confirm:
        raise PackInstallError(
            f"Pack {resolved_id} is not official; set confirm=true to activate"
        )

    pack_dir = _pack_dir(runtime.base_path, resolved_id)
    manifest = load_pack_manifest(pack_dir)

    previous = read_active_pack(runtime.base_path)
    if previous and previous.get("pack_id") and previous["pack_id"] != resolved_id:
        snapshot_governance(runtime.base_path, previous["pack_id"])

    spec_results: List[Dict[str, Any]] = []
    for list_key, spec_type in GOVERNANCE_LIST_KEYS.items():
        rel_paths = manifest["governance"].get(list_key) or []
        content = _read_governance_content(pack_dir, rel_paths)
        spec_results.append(
            _apply_governance_spec(
                runtime,
                spec_type,
                content,
                pack_id=resolved_id,
                activated_by=activated_by,
            )
        )

    policy_result = apply_policy_delta(runtime, pack_dir, activated_by=activated_by)
    governance_hashes = _governance_hashes(runtime)

    record = {
        "pack_id": resolved_id,
        "pack_name": entry.get("name", resolved_id),
        "activated_at": _utcnow(),
        "activated_by": activated_by,
        "official": official,
        "previous_pack_id": (previous or {}).get("pack_id"),
        "governance_hashes": governance_hashes,
        "governance_summary_hash": SqliteArtifactStore.compute_hash(
            json.dumps(governance_hashes, sort_keys=True)
        ),
    }
    write_active_pack(runtime.base_path, record)

    verification = runtime.governance.approval.verify_active_specs()
    if not verification["valid"]:
        raise PackInstallError(
            "Governance verification failed after activate: "
            + "; ".join(verification.get("issues", []))
        )

    return {
        "pack_id": resolved_id,
        "active": record,
        "spec_results": spec_results,
        "policy_delta": policy_result,
        "snapshot_of": previous.get("pack_id") if previous else None,
    }


def clone_pack(
    base_path: Path,
    source_pack_id: str,
    *,
    new_pack_id: str,
    name: str,
    description: str = "",
) -> Dict[str, Any]:
    """Clone an installed pack to a new apxv-pack-<slug> directory."""
    new_pack_id = _validate_pack_id(new_pack_id)
    source = get_pack(base_path, source_pack_id)
    if not source:
        raise PackInstallError(f"Source pack not found: {source_pack_id}")

    apx_root = resolve_apx_root(base_path)
    source_dir = apx_root / source["path"]
    target_dir = apx_root / "governance-libraries" / new_pack_id
    if target_dir.exists():
        raise PackInstallError(f"Pack already exists: {new_pack_id}")

    shutil.copytree(
        source_dir,
        target_dir,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    _rewrite_pack_identity(
        target_dir,
        pack_id=new_pack_id,
        name=name,
        description=description or f"Clone of {source['id']}",
    )
    agents_custom = target_dir / "agents" / "custom_agents.py"
    if agents_custom.exists():
        _rewrite_custom_agents(target_dir, pack_id=new_pack_id, name=name)

    return {
        "pack_id": new_pack_id,
        "name": name,
        "source_pack_id": source["id"],
        "path": str(target_dir.relative_to(apx_root)).replace("\\", "/"),
    }


def install_pack(base_path: Path, pack_id: str) -> Dict[str, Any]:
    """Verify a pack is present in the local catalog (tree-shipped packs)."""
    entry = get_pack(base_path, pack_id)
    if not entry:
        raise PackInstallError(f"Pack not found in governance-libraries: {pack_id}")
    pack_dir = _pack_dir(base_path, entry["id"])
    manifest = load_pack_manifest(pack_dir)
    return {
        "pack_id": entry["id"],
        "name": entry.get("name"),
        "installed": True,
        "path": entry["path"],
        "official": is_official_pack(entry["id"]),
        "agents": manifest.get("agents", []),
    }


def get_active_pack_summary(base_path: Path) -> Dict[str, Any]:
    active = read_active_pack(base_path)
    if not active:
        return {"active": None, "pack": None}
    pack = get_pack(base_path, active["pack_id"])
    return {
        "active": active,
        "pack": pack,
    }