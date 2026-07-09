"""
APXV — Governance Registry (Phase 2 + Step 3)

Tracks versioned governance specifications and enforces the approval
workflow before agents consume active specs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .audit_logger import AuditLogger
from .governance_approval import GovernanceApprovalError, GovernanceApprovalWorkflow
from .store import SqliteArtifactStore


class GovernanceRegistry:
    """Registers governed specifications and manages change approval."""

    def __init__(
        self,
        store: SqliteArtifactStore,
        audit_logger: AuditLogger,
        base_path: Optional[Path] = None,
    ):
        self.store = store
        self.audit_logger = audit_logger
        self.base_path = base_path or store.base_path
        self.approval = GovernanceApprovalWorkflow(
            store=store,
            base_path=self.base_path,
            audit_logger=audit_logger,
        )

    def require_approved_specs(self) -> None:
        self.approval.require_approved_specs()

    def propose_change(
        self,
        spec_type: str,
        content: str,
        *,
        proposed_by: str = "operator",
        summary: str = "",
    ) -> Dict[str, Any]:
        return self.approval.propose_change(
            spec_type,
            content,
            proposed_by=proposed_by,
            summary=summary,
        )

    def approve_proposal(self, proposal_id: str, *, approved_by: str = "operator") -> Dict[str, Any]:
        return self.approval.approve_proposal(proposal_id, approved_by=approved_by)

    def reject_proposal(
        self,
        proposal_id: str,
        *,
        rejected_by: str = "operator",
        reason: str = "",
    ) -> Dict[str, Any]:
        return self.approval.reject_proposal(proposal_id, rejected_by=rejected_by, reason=reason)

    def apply_proposal(self, proposal_id: str) -> Dict[str, Any]:
        result = self.approval.apply_proposal(proposal_id)
        spec = self._read_spec_metadata(result["spec_type"])
        self.register_specification(spec)
        return result

    def list_proposals(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.approval.list_proposals(limit=limit)

    def get_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        return self.approval.get_proposal(proposal_id)

    def _read_spec_metadata(self, spec_type: str) -> Dict[str, Any]:
        from .artifact_provider import SqliteArtifactProvider

        provider = SqliteArtifactProvider(self.base_path, store=self.store)
        return provider.read_specification(spec_type, require_approval=False)

    def register_specification(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        result = self.store.register_governance_spec(
            spec_type=spec["spec_type"],
            spec_id=spec.get("id", f"APX-{spec['spec_type'].upper()}-001"),
            version=spec.get("version", "1.0.0"),
            content_hash=spec["hash"],
            file_path=spec.get("file_path", ""),
        )
        if result.get("changed"):
            self.audit_logger.log_event(
                event_type="governance_spec_changed",
                data=result,
            )
        return result

    def get_active_specs(self) -> Dict[str, Any]:
        specs = self.store.list_governance_specs()
        return {row["spec_type"]: dict(row) for row in specs}

    def get_status(self) -> Dict[str, Any]:
        return {
            "active_specs": self.get_active_specs(),
            "spec_types_tracked": ["rule", "workflow", "knowledge"],
            "approval": self.approval.get_status(),
        }