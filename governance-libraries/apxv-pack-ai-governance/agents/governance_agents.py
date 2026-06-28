"""AI Governance Pack — redaction, governed LLM review, and attestation."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agents.agent1 import RuleGovernedRedactor
from agents.agent2 import WorkflowOrchestrator
from agents.agent3 import AttestationCoordinator
from agents.llm_backend import LLMBackend, SimulatedLLMBackend
from agents.llm_reasoner import LLMReasoner
from agents.zk.compliance_policy import DEFAULT_POLICY_AI_GOVERNANCE

if TYPE_CHECKING:
    from agents.runtime import APXRuntime

PACK_AGENT_IDS = (
    "APX-AGENT-001",
    "APX-AGENT-002",
    "APX-AGENT-003",
    "APX-AGENT-LLM-001",
)

DEFAULT_POLICY_AI = DEFAULT_POLICY_AI_GOVERNANCE

DEFAULT_REVIEW_PROMPT = (
    "Governance review: assess redacted content for release. "
    "Recommend APPROVED, REVIEW_REQUIRED, or REJECTED with brief reasoning."
)

SAMPLE_INPUT = (
    "Contact Jane at jane.smith@example.com or call (555) 987-6543. "
    "SSN: 987-65-4321. Credit application pending review."
)


def run_governed_ai_pipeline(
    input_text: str = SAMPLE_INPUT,
    *,
    runtime: Optional["APXRuntime"] = None,
    prompt: Optional[str] = None,
    backend: Optional[LLMBackend] = None,
) -> Dict[str, Any]:
    """Redact input, run LLMReasoner governance review, orchestrate, and attest."""
    runtime = runtime or __import__("agents.runtime", fromlist=["APXRuntime"]).APXRuntime()

    redactor = RuleGovernedRedactor(runtime=runtime)
    redactor_output = redactor.process_text(input_text)

    llm = LLMReasoner(runtime=runtime, backend=backend or SimulatedLLMBackend())
    review_prompt = prompt or DEFAULT_REVIEW_PROMPT
    llm_output = llm.execute(
        {
            "prompt": review_prompt,
            "governance_decision": "REVIEW_REQUIRED",
            "artifacts_referenced": [
                f"redaction:{redactor_output.get('input_hash', '')[:16]}",
            ],
        }
    )

    orchestrator = WorkflowOrchestrator(runtime=runtime)
    workflow_output = orchestrator.execute_workflow(redactor_output=redactor_output)

    proposed = workflow_output["proposed_artifact"]
    proposed["artifact_type"] = "ai_governed_redaction_result"
    proposed["output"]["compliance_policy_id"] = DEFAULT_POLICY_AI
    proposed["output"]["llm_governance"] = {
        "agent_id": llm_output.agent_id,
        "decision": llm_output.decision,
        "confidence": llm_output.confidence,
        "cost_usd": llm_output.cost_usd,
        "latency_ms": llm_output.latency_ms,
        "reasoning_summary": llm_output.reasoning_summary[:200],
    }
    proposed["governance_notes"] = (
        "AI governance per APX-WF-AI-001. "
        f"LLM decision: {llm_output.decision}. "
        f"Compliance policy id {DEFAULT_POLICY_AI}."
    )

    coordinator = AttestationCoordinator(runtime=runtime)
    final_output = coordinator.coordinate_attestation(workflow_output=workflow_output)
    attested = final_output["attested_result"]
    attested["compliance_policy_id"] = DEFAULT_POLICY_AI
    attested["llm_decision"] = llm_output.decision
    return attested


__all__ = [
    "PACK_AGENT_IDS",
    "DEFAULT_POLICY_AI",
    "DEFAULT_REVIEW_PROMPT",
    "SAMPLE_INPUT",
    "run_governed_ai_pipeline",
    "RuleGovernedRedactor",
    "WorkflowOrchestrator",
    "AttestationCoordinator",
    "LLMReasoner",
]