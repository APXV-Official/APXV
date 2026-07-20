"""Workshop v1.7–v1.8 depth: HITL, branches, catalog, swarm, pack_profile."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.catalog_quality import lint_catalog, lint_pipeline_file
from agents.pipeline_runner import run_pipeline_document, resume_pipeline_approval
from agents.pipeline_spec import load_pipeline_file, validate_pipeline_document
from agents.pipeline_store import save_pipeline
from agents.runtime import APXVRuntime
from agents.swarm import run_swarm
from tests.helpers import seed_governance_libraries, seed_test_instance

SAMPLE = (
    "Contact John at john.doe@example.com or call (555) 123-4567. "
    "SSN: 123-45-6789. Card: 4111 1111 1111 1111."
)


@pytest.fixture
def runtime(tmp_path):
    seed_test_instance(tmp_path)
    seed_governance_libraries(tmp_path)
    return APXVRuntime(tmp_path)


def test_hitl_pauses_and_resume_completes(runtime):
    path = ROOT / "examples" / "pipelines" / "apxv-pipeline-with-approval.yaml"
    doc = load_pipeline_file(path)
    result = run_pipeline_document(doc, runtime=runtime, input_text=SAMPLE)
    assert result["final_status"] == "awaiting_approval"
    assert result["pause"]["step_id"] == "approve"
    resumed = resume_pipeline_approval(
        runtime=runtime,
        resume_state=result["pause"]["resume_state"],
        approved=True,
    )
    assert resumed["final_status"] == "succeeded"
    statuses = [s["status"] for s in resumed["run_trace"]["steps"] if s["step_id"] == "approve"]
    assert "succeeded" in statuses


def test_hitl_reject(runtime):
    path = ROOT / "examples" / "pipelines" / "apxv-pipeline-with-approval.yaml"
    doc = load_pipeline_file(path)
    result = run_pipeline_document(doc, runtime=runtime, input_text=SAMPLE)
    resumed = resume_pipeline_approval(
        runtime=runtime,
        resume_state=result["pause"]["resume_state"],
        approved=False,
        note="reject test",
    )
    assert resumed["final_status"] == "failed"


def test_branch_next_on_success_skips_optional(runtime):
    path = ROOT / "examples" / "pipelines" / "apxv-pipeline-branch-demo.yaml"
    doc = load_pipeline_file(path)
    result = run_pipeline_document(doc, runtime=runtime, input_text=SAMPLE)
    assert result["final_status"] == "succeeded"
    by_id = {s["step_id"]: s for s in result["run_trace"]["steps"]}
    # optional_llm should not have succeeded as a real run (skipped or never active)
    if "optional_llm" in by_id:
        assert by_id["optional_llm"]["status"] in ("skipped",)
    assert by_id["redact"]["status"] == "succeeded"
    assert by_id["decide"]["status"] == "succeeded"


def test_pack_profile_restores_governance(runtime):
    before = (runtime.base_path / "managed" / "rules" / "rule1.md").read_text(
        encoding="utf-8"
    )
    doc = {
        "apiVersion": "apxv.pipeline/v0.1",
        "kind": "Pipeline",
        "id": "apxv-pipeline-profile-demo",
        "name": "Profile demo",
        "version": "0.1.0",
        "steps": [
            {
                "id": "redact",
                "name": "Redact under reference profile",
                "uses": "agent:APXV-AGENT-001",
                "pack_profile": "apxv-pack-reference-redaction",
            }
        ],
    }
    result = run_pipeline_document(doc, runtime=runtime, input_text=SAMPLE)
    assert result["final_status"] == "succeeded"
    after = (runtime.base_path / "managed" / "rules" / "rule1.md").read_text(
        encoding="utf-8"
    )
    assert after == before


def test_catalog_lint_ok(runtime):
    report = lint_catalog(runtime.base_path)
    assert "packs" in report
    assert "tiers" in report
    # examples from package root may lint via resolve_apxv_root
    ex = ROOT / "examples" / "pipelines" / "apxv-pipeline-reference-linear.yaml"
    pr = lint_pipeline_file(ex)
    assert pr["ok"], pr["errors"]


def test_swarm_v0_sequential(runtime):
    for name in (
        "apxv-pipeline-swarm-stage-a.yaml",
        "apxv-pipeline-swarm-stage-b.yaml",
    ):
        path = ROOT / "examples" / "pipelines" / name
        doc = load_pipeline_file(path)
        save_pipeline(runtime.base_path, doc, fmt="yaml")
    record = run_swarm(
        runtime=runtime,
        name="test-swarm",
        pipeline_ids=[
            "apxv-pipeline-swarm-stage-a",
            "apxv-pipeline-swarm-stage-b",
        ],
        input_text=SAMPLE,
    )
    assert record["final_status"] == "succeeded"
    assert len(record["stages"]) == 2
    assert record["swarm_id"].startswith("swarm-")


def test_example_depth_yamls_validate():
    for path in (ROOT / "examples" / "pipelines").glob("*.yaml"):
        raw = load_pipeline_file(path)
        result = validate_pipeline_document(raw)
        assert result.ok, f"{path.name}: {result.errors}"


def test_handoff_requires_target_message(runtime):
    doc = {
        "apiVersion": "apxv.pipeline/v0.1",
        "kind": "Pipeline",
        "id": "apxv-pipeline-handoff-empty",
        "name": "Handoff empty",
        "version": "0.1.0",
        "steps": [
            {"id": "h", "name": "Handoff", "uses": "apxv:handoff"},
        ],
    }
    result = run_pipeline_document(doc, runtime=runtime, input_text=SAMPLE)
    assert result["final_status"] == "failed"
    assert "Handoff has no target" in (result.get("error") or "")


def test_freeform_edges_order(runtime):
    """Run order follows wires, not array order."""
    doc = {
        "apiVersion": "apxv.pipeline/v0.1",
        "kind": "Pipeline",
        "id": "apxv-pipeline-freeform-wires",
        "name": "Freeform wires",
        "version": "0.1.0",
        "steps": [
            {
                "id": "decide",
                "name": "Third in array, second in graph",
                "uses": "agent:APXV-AGENT-003",
            },
            {
                "id": "redact",
                "name": "First run",
                "uses": "agent:APXV-AGENT-001",
            },
            {
                "id": "orchestrate",
                "name": "Middle",
                "uses": "agent:APXV-AGENT-002",
            },
        ],
        "edges": [
            {"from": "redact", "to": "orchestrate", "kind": "success"},
            {"from": "orchestrate", "to": "decide", "kind": "success"},
        ],
    }
    result = run_pipeline_document(doc, runtime=runtime, input_text=SAMPLE)
    assert result["final_status"] == "succeeded"
    # successful steps appear in graph order in trace (before trailing skipped)
    ok_ids = [
        s["step_id"]
        for s in result["run_trace"]["steps"]
        if s["status"] == "succeeded"
    ]
    assert ok_ids == ["redact", "orchestrate", "decide"]


def test_disabled_step_skipped(runtime):
    doc = {
        "apiVersion": "apxv.pipeline/v0.1",
        "kind": "Pipeline",
        "id": "apxv-pipeline-toggle-demo",
        "name": "Toggle demo",
        "version": "0.1.0",
        "steps": [
            {
                "id": "redact",
                "name": "Redact",
                "uses": "agent:APXV-AGENT-001",
                "enabled": True,
            },
            {
                "id": "skip_me",
                "name": "Would be orchestrator",
                "uses": "agent:APXV-AGENT-002",
                "enabled": False,
            },
            {
                "id": "orchestrate",
                "name": "Orchestrate",
                "uses": "agent:APXV-AGENT-002",
                "enabled": True,
            },
            {
                "id": "decide",
                "name": "Decide",
                "uses": "agent:APXV-AGENT-003",
            },
        ],
    }
    result = run_pipeline_document(doc, runtime=runtime, input_text=SAMPLE)
    assert result["final_status"] == "succeeded"
    by_id = {s["step_id"]: s for s in result["run_trace"]["steps"]}
    assert by_id["skip_me"]["status"] == "skipped"
    assert by_id["redact"]["status"] == "succeeded"
