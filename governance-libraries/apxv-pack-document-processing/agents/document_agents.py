"""Document Processing Pack — batch ingest, manifest, and pipeline chaining."""

from __future__ import annotations

import hashlib
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agents.agent1 import RuleGovernedRedactor
from agents.agent2 import WorkflowOrchestrator
from agents.agent3 import AttestationCoordinator
from agents.zk.compliance_policy import DEFAULT_POLICY_BATCH

if TYPE_CHECKING:
    from agents.runtime import APXRuntime

PACK_AGENT_IDS = (
    "APX-AGENT-001",
    "APX-AGENT-002",
    "APX-AGENT-003",
)

SUPPORTED_SUFFIXES = frozenset({".txt", ".json"})
_JSON_TEXT_KEYS = ("content", "text", "body", "message", "document")


def extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8")
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict):
            for key in _JSON_TEXT_KEYS:
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))
    raise ValueError(f"Unsupported batch file type: {path.suffix}")


def discover_batch_files(batch_dir: Path) -> List[Path]:
    if not batch_dir.is_dir():
        raise FileNotFoundError(f"Batch directory not found: {batch_dir}")

    files = [
        path
        for path in sorted(batch_dir.iterdir())
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    ]
    if not files:
        raise ValueError(f"No .txt or .json files found in {batch_dir}")
    return files


def build_batch_manifest(
    file_entries: List[Dict[str, Any]],
    *,
    batch_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "batch_id": batch_id or str(uuid.uuid4()),
        "file_count": len(file_entries),
        "compliance_policy_id": DEFAULT_POLICY_BATCH,
        "files": [
            {
                "path": entry["relative_path"],
                "original_hash": entry["input_hash"],
                "redacted_hash": entry["redacted_hash"],
                "entity_count": entry["entity_count"],
                "total_redactions": entry["total_redactions"],
            }
            for entry in file_entries
        ],
    }


def merge_batch_redactor_output(
    file_entries: List[Dict[str, Any]],
    *,
    template: Dict[str, Any],
) -> Dict[str, Any]:
    combined_original = "\n---\n".join(entry["original_text"] for entry in file_entries)
    combined_redacted = "\n---\n".join(entry["redacted_text"] for entry in file_entries)

    entities: List[Dict[str, Any]] = []
    redactions_applied: List[Dict[str, Any]] = []
    total_redactions = 0

    for entry in file_entries:
        total_redactions += entry["total_redactions"]
        for item in entry.get("redactions_applied", []):
            tagged = dict(item)
            tagged["source_file"] = entry["relative_path"]
            redactions_applied.append(tagged)
        for entity in entry.get("entities", []):
            tagged = dict(entity)
            tagged["source_file"] = entry["relative_path"]
            entities.append(tagged)

    merged = dict(template)
    merged.update(
        {
            "input_hash": hashlib.sha256(combined_original.encode()).hexdigest(),
            "redacted_text": combined_redacted,
            "redactions_applied": redactions_applied,
            "total_redactions": total_redactions,
            "entities": entities,
            "entity_count": len(entities),
            "batch_file_count": len(file_entries),
        }
    )
    return merged


def process_batch_directory(
    batch_dir: Path,
    *,
    runtime: Optional["APXRuntime"] = None,
    batch_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Redact each batch file, build manifest, orchestrate, and attest."""
    runtime = runtime or __import__("agents.runtime", fromlist=["APXRuntime"]).APXRuntime()
    batch_dir = batch_dir.resolve()

    redactor = RuleGovernedRedactor(runtime=runtime)
    file_entries: List[Dict[str, Any]] = []

    for path in discover_batch_files(batch_dir):
        original_text = extract_text_from_file(path)
        result = redactor.process_text(original_text)
        file_entries.append(
            {
                "relative_path": path.name,
                "original_text": original_text,
                "input_hash": result["input_hash"],
                "redacted_text": result["redacted_text"],
                "redactions_applied": result.get("redactions_applied", []),
                "total_redactions": result.get("total_redactions", 0),
                "entities": result.get("entities", []),
                "entity_count": result.get("entity_count", 0),
                "template": result,
            }
        )

    if not file_entries:
        raise ValueError("Batch processing produced no file entries")

    for entry in file_entries:
        entry["redacted_hash"] = hashlib.sha256(entry["redacted_text"].encode()).hexdigest()

    manifest = build_batch_manifest(file_entries, batch_id=batch_id)
    merged_output = merge_batch_redactor_output(
        file_entries,
        template=file_entries[0]["template"],
    )

    orchestrator = WorkflowOrchestrator(runtime=runtime)
    workflow_output = orchestrator.execute_workflow(redactor_output=merged_output)

    proposed = workflow_output["proposed_artifact"]
    proposed["artifact_type"] = "batch_redaction_result"
    proposed["output"]["batch_manifest"] = manifest
    proposed["output"]["compliance_policy_id"] = DEFAULT_POLICY_BATCH
    proposed["output"]["batch_file_count"] = manifest["file_count"]
    proposed["governance_notes"] = (
        "Batch document processing per APX-WF-DOC-001. "
        f"Processed {manifest['file_count']} files with compliance policy id {DEFAULT_POLICY_BATCH}."
    )

    coordinator = AttestationCoordinator(runtime=runtime)
    final_output = coordinator.coordinate_attestation(workflow_output=workflow_output)
    attested = final_output["attested_result"]
    attested["compliance_policy_id"] = DEFAULT_POLICY_BATCH
    return attested


__all__ = [
    "PACK_AGENT_IDS",
    "DEFAULT_POLICY_BATCH",
    "discover_batch_files",
    "extract_text_from_file",
    "build_batch_manifest",
    "process_batch_directory",
    "RuleGovernedRedactor",
    "WorkflowOrchestrator",
    "AttestationCoordinator",
]