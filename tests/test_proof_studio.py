"""Proof Studio — create, test, promote, attach to pipeline runs."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.pipeline_runner import run_pipeline_document
from agents.pipeline_spec import validate_pipeline_document
from agents.proof_studio import (
    compile_proof_spec,
    evaluate_proof_profile,
    get_proof_profile,
    list_predicate_catalog,
    list_promoted_proofs,
    list_proof_templates,
    promote_proof_profile,
    run_proof_profile_test,
    save_from_template,
    save_proof_profile,
)
from agents.runtime import APXVRuntime
from agents.studio_service import StudioError, list_promoted_for_workbench
from tests.helpers import seed_governance_libraries, seed_test_instance


@pytest.fixture
def runtime(tmp_path):
    seed_test_instance(tmp_path)
    seed_governance_libraries(tmp_path)
    return APXVRuntime(tmp_path)


def test_catalog_and_templates():
    catalog = list_predicate_catalog()
    assert any(p["id"] == "REDACTION_NONEMPTY" for p in catalog)
    templates = list_proof_templates()
    assert any(t["id"] == "APXV-PROOF-REDACTION-CORE" for t in templates)


def test_compile_rejects_unknown_predicate():
    with pytest.raises(StudioError, match="unknown predicate"):
        compile_proof_spec(
            proof_id="APXV-PROOF-BAD",
            name="Bad",
            predicates=[{"id": "NOT_A_REAL_PREDICATE"}],
        )


def test_create_test_promote_proof_profile(runtime):
    profile = save_proof_profile(
        runtime,
        proof_id="APXV-PROOF-CORE-TEST",
        name="Core claim test",
        description="Unit test profile",
        intent_md="# Intent\n\nProve redaction + governance.\n",
        predicates=[
            {"id": "REDACTION_NONEMPTY"},
            {"id": "RULE_BOUND"},
            {"id": "PIPELINE_CHAIN"},
            {"id": "ATTESTED_STATUS"},
            {"id": "GOVERNANCE_APPROVED"},
        ],
        require_attest=False,
    )
    assert profile["id"] == "APXV-PROOF-CORE-TEST"
    assert profile["claim_english"]
    assert (runtime.base_path / "managed/studio/proofs/APXV-PROOF-CORE-TEST/proof-spec.json").exists()

    with pytest.raises(StudioError, match="test has not succeeded"):
        promote_proof_profile(runtime, "APXV-PROOF-CORE-TEST", force=False)

    tested = run_proof_profile_test(runtime, "APXV-PROOF-CORE-TEST")
    assert tested["ok"] is True, tested
    assert tested["proof_claim"]["ok"] is True
    assert tested["last_test"]["final_status"] == "succeeded"

    promoted = promote_proof_profile(runtime, "APXV-PROOF-CORE-TEST")
    assert promoted["promoted"] is True
    assert promoted["maturity"] == "ready"

    shelf = list_promoted_for_workbench(runtime.base_path)
    assert any(p["id"] == "APXV-PROOF-CORE-TEST" for p in shelf.get("proofs") or [])
    assert any(p["id"] == "APXV-PROOF-CORE-TEST" for p in list_promoted_proofs(runtime.base_path))


def test_pipeline_defaults_preserve_proof_profile():
    raw = {
        "apiVersion": "apxv.pipeline/v0.1",
        "kind": "Pipeline",
        "id": "apxv-pipeline-with-proof",
        "name": "With proof",
        "version": "0.1.0",
        "defaults": {
            "attest": False,
            "on_step_failure": "stop",
            "proof_profile": "APXV-PROOF-CORE-TEST",
        },
        "steps": [
            {
                "id": "redact",
                "name": "Redact",
                "uses": "agent:APXV-AGENT-001",
            }
        ],
    }
    result = validate_pipeline_document(raw)
    assert result.ok, result.errors
    assert result.document["defaults"]["proof_profile"] == "APXV-PROOF-CORE-TEST"


def test_pipeline_run_applies_proof_profile(runtime):
    save_proof_profile(
        runtime,
        proof_id="APXV-PROOF-RUN-BIND",
        name="Run bind",
        predicates=[
            {"id": "REDACTION_NONEMPTY"},
            {"id": "ATTESTED_STATUS"},
            {"id": "GOVERNANCE_APPROVED"},
        ],
        require_attest=False,
    )
    # Mark tested so promote path optional — attach works without promote
    doc = {
        "apiVersion": "apxv.pipeline/v0.1",
        "kind": "Pipeline",
        "id": "apxv-pipeline-proof-bind",
        "name": "Proof bind",
        "version": "0.1.0",
        "defaults": {
            "attest": False,
            "proof_profile": "APXV-PROOF-RUN-BIND",
        },
        "steps": [
            {"id": "redact", "name": "Redact", "uses": "agent:APXV-AGENT-001"},
            {"id": "orch", "name": "Orch", "uses": "agent:APXV-AGENT-002"},
            {"id": "decide", "name": "Decide", "uses": "agent:APXV-AGENT-003"},
        ],
    }
    result = run_pipeline_document(
        doc,
        runtime=runtime,
        input_text=(
            "Contact Jane at jane@example.com or call 555-0100. SSN 111-22-3333."
        ),
    )
    assert result["final_status"] == "succeeded", result.get("error")
    assert result.get("proof_profile") == "APXV-PROOF-RUN-BIND"
    claim = result.get("proof_claim") or {}
    assert claim.get("ok") is True, claim
    assert "REDACTION_NONEMPTY" not in (claim.get("failed_predicates") or [])


def test_fail_closed_when_claim_impossible(runtime):
    save_proof_profile(
        runtime,
        proof_id="APXV-PROOF-IMPOSSIBLE",
        name="Impossible",
        predicates=[
            {"id": "ENTITY_COUNT_GTE", "params": {"n": 9999}},
        ],
        fail_closed=True,
        require_attest=False,
    )
    doc = {
        "apiVersion": "apxv.pipeline/v0.1",
        "kind": "Pipeline",
        "id": "apxv-pipeline-proof-fail",
        "name": "Proof fail",
        "version": "0.1.0",
        "defaults": {"proof_profile": "APXV-PROOF-IMPOSSIBLE"},
        "steps": [
            {"id": "redact", "name": "Redact", "uses": "agent:APXV-AGENT-001"},
            {"id": "orch", "name": "Orch", "uses": "agent:APXV-AGENT-002"},
            {"id": "decide", "name": "Decide", "uses": "agent:APXV-AGENT-003"},
        ],
    }
    result = run_pipeline_document(
        doc,
        runtime=runtime,
        input_text="hello with email test@example.com",
    )
    assert result["final_status"] == "failed"
    assert result.get("proof_claim", {}).get("ok") is False
    assert "ENTITY_COUNT_GTE" in (result.get("proof_claim", {}).get("failed_predicates") or [])


def test_template_clone(runtime):
    proof = save_from_template(runtime, "APXV-PROOF-REDACTION-CORE")
    assert proof["id"] == "APXV-PROOF-REDACTION-CORE"
    loaded = get_proof_profile(runtime.base_path, proof["id"])
    assert loaded["predicates"]
