"""Custom agents for apxv-pack-test-ui — Test UI Pack."""

from __future__ import annotations

from typing import Optional

from agents.agent1 import RuleGovernedRedactor
from agents.agent2 import WorkflowOrchestrator
from agents.agent3 import AttestationCoordinator
from agents.runtime import APXRuntime

SAMPLE_INPUT = (
    "Contact Jane at jane@example.com or call (555) 987-6543. "
    "SSN: 987-65-4321."
)


def run_pack_pipeline(
    input_text: Optional[str] = None,
    runtime: Optional[APXRuntime] = None,
    **_: object,
) -> dict:
    """Entry point used by APXV pipeline service for this pack."""
    runtime = runtime or APXRuntime()
    text = input_text or SAMPLE_INPUT
    redactor = RuleGovernedRedactor(runtime=runtime)
    redactor_output = redactor.process_text(text)
    orchestrator = WorkflowOrchestrator(runtime=runtime)
    workflow_output = orchestrator.execute_workflow(redactor_output=redactor_output)
    coordinator = AttestationCoordinator(runtime=runtime)
    return coordinator.coordinate_attestation(workflow_output=workflow_output)[
        "attested_result"
    ]
