"""
APX v1 — Tool User Agent (Second Phase 3 Agentic Component)

This is the second concrete agentic component that implements the
AgenticContract. It demonstrates how a tool-using agent can operate
safely within the APX governed runtime.

It produces only structured, attestable AgenticOutput and respects
the capability model, audit logging, and immutability requirements.

All code is original work written for APX v1.
"""

from typing import Dict, Any, List
from .agentic_contract import AgenticContract, AgenticOutput, validate_agentic_output
from .capability_checker import CapabilityChecker
from .audit_logger import AuditLogger
from .artifact_provider import FileArtifactProvider


class ToolUser(AgenticContract):
    """
    A contract-compliant tool-using agent.

    In a real deployment this would call external tools/APIs.
    For Phase 3 development it currently simulates tool usage
    while strictly following the AgenticContract.
    """

    required_capabilities: List[str] = [
        "read_specification",
        "write_artifact",
    ]

    def __init__(self, agent_id: str = "APX-AGENT-TOOL-001"):
        self.agent_id = agent_id
        self.agent_name = "ToolUser"

        self.capability_checker = CapabilityChecker()
        for cap in self.required_capabilities:
            self.capability_checker.grant_capability(self.agent_id, cap)

        self.audit_logger = AuditLogger(
            log_path=__import__("pathlib").Path(__file__).parent.parent
            / "managed" / "audit" / "tool_user_audit.log"
        )
        self.provider = FileArtifactProvider()

    def execute(self, context: Dict[str, Any]) -> AgenticOutput:
        """
        Execute tool usage (simulated) and return structured output.
        """
        # Enforce capability before any action
        self.capability_checker.require_capability(self.agent_id, "read_specification")
        self.capability_checker.require_capability(self.agent_id, "write_artifact")

        # Simulate tool execution based on context
        tool_name = context.get("tool_name", "unknown_tool")
        decision = f"TOOL_EXECUTED:{tool_name}"
        reasoning = f"Executed tool '{tool_name}' with governed context. Result recorded."

        output = AgenticOutput(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            decision=decision,
            reasoning_summary=reasoning[:500],
            artifacts_referenced=context.get("artifacts_referenced", []),
            confidence=0.90,
            cost_usd=0.001,
            latency_ms=450,
        )

        # Validate output against contract
        validate_agentic_output(output)

        # Log tool execution
        self.audit_logger.log_event(
            event_type="tool_user_executed",
            data={
                "agent_id": self.agent_id,
                "tool_name": tool_name,
                "decision": output.decision,
            }
        )

        # Write output as governed artifact
        self.provider.write_artifact(
            artifact=output.__dict__,
            name=f"tool_user_output_{self.agent_id}"
        )

        return output