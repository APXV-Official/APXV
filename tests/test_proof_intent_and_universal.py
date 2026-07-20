"""P2 intent compiler + P3 universal circuit wiring (real where keys exist)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.proof_intent import compile_intent_deterministic
from agents.proof_studio import (
    CIRCUIT_BINDING_UNIVERSAL,
    apply_proof_profile_to_result,
    export_proof_claim_bundle,
    save_profile_from_intent,
    save_proof_profile,
    universal_keys_available,
)
from agents.pipeline_runner import run_pipeline_document
from agents.runtime import APXVRuntime
from agents.zk.universal_bridge import build_witness_from_claim, keys_available
from tests.helpers import seed_governance_libraries, seed_test_instance


@pytest.fixture
def runtime(tmp_path):
    seed_test_instance(tmp_path)
    seed_governance_libraries(tmp_path)
    return APXVRuntime(tmp_path)


def test_intent_compiler_maps_categories_and_redaction():
    out = compile_intent_deterministic(
        "Prove that email and SSN were redacted and rules were bound, "
        "and the pipeline was attested.",
        proof_id="APXV-PROOF-INTENT-1",
        prefer_universal=False,
    )
    ids = {p["id"] for p in out["predicates"]}
    assert "REDACTION_NONEMPTY" in ids
    assert "CATEGORY_INCLUDES" in ids
    assert "RULE_BOUND" in ids
    assert "ATTESTED_STATUS" in ids
    cats = []
    for p in out["predicates"]:
        if p["id"] == "CATEGORY_INCLUDES":
            cats = p["params"]["categories"]
    assert "email" in cats
    assert "ssn" in cats
    assert out["proof_spec"]["claim_english"]


def test_intent_entity_count_threshold():
    out = compile_intent_deterministic(
        "Prove at least 3 entities were found",
        prefer_universal=False,
    )
    ent = next(p for p in out["predicates"] if p["id"] == "ENTITY_COUNT_GTE")
    assert ent["params"]["n"] == 3


def test_save_from_intent(runtime):
    profile = save_profile_from_intent(
        runtime,
        intent_md="Prove redaction occurred and governance approved the run.",
        proof_id="APXV-PROOF-INTENT-SAVE",
        name="Intent save",
        prefer_universal=False,
    )
    assert profile["id"] == "APXV-PROOF-INTENT-SAVE"
    assert profile.get("compile", {}).get("source") == "deterministic"
    assert profile["predicates"]


def test_export_claim_bundle_shape(runtime):
    claim = {
        "ok": True,
        "proof_profile_id": "APXV-PROOF-X",
        "claim_english": "This run proves: redaction.",
        "predicates": [{"id": "REDACTION_NONEMPTY", "ok": True, "detail": {"total_redactions": 2}}],
        "failed_predicates": [],
        "evaluated_at": "2026-01-01T00:00:00Z",
    }
    bundle = export_proof_claim_bundle(
        runtime.base_path, proof_profile_id="APXV-PROOF-X", claim=claim
    )
    assert bundle["export_type"] == "apxv.proof_claim_bundle"
    assert bundle["claim"]["ok"] is True
    assert "never_includes" in bundle["disclosure"]


def test_witness_builder_sets_mask_bits():
    claim = {
        "ok": True,
        "predicates": [
            {"id": "REDACTION_NONEMPTY", "ok": True, "params": {}, "detail": {"total_redactions": 2}},
            {"id": "ENTITY_COUNT_GTE", "ok": True, "params": {"n": 1}, "detail": {"entity_count": 2}},
            {"id": "RULE_BOUND", "ok": True, "params": {}, "detail": {}},
        ],
    }
    attested = {
        "proposed_artifact": {
            "input": {"original_hash": "aa", "post_redaction_hash": "bb"},
            "output": {"total_redactions": 2, "entities": [{}, {}]},
        },
        "attestation_id": "att-1",
    }
    w = build_witness_from_claim(claim, attested)
    assert int(w["predicate_mask"]) & 1  # redaction
    assert int(w["predicate_mask"]) & 2  # entity gte
    assert int(w["flags"]) & 1
    assert int(w["entity_count"]) == 2


@pytest.mark.skipif(
    not keys_available(ROOT),
    reason="universal-predicate-v1 keys not generated yet",
)
def test_universal_prove_on_real_pipeline(runtime):
    """Full path: profile → run → claim → real Groth16 universal proof."""
    # Copy keys into tmp runtime? Bridge uses ROOT for rust keys via base_path
    # pipeline uses runtime.base_path; attach_universal uses base_path from apply
    # which is runtime.base_path — keys looked up relative to that.
    # Point runtime base at ROOT for keys OR patch keys path.
    # Simplest: use real ROOT as base for this integration test.
    rt = APXVRuntime(ROOT)
    save_proof_profile(
        rt,
        proof_id="APXV-PROOF-UNI-LIVE",
        name="Universal live",
        predicates=[
            {"id": "REDACTION_NONEMPTY"},
            {"id": "ENTITY_COUNT_GTE", "params": {"n": 1}},
            {"id": "RULE_BOUND"},
            {"id": "PIPELINE_CHAIN"},
            {"id": "ATTESTED_STATUS"},
            {"id": "GOVERNANCE_APPROVED"},
        ],
        circuit_binding=CIRCUIT_BINDING_UNIVERSAL
        if universal_keys_available(ROOT)
        else "existing-dual-track",
        require_attest=False,
    )
    doc = {
        "apiVersion": "apxv.pipeline/v0.1",
        "kind": "Pipeline",
        "id": "apxv-pipeline-uni-live",
        "name": "Uni live",
        "version": "0.1.0",
        "defaults": {
            "proof_profile": "APXV-PROOF-UNI-LIVE",
            "attest": False,
        },
        "steps": [
            {"id": "redact", "name": "R", "uses": "agent:APXV-AGENT-001"},
            {"id": "orch", "name": "O", "uses": "agent:APXV-AGENT-002"},
            {"id": "decide", "name": "D", "uses": "agent:APXV-AGENT-003"},
        ],
    }
    result = run_pipeline_document(
        doc,
        runtime=rt,
        input_text=(
            "Contact Pat at pat@example.com phone 555-111-2222 SSN 999-88-7777."
        ),
        proof_profile_id="APXV-PROOF-UNI-LIVE",
    )
    assert result["final_status"] == "succeeded", result.get("error")
    claim = result.get("proof_claim") or {}
    assert claim.get("ok") is True, claim
    up = result.get("universal_predicate_proof") or claim.get("universal_predicate_proof")
    assert up, "expected universal_predicate_proof on result"
    assert up.get("verification_result") is True or up.get("independent_verify") is True
    assert up.get("vk_hash")
