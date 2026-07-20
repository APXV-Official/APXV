"""
APXV Studio service — create, test, promote operator Agents and Packs.

Studio Test uses the same pipeline runner as Workbench Run.
Definitions live under managed/studio/; packs under governance-libraries/.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .capability_policy import CapabilityPolicyManager
from .pack_catalog import list_packs, parse_pack_manifest, resolve_apxv_root
from .pack_install import activate_pack
from .pipeline_runner import run_pipeline_document
from .pipeline_store import delete_pipeline, save_pipeline
from .runtime import APXRuntime

STUDIO_REL = Path("managed") / "studio"
AGENTS_REL = STUDIO_REL / "agents"
META_REL = STUDIO_REL / "catalog.json"

_AGENT_ID_RE = re.compile(r"^APXV-AGENT-[A-Z0-9][A-Z0-9-]*$")
_PACK_ID_RE = re.compile(r"^apxv-pack-[a-z0-9][a-z0-9-]*$")

DEFAULT_CAPS = [
    "execute_agent",
    "read_specification",
    "write_artifact",
]


class StudioError(Exception):
    """Studio create/test/promote failures."""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _studio_root(base_path: Path) -> Path:
    root = base_path / STUDIO_REL
    root.mkdir(parents=True, exist_ok=True)
    (base_path / AGENTS_REL).mkdir(parents=True, exist_ok=True)
    return root


def _load_catalog(base_path: Path) -> Dict[str, Any]:
    path = base_path / META_REL
    if not path.exists():
        return {"agents": {}, "packs": {}, "proofs": {}, "updated_at": None}
    # utf-8-sig tolerates PowerShell/Windows BOM-tainted files
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {"agents": {}, "packs": {}, "proofs": {}, "updated_at": None}
    data.setdefault("agents", {})
    data.setdefault("packs", {})
    data.setdefault("proofs", {})
    return data


def _save_catalog(base_path: Path, catalog: Dict[str, Any]) -> None:
    _studio_root(base_path)
    catalog["updated_at"] = _utcnow()
    path = base_path / META_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    # Explicit utf-8 without BOM (Windows default tools often add BOM)
    path.write_bytes(
        (json.dumps(catalog, indent=2) + "\n").encode("utf-8")
    )


def _validate_agent_id(agent_id: str) -> str:
    aid = agent_id.strip().upper().replace("_", "-")
    if not aid.startswith("APXV-AGENT-"):
        aid = f"APXV-AGENT-{aid.lstrip('-')}"
    if not _AGENT_ID_RE.match(aid):
        raise StudioError(
            "agent id must match APXV-AGENT-<SLUG> (A-Z, 0-9, hyphens)"
        )
    return aid


def _validate_pack_id(pack_id: str) -> str:
    pid = pack_id.strip().lower()
    if not pid.startswith("apxv-pack-"):
        pid = f"apxv-pack-{pid}"
    if not _PACK_ID_RE.match(pid):
        raise StudioError(
            "pack id must match apxv-pack-<slug> (lowercase letters, numbers, hyphens)"
        )
    return pid


def agent_dir(base_path: Path, agent_id: str) -> Path:
    return base_path / AGENTS_REL / agent_id


def load_operator_agent(base_path: Path, agent_id: str) -> Optional[Dict[str, Any]]:
    d = agent_dir(base_path, agent_id)
    manifest_path = d / "manifest.json"
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    instruction = ""
    knowledge = ""
    ip = d / "instruction.md"
    kp = d / "knowledge.md"
    if ip.exists():
        instruction = ip.read_text(encoding="utf-8")
    if kp.exists():
        knowledge = kp.read_text(encoding="utf-8")
    catalog = _load_catalog(base_path)
    meta = (catalog.get("agents") or {}).get(agent_id) or {}
    return {
        **manifest,
        "instruction_md": instruction,
        "knowledge_md": knowledge,
        "promoted": bool(meta.get("promoted", manifest.get("promoted", False))),
        "maturity": meta.get("maturity") or manifest.get("maturity") or "draft",
        "last_test": meta.get("last_test") or manifest.get("last_test"),
        "path": str(d.relative_to(base_path)).replace("\\", "/"),
    }


def list_operator_agents(base_path: Path) -> List[Dict[str, Any]]:
    root = base_path / AGENTS_REL
    if not root.is_dir():
        return []
    out: List[Dict[str, Any]] = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "manifest.json").exists():
            rec = load_operator_agent(base_path, child.name)
            if rec:
                out.append(rec)
    return out


def _grant_capabilities(
    runtime: APXRuntime,
    agent_id: str,
    capabilities: List[str],
) -> None:
    manager = CapabilityPolicyManager(runtime.base_path)
    try:
        current = manager.load_policy()
        agents = dict(current.get("agents") or {})
    except Exception:
        agents = {}
    caps = list(dict.fromkeys((capabilities or []) + DEFAULT_CAPS))
    agents[agent_id] = caps
    manager.publish_policy(
        agents,
        issued_by="studio",
        description=f"Studio grant for {agent_id}",
    )
    # Reload checker
    runtime.capability_checker._load_policy()


def save_operator_agent(
    runtime: APXRuntime,
    *,
    agent_id: str,
    name: str,
    description: str = "",
    agent_type: str = "agentic",
    instruction_md: str = "",
    knowledge_md: str = "",
    capabilities: Optional[List[str]] = None,
) -> Dict[str, Any]:
    aid = _validate_agent_id(agent_id)
    atype = (agent_type or "agentic").strip().lower()
    if atype not in ("deterministic", "agentic", "hybrid", "tool"):
        raise StudioError("agent_type must be deterministic|agentic|hybrid|tool")

    d = agent_dir(runtime.base_path, aid)
    d.mkdir(parents=True, exist_ok=True)
    caps = list(dict.fromkeys((capabilities or []) + DEFAULT_CAPS))
    catalog = _load_catalog(runtime.base_path)
    prev = (catalog.get("agents") or {}).get(aid) or {}
    manifest = {
        "id": aid,
        "name": (name or aid).strip(),
        "description": (description or "").strip(),
        "agent_type": atype,
        "kind": "operator",
        "capabilities": caps,
        "created_at": prev.get("created_at") or _utcnow(),
        "updated_at": _utcnow(),
        "promoted": bool(prev.get("promoted", False)),
        "maturity": prev.get("maturity") or "draft",
        "last_test": prev.get("last_test"),
    }
    (d / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (d / "instruction.md").write_text(
        instruction_md if instruction_md.strip() else f"# {manifest['name']}\n\nOperator agent instructions.\n",
        encoding="utf-8",
    )
    (d / "knowledge.md").write_text(
        knowledge_md if knowledge_md.strip() else f"# Knowledge\n\nBound knowledge for {aid}.\n",
        encoding="utf-8",
    )
    _grant_capabilities(runtime, aid, caps)
    catalog.setdefault("agents", {})[aid] = {
        "promoted": manifest["promoted"],
        "maturity": manifest["maturity"],
        "last_test": manifest.get("last_test"),
        "name": manifest["name"],
        "updated_at": manifest["updated_at"],
    }
    _save_catalog(runtime.base_path, catalog)
    return load_operator_agent(runtime.base_path, aid) or manifest


def save_studio_pack(
    runtime: APXRuntime,
    *,
    pack_id: str,
    name: str,
    description: str = "",
    rules_md: str = "",
    workflow_md: str = "",
    knowledge_md: str = "",
    agent_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    pid = _validate_pack_id(pack_id)
    apx_root = resolve_apxv_root(runtime.base_path)
    libs = apx_root / "governance-libraries"
    libs.mkdir(parents=True, exist_ok=True)
    target = libs / pid
    target.mkdir(parents=True, exist_ok=True)

    agents = agent_ids or ["APXV-AGENT-001"]
    # Ensure at least one runnable agent exists for pack smoke
    agent_lines = []
    for i, aid in enumerate(agents):
        agent_lines.append(f"  - id: {aid}")
        agent_lines.append("    type: deterministic")
        if i == 0 and aid.startswith("APXV-AGENT-00"):
            agent_lines.append("    module: agents.agent1")
            agent_lines.append("    entry: process_text")

    # Quoted scalars — parse_pack_manifest is line-oriented and does not
    # understand YAML folded blocks (description: >- was returned as ">-").
    def _yaml_quote(value: str) -> str:
        cleaned = " ".join((value or "").split())
        escaped = cleaned.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    desc = description or f"Operator pack {pid} authored in APXV Studio."
    pack_yaml = f"""# Studio-authored pack
