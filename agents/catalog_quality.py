"""
APXV catalog quality — lint and smoke for packs and pipelines (v1.7).

Tiers: Example | Official | Community | Verified
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .pack_catalog import list_packs, pack_dir_for, parse_pack_manifest, resolve_apxv_root
from .pipeline_spec import load_pipeline_file, validate_pipeline_document
from .pipeline_store import list_pipelines
from .runtime import APXRuntime


def lint_pack(base_path: Path, pack_id: str) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    pack_dir = pack_dir_for(base_path, pack_id)
    if not pack_dir:
        return {"id": pack_id, "ok": False, "errors": ["pack not found"], "tier": None}
    try:
        manifest = parse_pack_manifest(pack_dir)
    except Exception as exc:
        return {"id": pack_id, "ok": False, "errors": [str(exc)], "tier": None}
    if not (pack_dir / "pack.yaml").is_file():
        errors.append("missing pack.yaml")
    if not (pack_dir / "README.md").is_file():
        warnings.append("missing README.md")
    if not (pack_dir / "ACCEPTANCE.md").is_file():
        warnings.append("missing ACCEPTANCE.md (required for Official tier)")
    agents_dir = pack_dir / "agents"
    if not agents_dir.is_dir():
        errors.append("missing agents/")
    gov = manifest.get("governance") or {}
    if not any(gov.get(k) for k in ("rules", "workflows", "knowledge")):
        warnings.append("no governance files declared")
    tier = "Official" if pack_id.startswith("apxv-pack-") and not errors else "Community"
    if pack_id in (
        "apxv-pack-reference-redaction",
        "apxv-pack-document-processing",
        "apxv-pack-ai-governance",
    ):
        tier = "Official" if not errors else "Example"
    return {
        "id": pack_id,
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "tier": tier,
        "name": manifest.get("name") or pack_id,
    }


def lint_pipeline_file(path: Path) -> Dict[str, Any]:
    try:
        raw = load_pipeline_file(path)
        result = validate_pipeline_document(raw)
        return {
            "path": str(path),
            "id": (result.document or {}).get("id") or path.stem,
            "ok": result.ok,
            "errors": result.errors,
            "warnings": result.warnings,
            "tier": "Example",
        }
    except Exception as exc:
        return {
            "path": str(path),
            "id": path.stem,
            "ok": False,
            "errors": [str(exc)],
            "warnings": [],
            "tier": None,
        }


def lint_catalog(base_path: Path) -> Dict[str, Any]:
    root = resolve_apxv_root(base_path)
    packs = list_packs(base_path)
    pack_reports = [lint_pack(base_path, p["id"]) for p in packs]
    pipeline_reports: List[Dict[str, Any]] = []
    examples = root / "examples" / "pipelines"
    if examples.is_dir():
        for path in sorted(examples.glob("*.yaml")) + sorted(examples.glob("*.json")):
            pipeline_reports.append(lint_pipeline_file(path))
    for item in list_pipelines(base_path):
        if item.get("path"):
            p = base_path / item["path"]
            if p.is_file():
                pipeline_reports.append(lint_pipeline_file(p))
    ok = all(r["ok"] for r in pack_reports) and all(
        r["ok"] for r in pipeline_reports if r.get("ok") is not None
    )
    return {
        "ok": ok,
        "packs": pack_reports,
        "pipelines": pipeline_reports,
        "tiers": ["Example", "Official", "Community", "Verified"],
    }


def smoke_pipeline(base_path: Path, pipeline_id: str) -> Dict[str, Any]:
    """Run a stored/example pipeline without attest (catalog smoke)."""
    from .pipeline_runner import run_pipeline_document, run_stored_pipeline
    from .pipeline_store import find_pipeline_path, load_pipeline

    runtime = APXRuntime(base_path)
    try:
        if find_pipeline_path(base_path, pipeline_id):
            result = run_stored_pipeline(
                pipeline_id, runtime=runtime, auto_approve=True
            )
        else:
            root = resolve_apxv_root(base_path)
            for path in (root / "examples" / "pipelines").glob("*"):
                if path.stem == pipeline_id or path.name.startswith(pipeline_id):
                    raw = load_pipeline_file(path)
                    result = run_pipeline_document(
                        raw, runtime=runtime, auto_approve=True
                    )
                    break
            else:
                return {"ok": False, "error": f"pipeline not found: {pipeline_id}"}
        ok = result.get("final_status") in ("succeeded", "awaiting_approval")
        return {
            "ok": ok,
            "pipeline_id": result.get("pipeline_id"),
            "final_status": result.get("final_status"),
            "error": result.get("error"),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
