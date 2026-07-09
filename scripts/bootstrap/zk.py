"""Governance + entity ZK trusted setup (steps 3–4)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from scripts.bootstrap.constants import ENTITY_CIRCUITS, GOVERNANCE_CIRCUITS
from scripts.setup_entity_zk import ensure_entity_zk_setup
from scripts.setup_first_run import verify_entity_zk_keys, verify_zk_keys
from scripts.setup_zk import ensure_zk_setup


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_governance_zk(base_path: Path, *, force: bool = False) -> Dict[str, Any]:
    """Step 3 — governance circuit trusted setup."""
    report = ensure_zk_setup(base_path=base_path, force=force)
    keys = verify_zk_keys(base_path)
    if not keys["ready"]:
        raise RuntimeError("Governance ZK keys incomplete after setup")
    report["keys_ready"] = True
    return report


def run_entity_zk(base_path: Path, *, force: bool = False) -> Dict[str, Any]:
    """Step 4 — entity circuit trusted setup."""
    report = ensure_entity_zk_setup(base_path=base_path, force=force)
    keys = verify_entity_zk_keys(base_path)
    if not keys["ready"]:
        raise RuntimeError("Entity ZK keys incomplete after setup")
    report["keys_ready"] = True
    return report


def collect_vk_hashes(base_path: Path) -> Dict[str, str]:
    """Collect verification key hashes for install.json provenance."""
    hashes: Dict[str, str] = {}
    gov_dir = base_path / "rust" / "apxv-circuits" / "keys"
    for circuit in GOVERNANCE_CIRCUITS:
        vk = gov_dir / f"{circuit}.vk"
        if vk.is_file():
            hashes[circuit] = _sha256_file(vk)
    entity_dir = base_path / "rust" / "apxv-zk" / "keys"
    for circuit in ENTITY_CIRCUITS:
        vk = entity_dir / f"{circuit}.vk"
        if vk.is_file():
            hashes[circuit] = _sha256_file(vk)
    return hashes


def zk_setup_timestamp(base_path: Path) -> str:
    """Earliest vk mtime among required circuits, else now (UTC)."""
    candidates = []
    for circuit in GOVERNANCE_CIRCUITS:
        vk = base_path / "rust" / "apxv-circuits" / "keys" / f"{circuit}.vk"
        if vk.is_file():
            candidates.append(vk.stat().st_mtime)
    for circuit in ENTITY_CIRCUITS:
        vk = base_path / "rust" / "apxv-zk" / "keys" / f"{circuit}.vk"
        if vk.is_file():
            candidates.append(vk.stat().st_mtime)
    if not candidates:
        return datetime.now(timezone.utc).isoformat()
    earliest = min(candidates)
    return datetime.fromtimestamp(earliest, tz=timezone.utc).isoformat()