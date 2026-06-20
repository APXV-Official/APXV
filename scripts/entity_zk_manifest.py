"""
APX v1 — Entity ZK Key Manifest (Phase 3)

Tracks versioned verification keys for the 8 entity Groth16 circuits in apx-zk.
Separate from governance circuit manifest (apx-circuits).
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
    "normalization",
    "core-redaction",
    "compliance",
    "threat",
    "voice-redaction",
    "redaction-v1",
    "merkle-inclusion",
    "batch-merkle",
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def entity_keys_dir(base_path: Optional[Path] = None) -> Path:
    base = base_path or Path(__file__).parent.parent
    return base / "rust" / "apx-zk" / "keys"


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
    manifest["manifest_version"] = MANIFEST_VERSION
    manifest["circuit_version"] = CIRCUIT_VERSION
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    manifest.setdefault("circuits", {})
    manifest["circuits"][circuit] = {
        "circuit_version": CIRCUIT_VERSION,
        "pk_hash": _sha256_file(pk),
        "vk_hash": _sha256_file(vk),
        "pk_path": str(pk.relative_to(base)).replace("\\", "/"),
        "vk_path": str(vk.relative_to(base)).replace("\\", "/"),
        "setup_at": manifest["updated_at"],
    }
    write_manifest(manifest, base_path=base)
    return manifest["circuits"][circuit]


def rebuild_manifest(base_path: Optional[Path] = None) -> Dict[str, Any]:
    for circuit in ENTITY_CIRCUITS:
        try:
            update_manifest_for_circuit(circuit, base_path=base_path)
        except FileNotFoundError:
            pass
    return load_manifest(base_path)