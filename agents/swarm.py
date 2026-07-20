"""
APXV Swarm v0 — directed pipeline handoffs under a parent run (v1.8).

Not multi-tenant cloud. Local composition of pipelines only.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .pipeline_runner import run_stored_pipeline
from .pipeline_spec import PipelineSpecError
from .runtime import APXRuntime

SWARMS_REL = Path("managed") / "swarms"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def swarms_dir(base_path: Path) -> Path:
    path = base_path / SWARMS_REL
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_swarm(
    *,
    runtime: APXRuntime,
    name: str,
    pipeline_ids: List[str],
    input_text: Optional[str] = None,
    attest_each: bool = False,
) -> Dict[str, Any]:
    """
    Run pipelines in sequence (fan-in linear swarm v0).
    Each stage may hand off via apxv:handoff inside the pipeline itself;
    this helper is the explicit multi-pipeline parent run.
    """
    if not pipeline_ids:
        raise PipelineSpecError("swarm requires at least one pipeline_id")
    swarm_id = f"swarm-{uuid.uuid4().hex[:12]}"
    parent = {
        "swarm_id": swarm_id,
        "name": name,
        "started_at": _utcnow(),
        "pipeline_ids": list(pipeline_ids),
    }
    stages: List[Dict[str, Any]] = []
    final_status = "succeeded"
    current_input = input_text
    for pid in pipeline_ids:
        stage_result = run_stored_pipeline(
            pid,
            runtime=runtime,
            input_text=current_input,
            attest=attest_each,
            auto_approve=True,
            parent_run=parent,
        )
        stages.append(
            {
                "pipeline_id": pid,
                "final_status": stage_result.get("final_status"),
                "artifact_hash": stage_result.get("artifact_hash"),
                "error": stage_result.get("error"),
                "run_trace": stage_result.get("run_trace"),
            }
        )
        if stage_result.get("final_status") not in ("succeeded",):
            final_status = stage_result.get("final_status") or "failed"
            break
        # Optional: pass redacted text forward if available
        ar = stage_result.get("attested_result") or {}
        redacted = (
            (ar.get("proposed_artifact") or {}).get("output") or {}
        ).get("redacted_text")
        if redacted:
            current_input = redacted

    record = {
        "swarm_id": swarm_id,
        "name": name,
        "final_status": final_status,
        "started_at": parent["started_at"],
        "finished_at": _utcnow(),
        "stages": stages,
        "pipeline_ids": pipeline_ids,
    }
    out = swarms_dir(runtime.base_path) / f"{swarm_id}.json"
    out.write_text(json.dumps(record, indent=2), encoding="utf-8")
    runtime.system_audit.log_event(
        event_type="swarm_run_completed",
        data={
            "swarm_id": swarm_id,
            "final_status": final_status,
            "stages": len(stages),
        },
    )
    return record


def list_swarms(base_path: Path) -> List[Dict[str, Any]]:
    root = swarms_dir(base_path)
    items = []
    for path in sorted(root.glob("swarm-*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            items.append(
                {
                    "swarm_id": data.get("swarm_id"),
                    "name": data.get("name"),
                    "final_status": data.get("final_status"),
                    "started_at": data.get("started_at"),
                    "stage_count": len(data.get("stages") or []),
                }
            )
        except Exception:
            continue
    return items


def get_swarm(base_path: Path, swarm_id: str) -> Optional[Dict[str, Any]]:
    path = swarms_dir(base_path) / f"{swarm_id}.json"
    if not path.is_file():
        # allow bare id without prefix file name mismatch
        for p in swarms_dir(base_path).glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if data.get("swarm_id") == swarm_id:
                    return data
            except Exception:
                continue
        return None
    return json.loads(path.read_text(encoding="utf-8"))
