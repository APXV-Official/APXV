"""
APXV — Capability-Based Access Control (Phase 2 + Step 2)

Capabilities define what an agent is allowed to do. Grants are loaded from a
signed, versioned policy document. Unsigned or tampered policies are rejected.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Set
import json

from .audit_logger import AuditLogger
from .capability_policy import CapabilityPolicyError, CapabilityPolicyManager
from .id_compat import agent_id_variants


CAPABILITIES = {
    "read_specification",
    "write_artifact",
    "execute_agent",
    "verify_attestation",
    "admin",
}


class CapabilityChecker:
    """Signed-policy capability enforcement for APX agents."""

    def __init__(
        self,
        audit_logger: Optional[AuditLogger] = None,
        policy_path: Optional[Path] = None,
        base_path: Optional[Path] = None,
        require_signed_policy: bool = True,
    ):
        if audit_logger is None:
            root = Path(base_path) if base_path else Path(__file__).parent.parent
            log_path = root / "managed" / "audit" / "capability_checks.log"
            self.audit_logger = AuditLogger(log_path=log_path)
        else:
            self.audit_logger = audit_logger

        self.base_path = Path(base_path) if base_path else Path(__file__).parent.parent
        self.policy_path = policy_path or (self.base_path / "managed" / "config" / "capabilities.json")
        self.require_signed_policy = require_signed_policy
        self.policy_manager = CapabilityPolicyManager(self.base_path)
        self.policy_manager.paths["policy"] = Path(self.policy_path)

        self._agent_capabilities: Dict[str, Set[str]] = {}
        self._policy_document: Optional[Dict[str, Any]] = None
        self._policy_verified = False
        self._policy_error: Optional[str] = None

        self._load_policy()

    def _load_policy(self) -> None:
        if not self.policy_path.exists():
            self._policy_error = f"Policy file not found: {self.policy_path}"
            return

        try:
            document = json.loads(self.policy_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            self._policy_error = f"Failed to read policy: {exc}"
            return

        if not document.get("signature"):
            if self.require_signed_policy:
                migrated = self.policy_manager.migrate_legacy_policy()
                if migrated is None:
                    self._policy_error = "Unsigned capability policy rejected"
                    return
                document = migrated["signed_policy"]
                if migrated.get("private_key_pem"):
                    self.audit_logger.log_event(
                        event_type="capability_signing_key_created",
                        data={"signer_id": migrated["signer_id"]},
                    )
            else:
                self._apply_agents(document.get("agents", {}))
                self._policy_document = document
                self._policy_verified = False
                return

        try:
            verification = self.policy_manager.verify_document(document)
        except CapabilityPolicyError as exc:
            self._policy_error = str(exc)
            self.audit_logger.log_event(
                event_type="capability_policy_rejected",
                data={"error": str(exc)},
            )
            return

        self._apply_agents(document.get("agents", {}))
        self._policy_document = document
        self._policy_verified = True
        self._policy_error = None
        self.audit_logger.log_event(
            event_type="capability_policy_loaded",
            data={
                "policy_version": verification["policy_version"],
                "content_hash": verification["content_hash"],
                "signer_id": verification["signer_id"],
            },
        )

    def _apply_agents(self, agents: Dict[str, Any]) -> None:
        self._agent_capabilities = {}
        for agent_id, caps in agents.items():
            self._agent_capabilities[agent_id] = set(caps)

    def is_policy_trusted(self) -> bool:
        if not self.require_signed_policy:
            return True
        return self._policy_verified

    def require_trusted_policy(self) -> None:
        if not self.is_policy_trusted():
            raise CapabilityPolicyError(
                self._policy_error or "Capability policy is not trusted"
            )

    def publish_policy(
        self,
        *,
        issued_by: str = "operator",
        description: str = "Updated signed capability policy",
    ) -> Dict[str, Any]:
        """Sign and persist the current in-memory grants as a new policy version."""
        self.require_trusted_policy()
        agents = {
            agent_id: sorted(caps)
            for agent_id, caps in sorted(self._agent_capabilities.items())
        }
        signed = self.policy_manager.publish_policy(
            agents,
            issued_by=issued_by,
            description=description,
        )
        self._policy_document = signed
        self._policy_verified = True
        self.audit_logger.log_event(
            event_type="capability_policy_published",
            data={
                "policy_version": signed.get("policy_version"),
                "content_hash": signed.get("content_hash"),
            },
        )
        return signed

    def grant_capability(self, agent_id: str, capability: str, persist: bool = False) -> None:
        self.require_trusted_policy()

        if capability not in CAPABILITIES:
            raise ValueError(f"Unknown capability: {capability}. Valid: {CAPABILITIES}")

        if agent_id not in self._agent_capabilities:
            self._agent_capabilities[agent_id] = set()

        self._agent_capabilities[agent_id].add(capability)
        self.audit_logger.log_event(
            event_type="capability_granted",
            data={"agent_id": agent_id, "capability": capability},
        )
        if persist:
            self.publish_policy(description=f"Granted {capability} to {agent_id}")

    def has_capability(self, agent_id: str, capability: str) -> bool:
        if self.require_signed_policy and not self._policy_verified:
            self.audit_logger.log_event(
                event_type="capability_check",
                data={
                    "agent_id": agent_id,
                    "capability": capability,
                    "result": "denied_untrusted_policy",
                },
            )
            return False

        caps: Set[str] = set()
        for variant in agent_id_variants(agent_id):
            caps.update(self._agent_capabilities.get(variant, set()))
        has_cap = capability in caps
        self.audit_logger.log_event(
            event_type="capability_check",
            data={
                "agent_id": agent_id,
                "capability": capability,
                "result": "granted" if has_cap else "denied",
            },
        )
        return has_cap

    def require_capability(self, agent_id: str, capability: str) -> None:
        if self.require_signed_policy and not self._policy_verified:
            raise CapabilityPolicyError(
                self._policy_error or "Capability policy is not trusted"
            )
        if not self.has_capability(agent_id, capability):
            raise PermissionError(
                f"Agent '{agent_id}' does not have required capability '{capability}'"
            )

    def get_agent_capabilities(self, agent_id: str) -> Set[str]:
        caps: Set[str] = set()
        for variant in agent_id_variants(agent_id):
            caps.update(self._agent_capabilities.get(variant, set()))
        return caps.copy()

    def get_status(self) -> Dict[str, Any]:
        policy_status = self.policy_manager.get_status()
        return {
            "total_agents": len(self._agent_capabilities),
            "defined_capabilities": sorted(CAPABILITIES),
            "policy_verified": self._policy_verified,
            "policy_error": self._policy_error,
            "policy_version": (self._policy_document or {}).get("policy_version"),
            "policy_content_hash": (self._policy_document or {}).get("content_hash"),
            "policy": policy_status,
            "audit_logger": self.audit_logger.get_status(),
        }