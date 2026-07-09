"""install.json provenance record (step 8)."""

from __future__ import annotations

import hashlib
import json
import socket
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from scripts.bootstrap.constants import BOOTSTRAP_VERSION, ENTITY_CIRCUITS, GOVERNANCE_CIRCUITS
from scripts.bootstrap.zk import collect_vk_hashes


def compute_host_id() -> str:
    """Stable-ish host fingerprint: sha256(hostname:uuid4)."""
    payload = f"{socket.gethostname()}:{uuid.uuid4()}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_install_json(
    base_path: Path,
    *,
    profile: str,
    zk_setup_at: str,
    ollama: Dict[str, Any],
    voice: Dict[str, Any],
    sovereign_setup: bool = True,
) -> Dict[str, Any]:
    """Assemble install.json per V1.3-PRODUCT-SPEC §4.2."""
    return {
        "bootstrap_version": BOOTSTRAP_VERSION,
        "profile": profile,
        "sovereign_setup": sovereign_setup,
        "zk_setup_at": zk_setup_at,
        "host_id": compute_host_id(),
        "governance_circuits": list(GOVERNANCE_CIRCUITS),
        "entity_circuits": list(ENTITY_CIRCUITS),
        "vk_hashes": collect_vk_hashes(base_path),
        "ollama": {
            "enabled": bool(ollama.get("enabled")),
            "model": ollama.get("model"),
            "verified": bool(ollama.get("verified")),
        },
        "voice": {
            "enabled": bool(voice.get("enabled")),
            "backend": voice.get("backend"),
            "model": voice.get("model"),
        },
        "bootstrap_completed_at": datetime.now(timezone.utc).isoformat(),
    }


def write_install_json(base_path: Path, payload: Dict[str, Any]) -> Path:
    """Persist managed/config/install.json."""
    path = base_path / "managed" / "config" / "install.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def read_install_json(base_path: Path) -> Dict[str, Any] | None:
    path = base_path / "managed" / "config" / "install.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))