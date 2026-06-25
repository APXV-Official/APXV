"""Reference Redaction Pack — runnable pipeline demo."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from agents.runtime import APXRuntime


def _load_reference_agents():
    mod_path = Path(__file__).resolve().parents[1] / "agents" / "reference_agents.py"
    spec = importlib.util.spec_from_file_location("pack_reference_agents", mod_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load pack agents from {mod_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_ref = _load_reference_agents()
RuleGovernedRedactor = _ref.RuleGovernedRedactor
WorkflowOrchestrator = _ref.WorkflowOrchestrator
AttestationCoordinator = _ref.AttestationCoordinator

SAMPLE_INPUT = (
    "Contact John at john.doe@example.com or call (555) 123-4567. "
    "SSN: 123-45-6789. Card: 4111 1111 1111 1111."
)


def run_pack_pipeline(input_text: str = SAMPLE_INPUT, runtime: APXRuntime | None = None) -> dict:
    runtime = runtime or APXRuntime()
    redactor = RuleGovernedRedactor(runtime=runtime)
    redactor_output = redactor.process_text(input_text)

    orchestrator = WorkflowOrchestrator(runtime=runtime)
    workflow_output = orchestrator.execute_workflow(redactor_output=redactor_output)

    coordinator = AttestationCoordinator(runtime=runtime)
    final_output = coordinator.coordinate_attestation(workflow_output=workflow_output)
    return final_output["attested_result"]


def main() -> int:
    result = run_pack_pipeline()
    status = result.get("final_status")
    redactions = result.get("proposed_artifact", {}).get("output", {}).get("total_redactions")
    print(f"Pack demo complete: final_status={status}, total_redactions={redactions}")
    if status != "ATTESTED":
        return 1
    if redactions != 4:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())