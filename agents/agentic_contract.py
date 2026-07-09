"""
APXV — Agentic Contract (Phase 3 Foundation)

This module defines the mandatory contract that any LLM-powered or
tool-using agent must follow to operate within the APX governed runtime.

The contract ensures that agentic components remain attestable,
auditable, and constrained — preserving the integrity of the
deterministic core established in Phases 1 and 2.

All code is original work written for APXV.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Protocol
from datetime import datetime, timezone


@dataclass
class AgenticOutput:
    """
    Mandatory structured output format for any agentic component.

    Every LLM or tool-using agent must return an object of this type.
    The output is then written through FileArtifactProvider and
    must carry full provenance.
    """
    agent_id: str
    agent_name: str
    decision: str
    reasoning_summary: str
    artifacts_referenced: List[str] = field(default_factory=list)
    confidence: float = 0.0
    cost_usd: float = 0.0
    latency_ms: int = 0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )


class AgenticContract(Protocol):
    """
    Interface that all agentic components must implement.

    Requirements:
    - Must declare required capabilities
    - Must produce AgenticOutput (never raw text or unstructured data)
    - Must log every execution via AuditLogger
    - Must only write outputs via FileArtifactProvider
    """

    required_capabilities: List[str]

    def execute(self, context: Dict[str, Any]) -> AgenticOutput:
        """
        Execute the agentic logic and return a structured, attestable output.

        Args:
            context: Input context (must come from governed specifications or prior artifacts)

        Returns:
            AgenticOutput — strictly structured and attestable
        """
        ...


# Pre-defined capability sets for common agentic roles
AGENTIC_CAPABILITY_SETS = {
    "llm_reasoner": [
        "read_specification",
        "write_artifact",
        "execute_agent",
    ],
    "tool_user": [
        "read_specification",
        "write_artifact",
    ],
    "hybrid_agent": [
        "read_specification",
        "write_artifact",
        "execute_agent",
        "verify_attestation",
    ],
}


def validate_agentic_output(output: AgenticOutput) -> bool:
    """
    Basic validation that an AgenticOutput meets the contract requirements.

    Returns True if valid, raises ValueError otherwise.
    """
    if not output.agent_id or not output.agent_name:
        raise ValueError("AgenticOutput must include agent_id and agent_name")

    if not output.decision:
        raise ValueError("AgenticOutput must include a decision")

    if not (0.0 <= output.confidence <= 1.0):
        raise ValueError("Confidence must be between 0.0 and 1.0")

    if output.cost_usd < 0 or output.latency_ms < 0:
        raise ValueError("Cost and latency cannot be negative")

    return True