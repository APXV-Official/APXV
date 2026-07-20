"""Phase 5: Studio create → test → promote (real runtime)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.pipeline_runner import run_pipeline_document
from agents.runtime import APXVRuntime
from agents.studio_service import (
    StudioError,
    list_operator_agents,
    list_promoted_for_workbench,
    load_operator_agent,
    promote_agent,
    promote_pack,
    save_operator_agent,
    save_studio_pack,
    run_operator_agent_test,
    run_studio_pack_test,
)
from tests.helpers import seed_governance_libraries, seed_test_instance


@pytest.fixture
def runtime(tmp_path):
    seed_test_instance(tmp_path)
    seed_governance_libraries(tmp_path)
    return APXVRuntime(tmp_path)


def test_create_test_promote_agent(runtime):
    agent = save_operator_agent(
        runtime,
        agent_id="APXV-AGENT-OP-DEMO",
        name="Demo Operator Agent",
        description="Studio test agent",
        agent_type="deterministic",
        instruction_md="# Instruction\n\nEcho input under policy.\n",
        knowledge_md="# Knowledge\n\nDemo knowledge.\n",
    )
    assert agent["id"] == "APXV-AGENT-OP-DEMO"
    assert load_operator_agent(runtime.base_path, "APXV-AGENT-OP-DEMO")

    with pytest.raises(StudioError):
        promote_agent(runtime, "APXV-AGENT-OP-DEMO", force=False)

    tested = run_operator_agent_test(runtime, "APXV-AGENT-OP-DEMO")
    assert tested["ok"] is True
    assert tested["result"]["final_status"] == "succeeded"
    assert tested["result"]["run_trace"]["steps"]

    promoted = promote_agent(runtime, "APXV-AGENT-OP-DEMO")
    assert promoted["promoted"] is True
    assert promoted["maturity"] == "ready"

    shelf = list_promoted_for_workbench(runtime.base_path)
    assert any(a["id"] == "APXV-AGENT-OP-DEMO" for a in shelf["agents"])

    # Workbench-style pipeline run
    doc = {
        "apiVersion": "apxv.pipeline/v0.1",
        "kind": "Pipeline",
        "id": "apxv-pipeline-use-op-agent",
        "name": "Use OP agent",
        "version": "0.1.0",
        "steps": [
            {
                "id": "op",
                "name": "Operator agent",
                "uses": "agent:APXV-AGENT-OP-DEMO",
            }
        ],
    }
    result = run_pipeline_document(
        doc, runtime=runtime, input_text="hello studio"
    )
    assert result["final_status"] == "succeeded"


def test_create_test_promote_pack(runtime):
    pack = save_studio_pack(
        runtime,
        pack_id="apxv-pack-studio-demo",
        name="Studio Demo Pack",
        description="Created in Studio",
        rules_md="# Rules\n\nDo not leak secrets.\n",
        workflow_md="# Workflow\n\n1. Ingest\n2. Process\n",
        knowledge_md="# Knowledge\n\nDemo pack knowledge.\n",
        agent_ids=["APXV-AGENT-001"],
    )
    assert pack["id"] == "apxv-pack-studio-demo"
    assert "Do not leak" in pack["rules_md"]

    with pytest.raises(StudioError):
        promote_pack(runtime, "apxv-pack-studio-demo", force=False)

    tested = run_studio_pack_test(runtime, "apxv-pack-studio-demo")
    assert tested["ok"] is True

    promoted = promote_pack(runtime, "apxv-pack-studio-demo")
    assert promoted["promoted"] is True

    shelf = list_promoted_for_workbench(runtime.base_path)
    assert any(p["id"] == "apxv-pack-studio-demo" for p in shelf["packs"])


def test_list_operator_agents_empty(runtime):
    assert list_operator_agents(runtime.base_path) == []


def test_bounded_loop_step(runtime):
    from agents.pipeline_runner import run_pipeline_document

    doc = {
        "apiVersion": "apxv.pipeline/v0.1",
        "kind": "Pipeline",
        "id": "apxv-pipeline-loop-demo",
        "name": "Loop demo",
        "version": "0.1.0",
        "steps": [
            {
                "id": "loop",
                "name": "Bounded loop",
                "uses": "apxv:loop",
                "config": {"max_iterations": 2},
            },
            {
                "id": "work",
                "name": "Work",
                "uses": "agent:APXV-AGENT-001",
            },
        ],
        "edges": [
            {"from": "loop", "to": "work", "kind": "success"},
        ],
    }
    result = run_pipeline_document(
        doc, runtime=runtime, input_text="loop test email a@b.com"
    )
    assert result["final_status"] == "succeeded"
    loop_steps = [
        s for s in result["run_trace"]["steps"] if s["step_id"] == "loop"
    ]
    assert loop_steps
    assert loop_steps[0]["status"] == "succeeded"
