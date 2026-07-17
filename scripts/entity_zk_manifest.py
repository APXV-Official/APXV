"""
APXV — Entity ZK Key Manifest (Phase 3)

Tracks versioned verification keys for the 6 default entity Groth16 circuits in apxv-zk.
Separate from governance circuit manifest (apxv-circuits).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import hashlib
import json

CIRCUIT_VERSION = "1.0.0"
MANIFEST_VERSION = "1.0.0"
ENTITY_CIRCUITS = (
    "core-redaction",
    "compliance",
    "voice-redaction",
    "redaction-v1",
    "merkle-inclusion",
    "batch-merkle",
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def entity_keys_dir(base_path: Optional[Path] = None) -> Path:
    base = base_path or Path(__file__).parent.parent
    return base / "rust" / "apxv-zk" / "keys"


def manifest_path(base_path: Optional[Path] = None) -> Path:
    return entity_keys_dir(base_path) / "entity-manifest.json"


def load_manifest(base_path: Optional[Path] = None) -> Dict[str, Any]:
    path = manifest_path(base_path)
    if not path.exists():
        return {
            "manifest_version": MANIFEST_VERSION,
            "circuit_version": CIRCUIT_VERSION,
            "updated_at": None,
            "circuits": {},
        }
    return json.loads(path.read_text(encoding="utf-8"))


def write_manifest(manifest: Dict[str, Any], base_path: Optional[Path] = None) -> Path:
    path = manifest_path(base_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def update_manifest_for_circuit(
    circuit: str,
    base_path: Optional[Path] = None,
) -> Dict[str, Any]:
    keys_dir = entity_keys_dir(base_path)
    pk = keys_dir / f"{circuit}.pk"
    vk = keys_dir / f"{circuit}.vk"
    if not pk.exists() or not vk.exists():
        raise FileNotFoundError(f"Missing entity keys for circuit {circuit}")

    base = base_path or Path(__file__).parent.parent
    manifest = load_manifest(base)
    manifest.setdefault("circuits", {})
    existing = manifest["circuits"].get(circuit, {})
    entry = {
        "circuit_version": CIRCUIT_VERSION,
        "pk_hash": _sha256_file(pk),
        "vk_hash": _sha256_file(vk),
        "pk_path": str(pk.relative_to(base)).replace("\\", "/"),
        "vk_path": str(vk.relative_to(base)).replace("\\", "/"),
    }
    unchanged = (
        existing.get("circuit_version") == entry["circuit_version"]
        and existing.get("pk_hash") == entry["pk_hash"]
        and existing.get("vk_hash") == entry["vk_hash"]
        and existing.get("pk_path") == entry["pk_path"]
        and existing.get("vk_path") == entry["vk_path"]
    )
    if unchanged:
        return existing

    manifest["manifest_version"] = MANIFEST_VERSION
    manifest["circuit_version"] = CIRCUIT_VERSION
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    entry["setup_at"] = existing.get("setup_at") or manifest["updated_at"]
    manifest["circuits"][circuit] = entry
    write_manifest(manifest, base_path=base)
    return manifest["circuits"][circuit]


def rebuild_manifest(base_path: Optional[Path] = None) -> Dict[str, Any]:
    for circuit in ENTITY_CIRCUITS:
        try:
            update_manifest_for_circuit(circuit, base_path=base_path)
        except FileNotFoundError:
            pass
    return load_manifest(base_path)


def verify_vk_hash(
    circuit: str,
    vk_hex: str,
    base_path: Optional[Path] = None,
) -> Dict[str, Any]:
    base = base_path or Path(__file__).parent.parent
    manifest = load_manifest(base)
    entry = manifest.get("circuits", {}).get(circuit)
    if not entry:
        return {
            "passed": False,
            "reason": f"No entity manifest entry for circuit {circuit}",
        }

    vk_path = base / entry["vk_path"]
    if not vk_path.exists():
        return {
            "passed": False,
            "reason": f"Entity manifest VK file missing: {vk_path}",
        }

    on_disk_hex = vk_path.read_bytes().hex()
    bundle_matches_disk = vk_hex.lower() == on_disk_hex.lower()
    return {
        "passed": bundle_matches_disk,
        "expected_vk_hash": entry["vk_hash"],
        "circuit_version": entry.get("circuit_version"),
        "reason": "VK matches entity manifest on-disk key"
        if bundle_matches_disk
        else "VK mismatch — wrong or stale entity verification key",
    }


def attach_entity_key_metadata(
    proof_bundle: Dict[str, Any],
    circuit: str,
    base_path: Optional[Path] = None,
) -> Dict[str, Any]:
    manifest = load_manifest(base_path)
    entry = manifest.get("circuits", {}).get(circuit, {})
    proof_bundle["circuit_version"] = entry.get("circuit_version", CIRCUIT_VERSION)
    proof_bundle["vk_hash"] = entry.get("vk_hash")
    proof_bundle["manifest_version"] = manifest.get("manifest_version")
    return proof_bundle