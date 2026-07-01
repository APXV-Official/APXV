"""
APX v1 — LLM Reasoner (Agentic Component)

Contract-compliant LLM agent with pluggable backends.
Plug in Ollama, OpenAI-compatible local servers, or your own LLMBackend.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import concurrent.futures
import os

from .agent_base import init_agent_context
from .agentic_contract import AgenticOutput, validate_agentic_output
from .llm_backend import LLMBackend, SimulatedLLMBackend

if TYPE_CHECKING:
    from .runtime import APXRuntime


class LLMReasoner:
    """
    Governed LLM agent. Uses AgenticContract output shape and APXRuntime wiring.

    Pass any LLMBackend implementation — default is simulated (no external calls).
    """

    required_capabilities: List[str] = [
        "read_specification",
        "write_artifact",
        "execute_agent",
    ]

    def __init__(
        self,
        agent_id: str = "APX-AGENT-LLM-001",
        max_cost_usd: float = 0.05,
        max_latency_ms: int = 5000,
        max_execution_time_seconds: Optional[int] = None,
        backend: Optional[LLMBackend] = None,
        base_path: Optional[Path] = None,
        runtime: Optional["APXRuntime"] = None,
    ):
        self.agent_id = agent_id
        self.agent_name = "LLMReasoner"
        self.max_cost_usd = max_cost_usd
        self.max_latency_ms = max_latency_ms
        if max_execution_time_seconds is None:
            max_execution_time_seconds = int(os.environ.get("APX_LLM_TIMEOUT_SECONDS", "120"))
        self.max_execution_time_seconds = max_execution_time_seconds
        self.backend = backend or SimulatedLLMBackend()

        ctx = init_agent_context(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            audit_filename="llm_reasoner_audit.log",
            base_path=base_path,
            runtime=runtime,
        )
        self.base_path = ctx["base_path"]
        self.provider = ctx["provider"]
        self.audit_logger = ctx["audit_logger"]
        self.capability_checker = ctx["capability_checker"]
        self.runtime = ctx["runtime"]

    def execute(self, context: Dict[str, Any]) -> AgenticOutput:
        self.capability_checker.require_capability(self.agent_id, "read_specification")
        self.capability_checker.require_capability(self.agent_id, "write_artifact")
        self.capability_checker.require_capability(self.agent_id, "execute_agent")

        prompt = context.get("prompt") or context.get("input_text") or ""
        system = context.get("system", "You are a governed APX assistant. Be concise.")
        if not prompt:
            prompt = (
                f"Given governance decision hint '{context.get('governance_decision', 'REVIEW_REQUIRED')}', "
                "recommend APPROVED, REVIEW_REQUIRED, or REJECTED with brief reasoning."
            )

        def _call_backend():
            return self.backend.complete(
                prompt,
                system=system,
                timeout_seconds=self.max_execution_time_seconds,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_call_backend)
            try:
                llm_result = future.result(timeout=self.max_execution_time_seconds + 1)
            except concurrent.futures.TimeoutError as exc:
                raise PermissionError(
                    f"LLM execution exceeded sandbox timeout ({self.max_execution_time_seconds}s)"
                ) from exc

        if llm_result.cost_usd > self.max_cost_usd:
            raise PermissionError(
                f"LLM call would exceed max cost limit (${self.max_cost_usd})"
            )
        if llm_result.latency_ms > self.max_latency_ms:
            raise PermissionError(
                f"LLM call would exceed max latency limit ({self.max_latency_ms}ms)"
            )

        decision = self._extract_decision(llm_result.text, context)
        reasoning = llm_result.text[:500]

        rule_spec = self.provider.read_specification("rule")
        rule_content = rule_spec.get("content", "").lower()
        if "human_review_required" in rule_content and decision != "REVIEW_REQUIRED":
            decision = "REVIEW_REQUIRED"
            reasoning += " [GOVERNANCE RULE ENFORCED: Human review required]"

        output = AgenticOutput(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            decision=decision,
            reasoning_summary=reasoning,
            artifacts_referenced=context.get("artifacts_referenced", []),
            confidence=0.85,
            cost_usd=llm_result.cost_usd,
            latency_ms=llm_result.latency_ms,
        )
        validate_agentic_output(output)

        self.audit_logger.log_event(
            event_type="llm_reasoner_executed",
            data={
                "agent_id": self.agent_id,
                "decision": output.decision,
                "confidence": output.confidence,
                "cost_usd": output.cost_usd,
                "latency_ms": output.latency_ms,
                "backend_model": llm_result.model,
                "sandbox_timeout": self.max_execution_time_seconds,
                "governance_enforced": "human_review_required" in rule_content,
            },
        )

        self.provider.write_artifact(
            artifact=output.__dict__,
            name=f"llm_reasoner_output_{self.agent_id}",
        )
        return output

    @staticmethod
    def _extract_decision(text: str, context: Dict[str, Any]) -> str:
        upper = text.upper()
        for candidate in ("APPROVED", "REJECTED", "REVIEW_REQUIRED"):
            if candidate in upper:
                return candidate
        return context.get("governance_decision", "REVIEW_REQUIRED")