"""
APX v1 — Agent 3: AttestationCoordinator

This is the third and final agent in the APX v1 minimal implementation.

Purpose:
- Complete the end-to-end agent pipeline for the tiny APX v1 scope.
- Accept the full output from the WorkflowOrchestrator (Agent 2).
- Simulate the attestation handoff step (real ZK circuits come in Step 5).
- Apply a final governance decision layer drawing from the managed knowledge base.
- Produce a complete, self-contained "AttestedResult" that represents the
  final governed output of the entire 3-agent system.
- Maintain the core APX principle: every agent actively re-reads the living
  markdown specifications (rules, workflow, knowledge) on every execution.

Together with Agent 1 and Agent 2, these three agents form a complete,
demonstrable chain:
  Redaction → Workflow Orchestration + Artifact Packaging → Attestation Coordination

This agent now uses the MinimalArtifactProvider for all specification access.

All code is original work written for APX v1.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import hashlib
import json

from .agent_base import init_agent_context, register_loaded_specs
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .runtime import APXRuntime


class AttestationCoordinator:
    """
    Final agent in the APX v1 pipeline.

    Responsibilities:
    - Drive the attestation coordination phase of APX-WF-001.
    - Perform governance decision based on loaded knowledge.
    - Package the final attested result with full provenance.
    - Prepare the structure that future circuits, scripts, and the
      minimal artifact layer will make fully real.

    Phase 2: Uses FileArtifactProvider and AuditLogger for immutable,
    cryptographically chained operations.
    """

    def __init__(self, base_path: Path = None, runtime: "APXRuntime" = None):
        self.agent_id = "APX-AGENT-003"
        self.agent_name = "AttestationCoordinator"
        ctx = init_agent_context(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            audit_filename="agent3_audit.log",
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

    def _make_governance_decision(self, proposed_artifact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simple governance decision logic based on the loaded knowledge base.

        In a fuller system this would be much richer. For APX v1 tiny scope
        we use a deterministic, auditable rule set derived from APX-KB-001.
        """
        total_redactions = proposed_artifact.get("output", {}).get("total_redactions", 0)
        redaction_categories = [
            r.get("category") for r in proposed_artifact.get("output", {}).get("redactions_applied", [])
        ]

        # Basic governance policy (inspired by the knowledge base we defined)
        if total_redactions == 0:
            decision = "APPROVED_NO_CHANGES"
            rationale = "No sensitive data detected. Output passes all governance checks."
        elif total_redactions <= 5 and "SSN" not in redaction_categories:
            decision = "APPROVED"
            rationale = "Low volume of redactions. No high-sensitivity categories (SSN) present."
        elif "SSN" in redaction_categories or total_redactions > 10:
            decision = "APPROVED_WITH_REVIEW_FLAG"
            rationale = "High-sensitivity data (SSN) or high volume of redactions. Manual review recommended."
        else:
            decision = "APPROVED"
            rationale = "Standard redaction volume. All rules followed."

        return {
            "decision": decision,
            "rationale": rationale,
            "governed_by_knowledge_id": self.knowledge["id"],
            "governed_by_knowledge_hash": self.knowledge["file_hash"],
            "decided_at": datetime.utcnow().isoformat() + "Z",
        }

    def coordinate_attestation(
        self,
        workflow_output: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point for Agent 3.

        Accepts the complete output from WorkflowOrchestrator (Agent 2)
        and produces the final attested result.
        """
        if workflow_output is None:
            raise ValueError("AttestationCoordinator requires workflow_output from Agent 2")

        # === Step 1: Load active specifications (mandatory) ===
        self.load_specifications()

        proposed_artifact = workflow_output.get("proposed_artifact", {})
        attestation_request = workflow_output.get("attestation_request", {})

        # === Governance Decision ===
        governance = self._make_governance_decision(proposed_artifact)

        # === Simulate Attestation / Proof Generation ===
        # In the real system (Step 5 + Step 7) this will call actual ZK circuits.
        # For APX v1 we create a deterministic placeholder that matches the
        # structure the future circuits will produce.
        proof_placeholder = {
            "proof_type": "groth16_placeholder",
            "circuit": attestation_request.get("circuit_hint", "redaction_v1"),
            "proof_hash": hashlib.sha256(
                json.dumps(proposed_artifact, sort_keys=True).encode()
            ).hexdigest()[:32] + "-placeholder",
            "public_inputs": attestation_request.get("public_inputs", {}),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "status": "simulated_proof_ready_for_real_circuit",
        }

        # === Final Attested Result ===
        attested_result = {
            "final_status": "ATTESTED",
            "attestation_id": f"attested-{hashlib.sha256(str(datetime.utcnow()).encode()).hexdigest()[:16]}",
            "completed_at": datetime.utcnow().isoformat() + "Z",
            "agent_chain": [
                "APX-AGENT-001",  # RuleGovernedRedactor
                "APX-AGENT-002",  # WorkflowOrchestrator
                self.agent_id,    # AttestationCoordinator
            ],
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
            "governance_decision": governance,
            "proposed_artifact": proposed_artifact,
            "attestation_request": attestation_request,
            "proof": proof_placeholder,
            "full_provenance_hash": hashlib.sha256(
                json.dumps(
                    {
                        "artifact": proposed_artifact,
                        "governance": governance,
                        "proof": proof_placeholder,
                    },
                    sort_keys=True,
                ).encode()
            ).hexdigest(),
        }

        # Final wrapper
        result = {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "workflow_id": self.workflow["id"],
            "workflow_version": self.workflow["version"],
            "attested_result": attested_result,
            "status": "pipeline_complete",
        }

        return result

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "specifications_loaded": bool(self.rule_set),
            "last_knowledge_version": self.knowledge.get("version"),
        }


# Convenience helper for direct use
def run_attestation_coordinator(
    workflow_output: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Quick entry point to run the final attestation coordination step."""
    coordinator = AttestationCoordinator()
    return coordinator.coordinate_attestation(workflow_output=workflow_output)
