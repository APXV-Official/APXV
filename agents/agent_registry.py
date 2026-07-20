"""Agent Registry — discover core and pack agents for Pack Studio / API v2."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .agent_base import DEFAULT_AGENT_CAPABILITIES
from .pack_catalog import get_pack, list_packs, pack_dir_for, parse_pack_manifest, resolve_apxv_root
from .runtime import APXVRuntime

CORE_AGENT_CATALOG: Dict[str, Dict[str, Any]] = {
    "APXV-AGENT-001": {
        "name": "RuleGovernedRedactor",
        "kind": "core",
        "agent_type": "deterministic",
        "module": "agents.agent1",
        "description": "Rule-governed text redaction (APXV-RULE-001).",
        "runnable": True,
    },
    "APXV-AGENT-002": {
        "name": "WorkflowOrchestrator",
        "kind": "core",
        "agent_type": "deterministic",
        "module": "agents.agent2",
        "description": "Workflow orchestration and proposed artifact packaging (APXV-WF-001).",
        "runnable": True,
    },
    "APXV-AGENT-003": {
        "name": "AttestationCoordinator",
        "kind": "core",
        "agent_type": "deterministic",
        "module": "agents.agent3",
        "description": "Governance decision and attestation coordination.",
        "runnable": True,
    },
    "APXV-AGENT-LLM-001": {
        "name": "LLMReasoner",
        "kind": "core",
        "agent_type": "agentic",
        "module": "agents.llm_reasoner",
        "description": "Local LLM review step (simulated or Ollama-backed).",
        "runnable": True,
    },
    # Reserved / not yet bound in pipeline_runner — omit from Workbench shelf
    "APXV-AGENT-TOOL-001": {
        "name": "ToolRunner",
        "kind": "core",
        "agent_type": "tool",
        "module": "agents.tool_runner",
        "description": "Reserved tool agent slot (not placeable until runner binds it).",
        "runnable": False,
    },
}

# Agents the freeform Workbench runner can execute today
RUNNABLE_CORE_AGENT_IDS = frozenset(
    {
        "APXV-AGENT-001",
        "APXV-AGENT-002",
        "APXV-AGENT-003",
        "APXV-AGENT-LLM-001",
    }
)


def _capabilities_for(
    agent_id: str,
    runtime: Optional[APXVRuntime] = None,
) -> List[str]:
    if runtime is not None:
        caps = runtime.capability_checker.get_agent_capabilities(agent_id)
        if caps:
            return sorted(caps)
    return sorted(DEFAULT_AGENT_CAPABILITIES.get(agent_id, []))


def _agent_module_path(pack_dir: Path, module: str) -> Optional[str]:
    """Resolve pack-local module path when module is not a core agents.* import."""
    if module.startswith("agents."):
        stem = module.split(".", 1)[1]
        candidate = pack_dir / "agents" / f"{stem}.py"
        if candidate.is_file():
            return str(candidate.relative_to(pack_dir)).replace("\\", "/")
    return None


def _discover_pack_agent_files(pack_dir: Path) -> List[Dict[str, str]]:
    agents_dir = pack_dir / "agents"
    if not agents_dir.is_dir():
        return []
    discovered: List[Dict[str, str]] = []
    for path in sorted(agents_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue
        discovered.append(
            {
                "file": str(path.relative_to(pack_dir)).replace("\\", "/"),
                "stem": path.stem,
            }
        )
    return discovered


def _base_record(
    agent_id: str,
    *,
    runtime: Optional[APXVRuntime] = None,
) -> Dict[str, Any]:
    meta = CORE_AGENT_CATALOG.get(agent_id, {})
    return {
        "id": agent_id,
        "name": meta.get("name", agent_id),
        "kind": meta.get("kind", "pack"),
        "agent_type": meta.get("agent_type", "deterministic"),
        "module": meta.get("module"),
        "description": meta.get("description", ""),
        "packs": [],
        "capabilities": _capabilities_for(agent_id, runtime),
        "module_files": [],
        "runnable": bool(meta.get("runnable", agent_id in RUNNABLE_CORE_AGENT_IDS)),
        "maturity": "core" if agent_id in CORE_AGENT_CATALOG else "example",
    }


def _merge_agent(
    index: Dict[str, Dict[str, Any]],
    agent_id: str,
    *,
    pack_id: str,
    manifest_spec: Optional[Dict[str, str]] = None,
    pack_dir: Optional[Path] = None,
    runtime: Optional[APXVRuntime] = None,
) -> None:
    record = index.get(agent_id)
    if record is None:
        record = _base_record(agent_id, runtime=runtime)
        index[agent_id] = record

    if pack_id not in record["packs"]:
        record["packs"].append(pack_id)

    if manifest_spec:
        record["agent_type"] = manifest_spec.get("type") or record["agent_type"]
        if manifest_spec.get("module"):
            record["module"] = manifest_spec["module"]
        if agent_id in CORE_AGENT_CATALOG:
            record["kind"] = "core"
        elif record["kind"] == "core" and agent_id not in CORE_AGENT_CATALOG:
            record["kind"] = "pack"

    if pack_dir and record.get("module"):
        module_path = _agent_module_path(pack_dir, record["module"])
        if module_path and module_path not in record["module_files"]:
            record["module_files"].append(module_path)


def _build_index(
    base_path: Path,
    *,
    runtime: Optional[APXVRuntime] = None,
) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}

    for agent_id in CORE_AGENT_CATALOG:
        caps = _capabilities_for(agent_id, runtime)
        if caps or agent_id.startswith("APXV-AGENT-00"):
            index[agent_id] = _base_record(agent_id, runtime=runtime)

    apx_root = resolve_apxv_root(base_path)
    for pack in list_packs(base_path):
        pack_id = pack["id"]
        pack_dir = apx_root / pack["path"]
        if not pack_dir.is_dir():
            continue
        try:
            manifest = parse_pack_manifest(pack_dir)
        except FileNotFoundError:
            continue

        for spec in manifest.get("agents", []):
            agent_id = spec.get("id")
            if not agent_id:
                continue
            _merge_agent(
                index,
                agent_id,
                pack_id=pack_id,
                manifest_spec=spec,
                pack_dir=pack_dir,
                runtime=runtime,
            )

        # Only attach module files for agents already declared in pack.yaml.
        # Do NOT invent shelf agents from helper modules (document_agents.py → fake IDs).
        yaml_ids = {spec.get("id") for spec in manifest.get("agents", []) if spec.get("id")}
        for discovered in _discover_pack_agent_files(pack_dir):
            for agent_id in yaml_ids:
                if agent_id not in index:
                    continue
                fpath = discovered["file"]
                if fpath not in index[agent_id].get("module_files", []):
                    index[agent_id].setdefault("module_files", []).append(fpath)

    # Studio operator agents (managed/studio/agents)
    try:
        from .studio_service import list_operator_agents

        for op in list_operator_agents(base_path):
            aid = op.get("id")
            if not aid:
                continue
            index[aid] = {
                "id": aid,
                "name": op.get("name") or aid,
                "kind": "operator",
                "agent_type": op.get("agent_type") or "agentic",
                "module": "agents.studio_service",
                "description": op.get("description") or "Studio-authored operator agent",
                "packs": [],
                "capabilities": op.get("capabilities")
                or _capabilities_for(aid, runtime),
                "module_files": [],
                "promoted": bool(op.get("promoted")),
                "maturity": op.get("maturity") or "draft",
            }
    except Exception:
        pass

    return index


def list_agents(
    base_path: Path,
    *,
    runtime: Optional[APXVRuntime] = None,
    runnable_only: bool = True,
) -> List[Dict[str, Any]]:
    """Return known agents (core + pack + operator), sorted by id.

    runnable_only=True (default) excludes reserved/unbound agents so Workbench
    shelf does not offer steps the runner cannot execute.
    """
    index = _build_index(base_path, runtime=runtime)
    agents = sorted(index.values(), key=lambda item: item["id"])
    for agent in agents:
        agent["packs"] = sorted(agent.get("packs", []))
        agent["module_files"] = sorted(agent.get("module_files", []))
        if "runnable" not in agent:
            if agent.get("kind") == "operator":
                agent["runnable"] = True
            else:
                agent["runnable"] = agent["id"] in RUNNABLE_CORE_AGENT_IDS
    if runnable_only:
        agents = [a for a in agents if a.get("runnable")]
    return agents


def get_agent(
    base_path: Path,
    agent_id: str,
    *,
    runtime: Optional[APXVRuntime] = None,
) -> Optional[Dict[str, Any]]:
    index = _build_index(base_path, runtime=runtime)
    record = index.get(agent_id)
    if not record:
        for key, value in index.items():
            if key.endswith(agent_id) or agent_id.endswith(key):
                record = value
                break
    if not record:
        return None
    result = dict(record)
    result["packs"] = sorted(result.get("packs", []))
    result["module_files"] = sorted(result.get("module_files", []))
    return result


def agents_for_pack(
    base_path: Path,
    pack_id: str,
    *,
    runtime: Optional[APXVRuntime] = None,
) -> Dict[str, Any]:
    """Return the agent chain declared in pack.yaml (execution order)."""
    entry = get_pack(base_path, pack_id)
    if not entry:
        return {"pack_id": pack_id, "agents": [], "discovered_modules": []}

    pack_dir = pack_dir_for(base_path, entry["id"])
    if not pack_dir:
        return {"pack_id": entry["id"], "agents": [], "discovered_modules": []}

    manifest = parse_pack_manifest(pack_dir)
    chain: List[Dict[str, Any]] = []
    for index, spec in enumerate(manifest.get("agents", [])):
        agent_id = spec.get("id")
        if not agent_id:
            continue
        detail = get_agent(base_path, agent_id, runtime=runtime) or _base_record(
            agent_id, runtime=runtime
        )
        chain.append(
            {
                **detail,
                "chain_index": index,
                "declared_module": spec.get("module"),
                "declared_type": spec.get("type"),
            }
        )

    referenced_files: Set[str] = set()
    for spec in manifest.get("agents", []):
        module = spec.get("module")
        if module:
            module_path = _agent_module_path(pack_dir, module)
            if module_path:
                referenced_files.add(module_path)

    discovered = _discover_pack_agent_files(pack_dir)
    extras = [item for item in discovered if item["file"] not in referenced_files]

    return {
        "pack_id": entry["id"],
        "pack_name": entry.get("name"),
        "agents": chain,
        "discovered_modules": extras,
    }