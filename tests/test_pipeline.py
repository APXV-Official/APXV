"""APX v1 integration tests for the governed agent pipeline."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.agent1 import RuleGovernedRedactor
from agents.agent2 import WorkflowOrchestrator
from agents.agent3 import AttestationCoordinator
from agents.runtime import APXRuntime
from scripts.prepare_proof_inputs import prepare_circuit_inputs
from scripts.verify_attestation import verify_python_attestation


SAMPLE_INPUT = (
    "Contact John at john.doe@example.com or call (555) 123-4567. "
    "SSN: 123-45-6789. Card: 4111 1111 1111 1111."
)


def run_pipeline(input_text: str = SAMPLE_INPUT, runtime: APXRuntime | None = None) -> dict:
    runtime = runtime or APXRuntime()
    redactor = RuleGovernedRedactor(runtime=runtime)
    redactor_output = redactor.process_text(input_text)

    orchestrator = WorkflowOrchestrator(runtime=runtime)
    workflow_output = orchestrator.execute_workflow(redactor_output=redactor_output)

    coordinator = AttestationCoordinator(runtime=runtime)
    final_output = coordinator.coordinate_attestation(workflow_output=workflow_output)
    return final_output["attested_result"]


def test_pipeline_produces_attested_result():
    attested = run_pipeline()
    assert attested["final_status"] == "ATTESTED"
    assert attested["governance_decision"]["decision"] == "APPROVED_WITH_REVIEW_FLAG"
    assert attested["proposed_artifact"]["output"]["total_redactions"] == 4


def test_python_verification_passes():
    attested = run_pipeline()
    report = verify_python_attestation(attested)
    assert report["overall_status"] == "VERIFIED"
    assert all(check["passed"] for check in report["checks"])


def test_prepare_circuit_inputs_uses_proof_chain():
    attested = run_pipeline()
    fake_redaction_proof = {"proof_hex": "abc123proof"}
    inputs = prepare_circuit_inputs(attested, redaction_proof=fake_redaction_proof)

    assert inputs["redaction_proof_inputs"]["redaction_count"] == 4
    assert len(inputs["rule_binding_inputs"]["redaction_proof_hash"]) == 64
    assert inputs["rule_binding_inputs"]["redaction_proof_hash"] != "a" * 64
    assert len(inputs["pipeline_attestation_inputs"]["final_governance_decision"]) == 64


@pytest.mark.skipif(
    not (ROOT / "rust" / "Cargo.toml").exists(),
    reason="Rust toolchain not available in this environment",
)
def test_full_attest_and_verify_real_zk():
    result = subprocess.run(
        [sys.executable, "-m", "scripts.run_apx", "--attest"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stderr[-800:]

    verify = subprocess.run(
        [sys.executable, "-m", "scripts.verify_attestation", "--real-zk"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert verify.returncode == 0, verify.stdout + verify.stderr
    assert "GROTH16 PROOFS INDEPENDENTLY VERIFIED" in verify.stdout

    standalone = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.apx_verify_bundle",
            str(sorted((ROOT / "managed" / "artifacts").glob("attested_result_pipeline_with_zk_*.json"))[-1]),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert standalone.returncode == 0, standalone.stdout + standalone.stderr
    assert "Standalone verification complete" in standalone.stdout