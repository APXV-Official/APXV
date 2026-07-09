"""Governance seed + runtime first-run (step 5)."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict

from agents.install_profile import write_runtime_profile

from scripts.bootstrap.constants import GOVERNANCE_SPEC_FILES
from scripts.setup_first_run import run_setup


def seed_rust_layout(base_path: Path, source_root: Path) -> Dict[str, Any]:
    """Copy rust workspace crates into instance root when absent (keys on operator storage)."""
    dest = base_path / "rust"
    if (dest / "Cargo.toml").is_file():
        return {"copied": False, "path": str(dest)}
    src = source_root / "rust"
    if not src.is_dir():
        raise RuntimeError(f"Missing rust workspace at {src}")

    dest.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for name in ("Cargo.toml", "Cargo.lock"):
        item = src / name
        if item.is_file():
            shutil.copy2(item, dest / name)
            copied.append(name)

    def _ignore(_dir: str, names: list[str]) -> set[str]:
        return {n for n in names if n in {"target", "keys"}}

    for crate in ("apxv-circuits", "apxv-zk"):
        crate_src = src / crate
        if crate_src.is_dir() and not (dest / crate).exists():
            shutil.copytree(crate_src, dest / crate, ignore=_ignore)
            copied.append(crate)

    return {"copied": True, "path": str(dest), "items": copied}


def seed_governance_templates(base_path: Path, source_root: Path) -> Dict[str, Any]:
    """Copy default managed governance specs from source tree when absent."""
    copied = []
    for spec_dir, filename in GOVERNANCE_SPEC_FILES:
        dest = base_path / "managed" / spec_dir / filename
        if dest.exists():
            continue
        src = source_root / "managed" / spec_dir / filename
        if not src.is_file():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied.append(f"managed/{spec_dir}/{filename}")

    gov_lib_src = source_root / "governance-libraries"
    gov_lib_dest = base_path / "governance-libraries"
    if gov_lib_src.is_dir() and not gov_lib_dest.exists():
        shutil.copytree(gov_lib_src, gov_lib_dest)
        copied.append("governance-libraries/")

    return {"copied": copied, "count": len(copied)}


def ensure_runtime_profile(base_path: Path, profile: str) -> Dict[str, Any]:
    """Write managed/config/runtime.json with install profile."""
    return write_runtime_profile(base_path, profile)


def run_first_run(base_path: Path, *, profile: str) -> Dict[str, Any]:
    """Initialize managed runtime (ZK keys already created in steps 3–4)."""
    report = run_setup(base_path, setup_zk=False)
    report["runtime_profile"] = ensure_runtime_profile(base_path, profile)
    if not report.get("healthy"):
        raise RuntimeError("setup_first_run integrity check failed")
    zk_keys = report["steps"].get("zk_keys", {})
    entity_keys = report["steps"].get("entity_zk_keys", {})
    if not zk_keys.get("ready") or not entity_keys.get("ready"):
        raise RuntimeError("ZK keys not ready after sovereign setup")
    return report