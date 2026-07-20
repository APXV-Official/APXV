"""
APXV pipeline storage under managed/pipelines/.

YAML preferred; JSON accepted. Round-trip via pipeline_spec.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .pipeline_spec import (
    PipelineSpecError,
    dump_pipeline,
    load_pipeline_file,
    normalize_document,
    validate_pipeline_document,
)

PIPELINES_REL = Path("managed") / "pipelines"


class PipelineStoreError(Exception):
    """Pipeline storage or lookup failure."""


def pipelines_dir(base_path: Path) -> Path:
    return Path(base_path) / PIPELINES_REL


def ensure_pipelines_dir(base_path: Path) -> Path:
    path = pipelines_dir(base_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _candidate_paths(base_path: Path, pipeline_id: str) -> List[Path]:
    root = pipelines_dir(base_path)
    return [
        root / f"{pipeline_id}.yaml",
        root / f"{pipeline_id}.yml",
        root / f"{pipeline_id}.json",
    ]


def find_pipeline_path(base_path: Path, pipeline_id: str) -> Optional[Path]:
    for path in _candidate_paths(base_path, pipeline_id):
        if path.is_file():
            return path
    return None


def list_pipelines(base_path: Path) -> List[Dict[str, Any]]:
    root = pipelines_dir(base_path)
    if not root.is_dir():
        return []
    seen = set()
    items: List[Dict[str, Any]] = []
    for path in sorted(root.glob("*")):
        if path.suffix.lower() not in (".yaml", ".yml", ".json"):
            continue
        try:
            raw = load_pipeline_file(path)
            result = validate_pipeline_document(raw)
            if not result.ok or result.document is None:
                items.append(
                    {
                        "id": path.stem,
                        "path": str(path.relative_to(base_path)) if path.is_relative_to(base_path) else str(path),
                        "valid": False,
                        "errors": result.errors,
                    }
                )
                continue
            doc = result.document
            pid = doc["id"]
            if pid in seen:
                continue
            seen.add(pid)
            items.append(
                {
                    "id": pid,
                    "name": doc.get("name"),
                    "version": doc.get("version"),
                    "description": doc.get("description"),
                    "step_count": len(doc.get("steps", [])),
                    "path": str(path.relative_to(base_path)) if _is_relative(path, base_path) else str(path),
                    "valid": True,
                }
            )
        except Exception as exc:
            items.append(
                {
                    "id": path.stem,
                    "path": str(path),
                    "valid": False,
                    "errors": [str(exc)],
                }
            )
    return items


def _is_relative(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def load_pipeline(base_path: Path, pipeline_id: str) -> Dict[str, Any]:
    path = find_pipeline_path(base_path, pipeline_id)
    if path is None:
        # allow absolute / relative file path as id when it exists
        candidate = Path(pipeline_id)
        if candidate.is_file():
            path = candidate
        else:
            raise PipelineStoreError(f"pipeline not found: {pipeline_id}")
    raw = load_pipeline_file(path)
    result = validate_pipeline_document(raw)
    return result.raise_if_invalid()


def save_pipeline(
    base_path: Path,
    document: Dict[str, Any],
    *,
    fmt: str = "yaml",
    overwrite: bool = True,
) -> Path:
    result = validate_pipeline_document(document)
    doc = result.raise_if_invalid()
    ensure_pipelines_dir(base_path)
    ext = "json" if fmt.lower() == "json" else "yaml"
    path = pipelines_dir(base_path) / f"{doc['id']}.{ext}"
    if path.exists() and not overwrite:
        raise PipelineStoreError(f"pipeline already exists: {path}")
    # remove other format siblings to avoid dual identity
    for other in _candidate_paths(base_path, doc["id"]):
        if other != path and other.is_file():
            other.unlink()
    path.write_text(dump_pipeline(doc, fmt=ext), encoding="utf-8")
    return path


def delete_pipeline(base_path: Path, pipeline_id: str) -> bool:
    path = find_pipeline_path(base_path, pipeline_id)
    if path is None:
        return False
    path.unlink()
    return True


def import_pipeline_text(
    base_path: Path,
    text: str,
    *,
    fmt: str = "auto",
    overwrite: bool = True,
) -> Dict[str, Any]:
    from .pipeline_spec import load_pipeline_text

    raw = load_pipeline_text(text, fmt=fmt)
    result = validate_pipeline_document(raw)
    doc = result.raise_if_invalid()
    path = save_pipeline(base_path, doc, fmt="yaml" if fmt != "json" else "json", overwrite=overwrite)
    return {"document": doc, "path": str(path)}


def export_pipeline(base_path: Path, pipeline_id: str, *, fmt: str = "yaml") -> str:
    doc = load_pipeline(base_path, pipeline_id)
    return dump_pipeline(doc, fmt=fmt)
