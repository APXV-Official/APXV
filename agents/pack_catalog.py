"""Discover official agent packs from governance-libraries/."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import re

_APXV_ROOT = Path(__file__).resolve().parent.parent

OFFICIAL_PACK_IDS = frozenset(
    {
        "apxv-pack-reference-redaction",
        "apxv-pack-document-processing",
        "apxv-pack-ai-governance",
    }
)

# Scaffold leftovers / ephemeral packs — never show on Workbench shelf
HIDDEN_PACK_IDS = frozenset(
    {
        "apxv-pack-test-ui",
        "apxv-pack-my-agent-pack",
        "apxv-pack-release-smoke",
    }
)

HIDDEN_PACK_NAME_HINTS = (
    "test ui",
    "my agent pack",
)

GOVERNANCE_LIST_KEYS = {
    "rules": "rule",
    "workflows": "workflow",
    "knowledge": "knowledge",
}


def is_official_pack(pack_id: str) -> bool:
    return pack_id.strip() in OFFICIAL_PACK_IDS


def resolve_apxv_root(base_path: Path) -> Path:
    """Return base_path when it contains packs; otherwise the installed APXV root."""
    if (base_path / "governance-libraries").is_dir():
        return base_path
    return _APXV_ROOT


def parse_pack_manifest(pack_dir: Path) -> Dict[str, Any]:
    """Parse pack.yaml: metadata, agents[], governance file lists, policy_delta path."""
    pack_yaml = pack_dir / "pack.yaml"
    if not pack_yaml.exists():
        raise FileNotFoundError(f"pack.yaml missing in {pack_dir}")

    manifest: Dict[str, Any] = {
        "pack_id": pack_dir.name,
        "governance": {key: [] for key in GOVERNANCE_LIST_KEYS},
        "agents": [],
        "policy_delta": None,
    }
    section: Optional[str] = None
    gov_sub: Optional[str] = None
    agent_entry: Optional[Dict[str, str]] = None

    def _flush_agent_entry() -> None:
        nonlocal agent_entry
        if agent_entry:
            manifest["agents"].append(agent_entry)
            agent_entry = None

    pending_key: Optional[str] = None
    pending_parts: List[str] = []

    def _flush_pending() -> None:
        nonlocal pending_key, pending_parts
        if pending_key is not None:
            manifest[pending_key] = " ".join(pending_parts).strip()
            pending_key = None
            pending_parts = []

    for line in pack_yaml.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Folded/literal block continuation for top-level scalars (description: >-).
        if pending_key is not None:
            if ":" in stripped and not line[:1].isspace() and not stripped.startswith("-"):
                _flush_pending()
            else:
                pending_parts.append(stripped)
                continue

        if stripped == "governance:":
            _flush_agent_entry()
            _flush_pending()
            section = "governance"
            gov_sub = None
            continue
        if stripped == "capabilities:":
            _flush_agent_entry()
            _flush_pending()
            section = "capabilities"
            gov_sub = None
            continue
        if stripped == "agents:":
            _flush_agent_entry()
            _flush_pending()
            section = "agents"
            gov_sub = None
            continue

        if section == "agents":
            if stripped.startswith("- "):
                _flush_agent_entry()
                agent_entry = {}
                remainder = stripped[2:].strip()
                if remainder.startswith("id:"):
                    agent_entry["id"] = remainder.split(":", 1)[1].strip()
                continue
            if agent_entry is not None and ":" in stripped:
                key, value = stripped.split(":", 1)
                agent_entry[key.strip()] = value.strip()
            continue

        if section == "governance":
            if stripped.endswith(":") and not stripped.startswith("-"):
                gov_sub = stripped[:-1]
                if gov_sub not in manifest["governance"]:
                    manifest["governance"][gov_sub] = []
                continue
            if stripped.startswith("- ") and gov_sub:
                manifest["governance"][gov_sub].append(stripped[2:].strip())
            continue

        if section == "capabilities" and ":" in stripped:
            key, value = stripped.split(":", 1)
            if key.strip() == "policy_delta":
                manifest["policy_delta"] = value.strip()
            continue

        if ":" in stripped and section is None:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            # YAML folded/literal markers — capture following indented lines.
            if value in (">", ">-", "|", "|-"):
                pending_key = key
                pending_parts = []
            else:
                manifest[key] = value

    _flush_pending()
    _flush_agent_entry()

    if "pack_id" in manifest and isinstance(manifest["pack_id"], str):
        manifest["pack_id"] = manifest["pack_id"].strip()
    return manifest


def pack_dir_for(base_path: Path, pack_id: str) -> Optional[Path]:
    entry = get_pack(base_path, pack_id)
    if not entry:
        return None
    return resolve_apxv_root(base_path) / entry["path"]


def _parse_pack_yaml(text: str) -> Dict[str, str]:
    data: Dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _is_hidden_pack(pack_id: str, name: str = "") -> bool:
    if pack_id in HIDDEN_PACK_IDS:
        return True
    low = f"{pack_id} {name}".lower()
    return any(h in low for h in HIDDEN_PACK_NAME_HINTS)


def list_packs(
    base_path: Path,
    *,
    include_hidden: bool = False,
) -> List[Dict[str, Any]]:
    root = resolve_apxv_root(base_path) / "governance-libraries"
    packs: List[Dict[str, Any]] = []
    if not root.is_dir():
        return packs

    for pack_yaml in sorted(root.glob("apxv-pack-*/pack.yaml")):
        parsed = _parse_pack_yaml(pack_yaml.read_text(encoding="utf-8"))
        pack_dir = pack_yaml.parent
        pack_id = parsed.get("pack_id") or pack_dir.name
        name = parsed.get("name", pack_dir.name)
        if not include_hidden and _is_hidden_pack(pack_id, name):
            continue
        maturity = "official" if is_official_pack(pack_id) else "example"
        packs.append(
            {
                "id": pack_id,
                "name": name,
                "version": parsed.get("version", "0.0.0"),
                "description": parsed.get("description", ""),
                "requires_apxv1": parsed.get("requires_apxv1", ""),
                "official": is_official_pack(pack_id),
                "maturity": maturity,
                "path": str(pack_dir.relative_to(resolve_apxv_root(base_path))).replace("\\", "/"),
                "demo": str(
                    (pack_dir / "examples" / "run_pack_demo.py").relative_to(resolve_apxv_root(base_path))
                ).replace("\\", "/"),
            }
        )
    return packs


def get_pack(base_path: Path, pack_id: str) -> Optional[Dict[str, Any]]:
    apx_root = resolve_apxv_root(base_path)
    for pack in list_packs(base_path):
        if pack["id"] == pack_id or pack["id"].endswith(pack_id):
            pack_dir = apx_root / pack["path"]
            readme = pack_dir / "README.md"
            pack["readme_excerpt"] = ""
            if readme.exists():
                pack["readme_excerpt"] = readme.read_text(encoding="utf-8")[:2000]
            pack["governance_files"] = [
                str(p.relative_to(apx_root)).replace("\\", "/")
                for p in sorted(pack_dir.rglob("*"))
                if p.is_file() and "governance" in p.parts
            ]
            try:
                manifest = parse_pack_manifest(pack_dir)
                pack["agents"] = manifest.get("agents", [])
                pack["official"] = is_official_pack(pack["id"])
            except FileNotFoundError:
                pack["agents"] = []
            return pack
    return None


def find_pack(base_path: Path, pack: Optional[str]) -> Optional[Dict[str, Any]]:
    """Resolve a pack alias or id to catalog metadata."""
    if not pack:
        pack = "reference"
    normalized = pack.strip().lower()
    for entry in list_packs(base_path):
        entry_id = entry["id"].lower()
        if normalized == entry_id or normalized == entry["id"]:
            return entry
        if normalized in entry_id:
            return entry
    aliases = {
        "reference": "reference",
        "document": "document",
        "ai": "ai",
    }
    if normalized in aliases:
        needle = aliases[normalized]
        for entry in list_packs(base_path):
            if needle in entry["id"].lower():
                return entry
    return None


def resolve_pack_key(pack: Optional[str], base_path: Optional[Path] = None) -> str:
    """Return runtime dispatch key: reference, document, ai, or custom pack id."""
    if base_path is not None:
        entry = find_pack(base_path, pack)
        if entry:
            entry_id = entry["id"].lower()
            if "document" in entry_id:
                return "document"
            if "ai" in entry_id and "governance" in entry_id:
                return "ai"
            if "reference" in entry_id:
                return "reference"
            return entry["id"]
    normalized = (pack or "reference").strip().lower()
    aliases = {
        "reference": "reference",
        "apxv-pack-reference-redaction": "reference",
        "document": "document",
        "apxv-pack-document-processing": "document",
        "ai": "ai",
        "apxv-pack-ai-governance": "ai",
    }
    if normalized not in aliases:
        if normalized.startswith("apxv-pack-"):
            return pack.strip()
        raise ValueError(f"Unknown pack: {pack}. Use reference, document, ai, or a pack id.")
    return aliases[normalized]