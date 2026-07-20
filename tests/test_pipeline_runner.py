"""Tests for Workshop pipeline store, runner, and capability fail-closed."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.pipeline_runner import run_pipeline_document, run_stored_pipeline
from agents.pipeline_spec import validate_pipeline_document
from agents.pipeline_store import export_pipeline, import_pipeline_text, list_pipelines, save_pipeline
from agents.runtime import APXVRuntime
from tests.helpers import seed_test_instance

SAMPLE = (
    "Contact John at john.doe@example.com or call (555) 123-4567. "
    "SSN: 123-45-6789. Card: 4111 1111 1111 1111."
)

LINEAR = {
    "apiVersion": "apxv.pipeline/v0.1",
    "kind": "Pipeline",
    "id": "apxv-pipeline-reference-linear",
    "name": "Reference linear composition",
    "version": "0.1.0",
    "defaults": {"attest": False, "on_step_failure": "stop"},
    "steps": [
        {"id": "redact", "name": "Rule-governed redaction", "uses": "agent:APXV-AGENT-001"},
        {"id": "orchestrate", "name": "Workflow orchestration", "uses": "agent:APXV-AGENT-002"},
        {"id": "decide", "name": "Attestation coordination", "uses": "agent:APXV-AGENT-003"},
    ],
}


@pytest.fixture
def runtime(tmp_path):
    seed_test_instance(tmp_path)
    return APXVRuntime(tmp_path)


def test_run_linear_pipeline_produces_trace(runtime):
    result = run_pipeline_document(LINEAR, runtime=runtime, input_text=SAMPLE)
    assert result["final_status"] == "succeeded"
    assert result["pipeline_id"] == "apxv-pipeline-reference-linear"
    trace = result["run_trace"]
    assert len(trace["steps"]) == 3
    assert all(s["status"] == "succeeded" for s in trace["steps"])
    assert result["governance_decision"] in (
        "APPROVED",
        "APPROVED_WITH_REVIEW_FLAG",
        "APPROVED_NO_CHANGES",
    )
    assert result.get("artifact_hash")
    # Accuracy: step ids match Spec
    assert [s["step_id"] for s in trace["steps"]] == ["redact", "orchestrate", "decide"]


def test_store_export_import_round_trip(runtime):
    save_pipeline(runtime.base_path, LINEAR, fmt="yaml")
    items = list_pipelines(runtime.base_path)
    assert any(i["id"] == "apxv-pipeline-reference-linear" and i.get("valid") for i in items)
    exported = export_pipeline(runtime.base_path, "apxv-pipeline-reference-linear", fmt="yaml")
    # wipe and re-import
    managed = runtime.base_path / "managed" / "pipelines"
    for p in managed.glob("*"):
        p.unlink()
    imported = import_pipeline_text(runtime.base_path, exported, fmt="yaml")
    assert imported["document"]["id"] == "apxv-pipeline-reference-linear"
    result = run_stored_pipeline(
        "apxv-pipeline-reference-linear",
        runtime=runtime,
        input_text=SAMPLE,
    )
    assert result["final_status"] == "succeeded"


def test_json_store_round_trip(runtime):
    save_pipeline(runtime.base_path, LINEAR, fmt="json")
    exported = export_pipeline(runtime.base_path, "apxv-pipeline-reference-linear", fmt="json")
    data = json.loads(exported)
    assert data["id"] == "apxv-pipeline-reference-linear"
    result = validate_pipeline_document(data)
    assert result.ok


def test_capability_deny_fails_step(runtime):
    # Revoke execute_agent for agent 001 by signing empty policy is heavy;
    # instead require a fake extra capability that agents do not have.
    doc = {
        **LINEAR,
        "id": "apxv-pipeline-cap-deny",
        "steps": [
            {
                "id": "redact",
                "name": "Redact",
                "uses": "agent:APXV-AGENT-001",
                "capabilities_required": ["this_capability_does_not_exist"],
            }
        ],
    }
    result = run_pipeline_document(doc, runtime=runtime, input_text=SAMPLE)
    assert result["final_status"] == "failed"
    assert result["run_trace"]["steps"][0]["status"] == "failed"
    assert result["run_trace"]["steps"][0]["error"]


def test_invalid_agent_binding_fails(runtime):
    doc = {
        **LINEAR,
        "id": "apxv-pipeline-bad-agent",
        "steps": [
            {"id": "x", "name": "X", "uses": "agent:APXV-AGENT-DOES-NOT-EXIST"},
        ],
    }
    result = run_pipeline_document(doc, runtime=runtime, input_text=SAMPLE)
    assert result["final_status"] == "failed"


def test_pack_step_pipeline(runtime):
    from tests.helpers import seed_governance_libraries

    seed_governance_libraries(runtime.base_path)
    doc = {
        "apiVersion": "apxv.pipeline/v0.1",
        "kind": "Pipeline",
        "id": "apxv-pipeline-run-reference-pack",
        "name": "Pack entry",
        "version": "0.1.0",
        "steps": [
            {
                "id": "pack_main",
                "name": "Reference pack",
                "uses": "pack:apxv-pack-reference-redaction",
            }
        ],
    }
    result = run_pipeline_document(doc, runtime=runtime, input_text=SAMPLE)
    assert result["final_status"] == "succeeded"
    assert result["run_trace"]["steps"][0]["status"] == "succeeded"