pack_id: {pid}
name: {_yaml_quote(name or pid)}
version: 0.1.0
requires_apxv1: ">=1.2.0"
author: APXV-Studio
license: Apache-2.0
description: {_yaml_quote(desc)}

agents:
{chr(10).join(agent_lines) if agent_lines else "  - id: APXV-AGENT-001"}

governance:
  rules:
    - governance/rules/RULE-STUDIO-001.md
  workflows:
    - governance/workflows/WORKFLOW-STUDIO-001.md
  knowledge:
    - governance/knowledge/KB-STUDIO-001.md

capabilities:
  policy_delta: capabilities/policy-delta.json
"""
    (target / "pack.yaml").write_text(pack_yaml, encoding="utf-8")
    for sub in (
        "governance/rules",
        "governance/workflows",
        "governance/knowledge",
        "capabilities",
        "agents",
    ):
        (target / sub).mkdir(parents=True, exist_ok=True)

    (target / "governance" / "rules" / "RULE-STUDIO-001.md").write_text(
        rules_md.strip()
        or f"# RULE-STUDIO-001\n\nStudio pack rules for {pid}.\n",
        encoding="utf-8",
    )
    (target / "governance" / "workflows" / "WORKFLOW-STUDIO-001.md").write_text(
        workflow_md.strip()
        or f"# WORKFLOW-STUDIO-001\n\nStudio pack workflow for {pid}.\n",
        encoding="utf-8",
    )
    (target / "governance" / "knowledge" / "KB-STUDIO-001.md").write_text(
        knowledge_md.strip()
        or f"# KB-STUDIO-001\n\nStudio pack knowledge for {pid}.\n",
        encoding="utf-8",
    )

    # Capability grants for bound agents
    delta_agents: Dict[str, List[str]] = {}
    for aid in agents:
        delta_agents[aid] = list(DEFAULT_CAPS)
    (target / "capabilities" / "policy-delta.json").write_text(
        json.dumps({"agents_to_add": delta_agents}, indent=2) + "\n",
        encoding="utf-8",
    )
    (target / "capabilities" / "CAPABILITIES.md").write_text(
        f"# Capabilities — {name or pid}\n\n"
        + "\n".join(f"- `{a}`: execute_agent, read_specification, write_artifact" for a in agents)
        + "\n",
        encoding="utf-8",
    )
    (target / "ACCEPTANCE.md").write_text(
        f"# Acceptance — {pid}\n\nStudio-authored pack. Test via Studio Test, then promote.\n",
        encoding="utf-8",
    )
    (target / "README.md").write_text(
        f"# {name or pid}\n\n{description or 'Studio-authored APXV pack.'}\n",
        encoding="utf-8",
    )
    (target / "agents" / "__init__.py").write_text("", encoding="utf-8")

    catalog = _load_catalog(runtime.base_path)
    catalog.setdefault("packs", {})[pid] = {
        "promoted": False,
        "maturity": "draft",
        "name": name or pid,
        "last_test": None,
        "updated_at": _utcnow(),
    }
    _save_catalog(runtime.base_path, catalog)

    return get_studio_pack(runtime.base_path, pid)


def get_studio_pack(base_path: Path, pack_id: str) -> Dict[str, Any]:
    pid = pack_id.strip()
    apx_root = resolve_apxv_root(base_path)
    pack_dir = apx_root / "governance-libraries" / pid
    if not pack_dir.is_dir():
        raise StudioError(f"Pack not found: {pid}")
    try:
        manifest = parse_pack_manifest(pack_dir)
    except FileNotFoundError as exc:
        raise StudioError(str(exc)) from exc
    catalog = _load_catalog(base_path)
    meta = (catalog.get("packs") or {}).get(pid) or {}

    def _read(rel: str) -> str:
        p = pack_dir / rel
        return p.read_text(encoding="utf-8") if p.exists() else ""

    return {
        "id": pid,
        "name": manifest.get("name") or meta.get("name") or pid,
        "description": manifest.get("description") or "",
        "version": manifest.get("version"),
        "agents": [a.get("id") for a in (manifest.get("agents") or []) if a.get("id")],
        "rules_md": _read("governance/rules/RULE-STUDIO-001.md"),
        "workflow_md": _read("governance/workflows/WORKFLOW-STUDIO-001.md"),
        "knowledge_md": _read("governance/knowledge/KB-STUDIO-001.md"),
        "promoted": bool(meta.get("promoted", False)),
        "maturity": meta.get("maturity") or "draft",
        "last_test": meta.get("last_test"),
        "path": str(pack_dir.relative_to(apx_root)).replace("\\", "/"),
        "studio_authored": True,
    }


def list_studio_packs(base_path: Path) -> List[Dict[str, Any]]:
    catalog = _load_catalog(base_path)
    out: List[Dict[str, Any]] = []
    for pid, meta in sorted((catalog.get("packs") or {}).items()):
        try:
            out.append(get_studio_pack(base_path, pid))
        except StudioError:
            out.append({"id": pid, **meta, "studio_authored": True})
    return out


def _record_agent_test(
    base_path: Path, agent_id: str, result: Dict[str, Any]
) -> None:
    catalog = _load_catalog(base_path)
    catalog.setdefault("agents", {}).setdefault(agent_id, {})
    catalog["agents"][agent_id]["last_test"] = result
    if result.get("final_status") == "succeeded":
        catalog["agents"][agent_id]["maturity"] = catalog["agents"][agent_id].get(
            "maturity"
        ) or "draft"
    _save_catalog(base_path, catalog)
    d = agent_dir(base_path, agent_id)
    mp = d / "manifest.json"
    if mp.exists():
        man = json.loads(mp.read_text(encoding="utf-8"))
        man["last_test"] = result
        man["updated_at"] = _utcnow()
        mp.write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")


def _record_pack_test(base_path: Path, pack_id: str, result: Dict[str, Any]) -> None:
    catalog = _load_catalog(base_path)
    catalog.setdefault("packs", {}).setdefault(pack_id, {})
    catalog["packs"][pack_id]["last_test"] = result
    _save_catalog(base_path, catalog)


def run_operator_agent_test(
    runtime: APXRuntime,
    agent_id: str,
    *,
    input_text: str = "Studio test sample: contact test@example.com",
) -> Dict[str, Any]:
    aid = _validate_agent_id(agent_id)
    defn = load_operator_agent(runtime.base_path, aid)
    if not defn:
        raise StudioError(f"Operator agent not found: {aid}")

    pipeline_id = f"apxv-pipeline-studio-test-{aid.lower().replace('_', '-')[-24:]}"
    doc = {
        "apiVersion": "apxv.pipeline/v0.1",
        "kind": "Pipeline",
        "id": pipeline_id,
        "name": f"Studio test {aid}",
        "version": "0.1.0",
        "description": "Ephemeral Studio agent test pipeline",
        "defaults": {"attest": False, "on_step_failure": "stop"},
        "steps": [
            {
                "id": "studio_agent",
                "name": defn.get("name") or aid,
                "uses": f"agent:{aid}",
                "enabled": True,
            }
        ],
    }
    try:
        save_pipeline(runtime.base_path, doc, fmt="yaml", overwrite=True)
    except Exception:
        pass
    try:
        result = run_pipeline_document(doc, runtime=runtime, input_text=input_text)
    finally:
        # Keep Workbench library clean — studio tests are ephemeral.
        try:
            delete_pipeline(runtime.base_path, pipeline_id)
        except Exception:
            pass
    test_rec = {
        "at": _utcnow(),
        "final_status": result.get("final_status"),
        "pipeline_id": pipeline_id,
        "error": result.get("error"),
        "run_trace": result.get("run_trace"),
    }
    _record_agent_test(runtime.base_path, aid, test_rec)
    return {
        "ok": result.get("final_status") == "succeeded",
        "agent_id": aid,
        "result": result,
        "last_test": test_rec,
    }


def run_studio_pack_test(
    runtime: APXRuntime,
    pack_id: str,
    *,
    input_text: str = "Studio pack test: email demo@example.com phone 555-0100",
) -> Dict[str, Any]:
    pid = _validate_pack_id(pack_id)
    try:
        get_studio_pack(runtime.base_path, pid)
    except StudioError:
        # Allow testing any installed pack id
        pass

    try:
        activate_pack(runtime, pid, activated_by="studio", confirm=True)
    except Exception as exc:
        # Still try profile run
        activate_err = str(exc)
    else:
        activate_err = None

    pipeline_id = f"apxv-pipeline-studio-pack-{pid.replace('apxv-pack-', '')[:20]}"
    doc = {
        "apiVersion": "apxv.pipeline/v0.1",
        "kind": "Pipeline",
        "id": pipeline_id,
        "name": f"Studio pack test {pid}",
        "version": "0.1.0",
        "defaults": {"attest": False, "on_step_failure": "stop"},
        "steps": [
            {
                "id": "under_pack",
                "name": "Run under pack profile",
                "uses": "agent:APXV-AGENT-001",
                "pack_profile": pid,
                "enabled": True,
            }
        ],
    }
    try:
        save_pipeline(runtime.base_path, doc, fmt="yaml", overwrite=True)
    except Exception:
        pass
    try:
        result = run_pipeline_document(doc, runtime=runtime, input_text=input_text)
    finally:
        try:
            delete_pipeline(runtime.base_path, pipeline_id)
        except Exception:
            pass
    test_rec = {
        "at": _utcnow(),
        "final_status": result.get("final_status"),
        "pipeline_id": pipeline_id,
        "error": result.get("error") or activate_err,
        "run_trace": result.get("run_trace"),
        "activate_error": activate_err,
    }
    _record_pack_test(runtime.base_path, pid, test_rec)
    return {
        "ok": result.get("final_status") == "succeeded",
        "pack_id": pid,
        "result": result,
        "last_test": test_rec,
    }


def promote_agent(
    runtime: APXRuntime,
    agent_id: str,
    *,
    force: bool = False,
) -> Dict[str, Any]:
    aid = _validate_agent_id(agent_id)
    defn = load_operator_agent(runtime.base_path, aid)
    if not defn:
        raise StudioError(f"Operator agent not found: {aid}")
    last = defn.get("last_test") or {}
    if not force and last.get("final_status") != "succeeded":
        raise StudioError(
            "Agent test has not succeeded. Run Test successfully before promote, "
            "or pass force=true to promote as Draft."
        )
    catalog = _load_catalog(runtime.base_path)
    catalog.setdefault("agents", {}).setdefault(aid, {})
    catalog["agents"][aid]["promoted"] = True
    catalog["agents"][aid]["maturity"] = (
        "ready" if last.get("final_status") == "succeeded" else "draft"
    )
    catalog["agents"][aid]["promoted_at"] = _utcnow()
    _save_catalog(runtime.base_path, catalog)
    d = agent_dir(runtime.base_path, aid)
    mp = d / "manifest.json"
    if mp.exists():
        man = json.loads(mp.read_text(encoding="utf-8"))
        man["promoted"] = True
        man["maturity"] = catalog["agents"][aid]["maturity"]
        mp.write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")
    return load_operator_agent(runtime.base_path, aid) or defn


def promote_pack(
    runtime: APXRuntime,
    pack_id: str,
    *,
    force: bool = False,
) -> Dict[str, Any]:
    pid = _validate_pack_id(pack_id)
    catalog = _load_catalog(runtime.base_path)
    meta = (catalog.get("packs") or {}).get(pid) or {}
    last = meta.get("last_test") or {}
    if not force and last.get("final_status") != "succeeded":
        raise StudioError(
            "Pack test has not succeeded. Run Test successfully before promote, "
            "or pass force=true to promote as Draft."
        )
    catalog.setdefault("packs", {}).setdefault(pid, {})
    catalog["packs"][pid]["promoted"] = True
    catalog["packs"][pid]["maturity"] = (
        "ready" if last.get("final_status") == "succeeded" else "draft"
    )
    catalog["packs"][pid]["promoted_at"] = _utcnow()
    _save_catalog(runtime.base_path, catalog)
    try:
        return get_studio_pack(runtime.base_path, pid)
    except StudioError:
        return {"id": pid, **catalog["packs"][pid]}


def list_promoted_for_workbench(base_path: Path) -> Dict[str, Any]:
    """Shelf-facing: promoted operator agents + packs + proof profiles."""
    from .proof_studio import list_promoted_proofs

    agents = [
        a
        for a in list_operator_agents(base_path)
        if a.get("promoted") or a.get("maturity") == "ready"
    ]
    packs = [
        p
        for p in list_studio_packs(base_path)
        if p.get("promoted") or p.get("maturity") == "ready"
    ]
    proofs = list_promoted_proofs(base_path)
    return {"agents": agents, "packs": packs, "proofs": proofs}


def instruction_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()
