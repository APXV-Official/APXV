"""Load vendor VK blocklist for migration guard (PR-10 file; enforced in PR-11 doctor)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Set

_BLOCKLIST_PATH = Path(__file__).resolve().parent / "vendor_vk_blocklist.json"


@lru_cache(maxsize=1)
def load_vendor_vk_blocklist() -> Dict[str, Any]:
    if not _BLOCKLIST_PATH.is_file():
        return {"vk_hashes": []}
    return json.loads(_BLOCKLIST_PATH.read_text(encoding="utf-8"))


def vendor_vk_hashes() -> Set[str]:
    payload = load_vendor_vk_blocklist()
    hashes: List[str] = payload.get("vk_hashes") or []
    return {h.lower() for h in hashes if isinstance(h, str)}


def is_vendor_vk_hash(vk_hash: str) -> bool:
    return vk_hash.lower() in vendor_vk_hashes()