"""One-time install.json migration for v1.3.x -> v1.4.0 circuit trim."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from scripts.bootstrap.constants import ENTITY_CIRCUITS

ROOT = Path(__file__).resolve().parent.parent


def resolve_base_path() -> Path:
    env = os.environ.get("APXV_ROOT") or os.environ.get("APXV_BASE_PATH")
    if env:
        return Path(env).resolve()
    return ROOT

REMOVED_ENTITY_CIRCUITS = frozenset({"normalization", "threat"})


def migrate_install_json(base_path: Path) -> dict[str, object]:
    path = base_path / "managed" / "config" / "install.json"
    if not path.is_file():
        return {"changed": False, "reason": "install.json missing"}

    data = json.loads(path.read_text(encoding="utf-8"))
    entity = list(data.get("entity_circuits") or [])
    vk_hashes = dict(data.get("vk_hashes") or {})
    removed = [c for c in entity if c in REMOVED_ENTITY_CIRCUITS]
    for circuit in REMOVED_ENTITY_CIRCUITS:
        vk_hashes.pop(circuit, None)
    entity = [c for c in entity if c not in REMOVED_ENTITY_CIRCUITS]

    changed = bool(removed) or entity != list(data.get("entity_circuits") or [])
    if not changed and data.get("bootstrap_version") == "1.4.0":
        return {"changed": False, "reason": "already migrated"}

    data["entity_circuits"] = list(ENTITY_CIRCUITS) if entity != list(ENTITY_CIRCUITS) else entity
    data["vk_hashes"] = vk_hashes
    if data.get("bootstrap_version", "").startswith("1.3"):
        data["bootstrap_version"] = "1.4.0"

    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {"changed": True, "removed": removed, "entity_circuits": data["entity_circuits"]}


def main() -> int:
    base = resolve_base_path()
    result = migrate_install_json(base)
    if result.get("changed"):
        print(f"migrated install.json at {base}")
        if result.get("removed"):
            print(f"  removed deprecated circuits: {result['removed']}")
    else:
        print(result.get("reason", "no changes"))
    return 0


if __name__ == "__main__":
    sys.exit(main())