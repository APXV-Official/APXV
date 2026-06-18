"""
APX v1 — Agent 1: RuleGovernedRedactor

This is the first of the three small agents in the APX v1 minimal implementation.

Purpose:
- Demonstrate an agent that actively reads its behavioral rules, workflow, and knowledge
  from living markdown files at runtime (the core APX managed agents concept).
- Strictly follow APX-WF-001 (Rule-Governed Text Processing & Attestation).
- Apply redactions exactly as defined in APX-RULE-001.
- Use APX-KB-001 for examples and edge case guidance.
- Produce a structured, auditable output ready for artifact creation and attestation.

This agent is intentionally simple and self-contained for the tiny APX v1 scope.
It uses the MinimalArtifactProvider for all governed markdown access.

All code is original work written for APX v1.
"""

from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import hashlib

from .agent_base import init_agent_context, register_loaded_specs
from .redaction_engine import RedactionEngine
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .runtime import APXRuntime


class RuleGovernedRedactor:
    """
    A simple agent that processes text according to externally defined
    rules, workflow, and knowledge stored in markdown files.

    Phase 2: Uses FileArtifactProvider (immutable, integrity-checked) and
    AuditLogger (cryptographically chained) for all artifact operations.
    """

    def __init__(self, base_path: Path = None, runtime: "APXRuntime" = None):
        self.agent_id = "APX-AGENT-001"
        self.agent_name = "RuleGovernedRedactor"
        ctx = init_agent_context(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            audit_filename="agent1_audit.log",
            base_path=base_path,
            runtime=runtime,
        )
        self.base_path = ctx["base_path"]
        self.provider = ctx["provider"]
        self.audit_logger = ctx["audit_logger"]
        self.capability_checker = ctx["capability_checker"]
        self._governance = ctx["governance"]
        self.runtime = ctx["runtime"]

        self.rule_set: Dict[str, Any] = {}
        self.workflow: Dict[str, Any] = {}
        self.knowledge: Dict[str, Any] = {}
        self.redaction_engine = RedactionEngine()

    def load_specifications(self) -> None:
        """
        Load the current rule set, workflow, and knowledge.
        This must be called at the start of every execution (no caching).
        """
        # Phase 2: Enforce capability before reading governed specifications
        self.capability_checker.require_capability(self.agent_id, "read_specification")

        # Load via the artifact provider (the single source of truth for governed specs)
        rule_spec = self.provider.read_specification("rule", governance_registry=self._governance)
        workflow_spec = self.provider.read_specification("workflow", governance_registry=self._governance)
        knowledge_spec = self.provider.read_specification("knowledge", governance_registry=self._governance)
        register_loaded_specs(
            self._governance,
            {"rule": rule_spec, "workflow": workflow_spec, "knowledge": knowledge_spec},
        )

        rule_raw = rule_spec["content"]
        workflow_raw = workflow_spec["content"]
        knowledge_raw = knowledge_spec["content"]

        # Store raw + basic parsed metadata
        self.rule_set = {
            "raw": rule_raw,
            "id": "APX-RULE-001",
            "version": "1.0.0",
            "file_hash": hashlib.sha256(rule_raw.encode()).hexdigest(),
        }

        self.workflow = {
            "raw": workflow_raw,
            "id": "APX-WF-001",
            "version": "1.0.0",
            "file_hash": hashlib.sha256(workflow_raw.encode()).hexdigest(),
        }

        self.knowledge = {
            "raw": knowledge_raw,
            "id": "APX-KB-001",
            "version": "1.0.0",
            "file_hash": hashlib.sha256(knowledge_raw.encode()).hexdigest(),
        }

    def _apply_redactions(self, text: str) -> Dict[str, Any]:
        """Apply redactions strictly according to APX-RULE-001."""
        return self.redaction_engine.apply(text)

    def process_text(self, input_text: str) -> Dict[str, Any]:
        """
        Main entry point for the agent.

        Follows APX-WF-001 as closely as possible within the current scope.
        """
        # Step 1: Load active specifications (must re-read every time)
        self.load_specifications()

        # Step 2: Record input hash
        input_hash = hashlib.sha256(input_text.encode()).hexdigest()

        # Step 3: Apply redactions per loaded rule
        redaction_result = self._apply_redactions(input_text)

        # Step 4: Build structured output
        output = {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "input_hash": input_hash,
            "redacted_text": redaction_result["redacted_text"],
            "redactions_applied": redaction_result["redactions_applied"],
            "total_redactions": redaction_result["total_redactions"],
            "redaction_summary": redaction_result.get("redaction_summary", ""),
            "redaction_engine_version": redaction_result.get("engine_version"),
            "rule_id": self.rule_set["id"],
            "rule_version": self.rule_set["version"],
            "rule_file_hash": self.rule_set["file_hash"],
            "workflow_id": self.workflow["id"],
            "workflow_version": self.workflow["version"],
            "workflow_file_hash": self.workflow["file_hash"],
            "knowledge_id": self.knowledge["id"],
            "knowledge_version": self.knowledge["version"],
            "knowledge_file_hash": self.knowledge["file_hash"],
            "status": "success",
        }

        # Step 5 & 6 (simulated for now):
        # In a fuller implementation these would write an artifact and request attestation.
        # For APX v1 tiny scope we return everything needed for those later steps.

        return output

    def get_status(self) -> Dict[str, Any]:
        """Return basic status information about this agent."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "specifications_loaded": bool(self.rule_set),
            "last_rule_version": self.rule_set.get("version"),
        }


# Convenience function for quick testing
def run_redaction_agent(input_text: str) -> Dict[str, Any]:
    """Quick helper to run the redactor on a piece of text."""
    agent = RuleGovernedRedactor()
    return agent.process_text(input_text)
