"""
APX v1 — Pipeline Service (quiet execution for local API)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import json

from .runtime import APXRuntime


def run_pipeline_quiet(
    input_text: Optional[str] = None,
    attest: bool = False,
    runtime: Optional[APXRuntime] = None,
) -> Dict[str, Any]:
    """
    Execute the full governed pipeline without CLI output.
    Returns structured result for API/job consumers.
    """
    from agents.agent1 import RuleGovernedRedactor
    from agents.agent2 import WorkflowOrchestrator
    from agents.agent3 import AttestationCoordinator

    if input_text is None:
        input_text = (
            "Contact John at john.doe@example.com or call (555) 123-4567. "
            "SSN: 123-45-6789. Card: 4111 1111 1111 1111."
        )

    runtime = runtime or APXRuntime()
    provider = runtime.provider

    redactor = RuleGovernedRedactor(runtime=runtime)
    redactor_output = redactor.process_text(input_text)

    orchestrator = WorkflowOrchestrator(runtime=runtime)
    workflow_output = orchestrator.execute_workflow(redactor_output=redactor_output)

    coordinator = AttestationCoordinator(runtime=runtime)
    final_output = coordinator.coordinate_attestation(workflow_output=workflow_output)
    attested = final_output["attested_result"]

    write_meta = provider.write_artifact(artifact=attested, name="attested_result_pipeline")

    zk_summary = None
    if attest:
        from scripts.setup_zk import ensure_zk_setup
        from scripts.run_apx import generate_zk_proof

        ensure_zk_setup(base_path=runtime.base_path)
        base = runtime.base_path

        zk_redaction = generate_zk_proof(attested, base, circuit="redaction")
        attested["zk_proof_redaction"] = zk_redaction

        zk_rule = generate_zk_proof(
            attested, base, circuit="rule-binding", redaction_proof=zk_redaction
        )
        attested["zk_proof_rule_binding"] = zk_rule

        zk_pipeline = generate_zk_proof(
            attested, base, circuit="pipeline", redaction_proof=zk_redaction
        )
        attested["zk_proof_pipeline"] = zk_pipeline

        write_meta = provider.write_artifact(
            artifact=attested, name="attested_result_pipeline_with_zk"
        )
        runtime.system_audit.log_event(
            event_type="pipeline_attested_with_zk",
            data={"attestation_id": attested.get("attestation_id"), "via": "api"},
        )
        zk_summary = {
            "redaction": zk_redaction.get("verification_result"),
            "rule_binding": zk_rule.get("verification_result"),
            "pipeline": zk_pipeline.get("verification_result"),
        }

    runtime.system_audit.log_event(
        event_type="pipeline_completed",
        data={
            "attestation_id": attested.get("attestation_id"),
            "artifact_hash": write_meta["hash"],
            "attest": attest,
            "via": "api",
        },
    )

    return {
        "attestation_id": attested.get("attestation_id"),
        "final_status": attested.get("final_status"),
        "governance_decision": attested.get("governance_decision", {}).get("decision"),
        "artifact_hash": write_meta["hash"],
        "artifact_path": write_meta["path"],
        "total_redactions": attested.get("proposed_artifact", {})
        .get("output", {})
        .get("total_redactions"),
        "full_provenance_hash": attested.get("full_provenance_hash"),
        "zk_summary": zk_summary,
        "attested_result": attested,
    }


def execute_job_payload(payload: Dict[str, Any], runtime: Optional[APXRuntime] = None) -> Dict[str, Any]:
    return run_pipeline_quiet(
        input_text=payload.get("input_text"),
        attest=bool(payload.get("attest", False)),
        runtime=runtime,
    )