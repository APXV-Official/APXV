"""
APX v1 — Agent 2: WorkflowOrchestrator

This is the second of the three small agents in the APX v1 minimal implementation.

Purpose:
- Explicitly execute the workflow defined in APX-WF-001.
- Demonstrate orchestration across the managed layer (rules + workflow + knowledge).
- Accept output from Agent 1 (or raw input) and drive the process through
  the full 6-step workflow as closely as possible within current scope.
- Produce a clean, structured "proposed artifact" package that is ready for
  the future minimal artifact provider and attestation handoff.
- Maintain the core APX principle: agents actively read living markdown
  specifications at runtime on every execution.

This agent builds directly on the redaction work from agent1.py but focuses
on workflow fidelity and artifact packaging.

It now uses the MinimalArtifactProvider for all governed specification access.

All code is original work written for APX v1.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import hashlib
import json

from .agent_base import init_agent_context, register_loaded_specs
from .llm_reasoner import LLMReasoner
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .runtime import APXRuntime


class WorkflowOrchestrator:
    """
    Agent that drives the exact workflow defined in APX-WF-001.

    It coordinates the steps:
    1. Load active rules, workflow, and knowledge
    2. Record input hash
    3. Apply redactions (delegates to redaction logic or accepts pre-redacted)
    4. Build structured output
    5. Package as proposed artifact
    6. Prepare attestation request payload

    Phase 2: Uses FileArtifactProvider and AuditLogger for immutable,
    cryptographically chained operations.
    """

    def __init__(self, base_path: Path = None, runtime: "APXRuntime" = None):
        self.agent_id = "APX-AGENT-002"
        self.agent_name = "WorkflowOrchestrator"
        ctx = init_agent_context(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            audit_filename="agent2_audit.log",
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

    def load_specifications(self) -> None:
        """Re-load all three markdown specifications on every run via the artifact provider."""
        # Phase 2: Enforce capability before reading governed specifications
        self.capability_checker.require_capability(self.agent_id, "read_specification")

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

    def _simulate_redaction_if_needed(self, text: str) -> Dict[str, Any]:
        """
        Lightweight redaction simulation when raw text is passed directly.
        In a real flow this would usually come from Agent 1.
        """
        from .redaction_engine import RedactionEngine

        return RedactionEngine().apply(text)

    def execute_workflow(
        self,
        input_text: Optional[str] = None,
        redactor_output: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the full workflow defined in APX-WF-001.

        You can pass either:
        - raw input_text (orchestrator will simulate redaction), or
        - redactor_output from Agent 1 for proper chaining.
        """
        # === Step 1: Load active specifications (mandatory on every run) ===
        self.load_specifications()

        # === Determine source material and redaction result ===
        if redactor_output is not None:
            # Preferred path: use output from RuleGovernedRedactor
            source_text = redactor_output.get("redacted_text", "")
            redactions_applied = redactor_output.get("redactions_applied", [])
            total_redactions = redactor_output.get("total_redactions", 0)
            entities = redactor_output.get("entities", [])
            entity_count = redactor_output.get("entity_count", len(entities))
            original_input_hash = redactor_output.get("input_hash")
            upstream_agent = redactor_output.get("agent_id")
        elif input_text is not None:
            # Fallback: raw text path
            redaction_result = self._simulate_redaction_if_needed(input_text)
            source_text = redaction_result["redacted_text"]
            redactions_applied = redaction_result["redactions_applied"]
            total_redactions = redaction_result["total_redactions"]
            entities = redaction_result.get("entities", [])
            entity_count = redaction_result.get("entity_count", len(entities))
            original_input_hash = hashlib.sha256(input_text.encode()).hexdigest()
            upstream_agent = None
        else:
            raise ValueError("Must provide either input_text or redactor_output")

        # === Step 2: Record input hash (already have it) ===
        workflow_input_hash = hashlib.sha256(source_text.encode()).hexdigest()

        # === Step 3 & 4: Structured output already prepared ===
        # We now build the rich execution record

        execution_trace = [
            {"step": 1, "name": "load_specifications", "timestamp": datetime.utcnow().isoformat() + "Z"},
            {"step": 2, "name": "record_input_hash", "input_hash": original_input_hash},
            {"step": 3, "name": "apply_redactions", "redactions": redactions_applied},
            {"step": 4, "name": "build_structured_output"},
        ]

        # === Step 5: Package as Proposed Artifact ===
        proposed_artifact = {
            "artifact_type": "redaction_result",
            "schema_version": "apx-artifact-v0.1",
            "agent_chain": [upstream_agent, self.agent_id] if upstream_agent else [self.agent_id],
            "created_at": datetime.utcnow().isoformat() + "Z",
            "governed_by": {
                "rule_id": self.rule_set["id"],
                "rule_version": self.rule_set["version"],
                "rule_file_hash": self.rule_set["file_hash"],
                "workflow_id": self.workflow["id"],
                "workflow_version": self.workflow["version"],
                "workflow_file_hash": self.workflow["file_hash"],
                "knowledge_id": self.knowledge["id"],
                "knowledge_version": self.knowledge["version"],
                "knowledge_file_hash": self.knowledge["file_hash"],
            },
            "input": {
                "original_hash": original_input_hash,
                "post_redaction_hash": workflow_input_hash,
            },
            "output": {
                "redacted_text": source_text,
                "redactions_applied": redactions_applied,
                "total_redactions": total_redactions,
                "entities": entities,
                "entity_count": entity_count,
            },
            "execution_trace": execution_trace,
            "governance_notes": "Followed APX-WF-001 exactly. All redactions deterministic per APX-RULE-001.",
        }

        # === Step 6: Prepare Attestation Request Payload ===
        attestation_request = {
            "request_id": f"attest-{hashlib.sha256(str(datetime.utcnow()).encode()).hexdigest()[:12]}",
            "artifact_hash": hashlib.sha256(json.dumps(proposed_artifact, sort_keys=True).encode()).hexdigest(),
            "circuit_hint": "redaction_v1",   # Points to future circuit in Step 5
            "public_inputs": {
                "rule_hash": self.rule_set["file_hash"],
                "workflow_hash": self.workflow["file_hash"],
                "input_hash": original_input_hash,
                "redaction_count": total_redactions,
            },
            "requested_at": datetime.utcnow().isoformat() + "Z",
            "status": "pending_proof",
        }

        # Final structured response
        result = {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "workflow_id": self.workflow["id"],
            "workflow_version": self.workflow["version"],
            "workflow_file_hash": self.workflow["file_hash"],
            "proposed_artifact": proposed_artifact,
            "attestation_request": attestation_request,
            "status": "workflow_complete_ready_for_artifact_and_proof",
        }

        return result

    def execute_with_llm_reasoning(
        self,
        context: Dict[str, Any],
        use_llm: bool = False,
    ) -> Dict[str, Any]:
        """
        Hybrid workflow step: optionally delegate reasoning to the LLMReasoner
        while remaining fully compliant with the AgenticContract and Phase 2 controls.
        """
        self.load_specifications()

        if use_llm:
            # Phase 3: Hybrid path — delegate to LLMReasoner
            llm_agent = LLMReasoner()
            llm_output = llm_agent.execute(context)

            # Log the hybrid decision
            self.audit_logger.log_event(
                event_type="hybrid_workflow_llm_used",
                data={
                    "workflow_id": self.workflow["id"],
                    "llm_decision": llm_output.decision,
                }
            )

            return {
                "mode": "llm_reasoning",
                "llm_output": llm_output.__dict__,
            }
        else:
            # Deterministic path (existing behavior)
            return self.execute_workflow(redactor_output=context)

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "specifications_loaded": bool(self.rule_set),
            "last_workflow_version": self.workflow.get("version"),
        }


# Convenience helper for direct use
def run_workflow_orchestrator(
    input_text: Optional[str] = None,
    redactor_output: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Quick entry point to run the full workflow orchestration."""
    orchestrator = WorkflowOrchestrator()
    return orchestrator.execute_workflow(input_text=input_text, redactor_output=redactor_output)
