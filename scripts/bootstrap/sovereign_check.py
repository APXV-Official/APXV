"""Sovereign provenance verification (PR-11 doctor + integrity enforcement)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from scripts.bootstrap.install_json import read_install_json
from scripts.bootstrap.vendor_blocklist import is_vendor_vk_hash
from scripts.bootstrap.zk import collect_vk_hashes
from scripts.setup_first_run import verify_entity_zk_keys, verify_zk_keys


def verify_sovereign_setup(base_path: Path, *, require_provenance: bool = False) -> Dict[str, Any]:
    """Validate install.json provenance and on-disk ZK keys.

    When require_provenance is False (runtime integrity), operator-generated keys
    without install.json yet are acceptable (bootstrap step 5). Doctor passes
    require_provenance=True to enforce full provenance for operators.
    """
    issues: List[str] = []
    zk = verify_zk_keys(base_path)
    entity = verify_entity_zk_keys(base_path)
    keys_ready = bool(zk.get("ready") and entity.get("ready"))

    on_disk = collect_vk_hashes(base_path)
    has_any_keys = bool(on_disk)

    vendor_circuits = sorted(circuit for circuit, vk_hash in on_disk.items() if is_vendor_vk_hash(vk_hash))
    if vendor_circuits:
        issues.append(f"vendor_vk_detected: {', '.join(vendor_circuits)}")

    install = read_install_json(base_path)
    install_present = install is not None
    install_sovereign = bool(install and install.get("sovereign_setup"))

    vk_hashes_match = True
    mismatch_circuits: List[str] = []
    if install and isinstance(install.get("vk_hashes"), dict):
        recorded: Dict[str, str] = install["vk_hashes"]
        for circuit, expected in recorded.items():
            actual = on_disk.get(circuit)
            if actual is None or actual.lower() != str(expected).lower():
                vk_hashes_match = False
                mismatch_circuits.append(circuit)
        for circuit in on_disk:
            if circuit not in recorded:
                vk_hashes_match = False
                mismatch_circuits.append(circuit)
    if keys_ready and not install_present and require_provenance:
        vk_hashes_match = False
        issues.append("install_json_missing")

    if keys_ready and install_present and not install_sovereign:
        issues.append("sovereign_setup_not_true")

    if keys_ready and install_present and install_sovereign and not vk_hashes_match:
        issues.append(f"vk_hash_mismatch: {', '.join(sorted(set(mismatch_circuits)))}")

    if has_any_keys and not keys_ready:
        issues.append("keys_incomplete")

    if not has_any_keys:
        sovereign_ok = True
        status = "pending"
    elif vendor_circuits:
        sovereign_ok = False
        status = "vendor_keys"
    elif keys_ready:
        if install_present:
            sovereign_ok = bool(install_sovereign and vk_hashes_match and not vendor_circuits)
            status = "sovereign" if sovereign_ok else "violation"
        elif require_provenance:
            sovereign_ok = False
            status = "violation"
        else:
            sovereign_ok = True
            status = "pending_provenance"
    else:
        sovereign_ok = False
        status = "incomplete"

    return {
        "status": status,
        "sovereign_setup": install_sovereign,
        "sovereign_ok": sovereign_ok,
        "keys_ready": keys_ready,
        "install_json_present": install_present,
        "vk_hashes_match": vk_hashes_match,
        "vendor_circuits": vendor_circuits,
        "issues": issues,
    }