"""
APX v1 — Governance Change Approval Workflow (Phase 4 / Step 3)

Propose → approve (signed) → apply. Direct spec edits without approval
are rejected at runtime.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import base64
import hashlib
import json
import uuid

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .store import SqliteArtifactStore

GOVERNANCE_SCHEMA_VERSION = "1.0.0"
SIGNING_CONFIG_VERSION = "1.0.0"
SIGNATURE_ALGORITHM = "Ed25519"

SPEC_TYPES = ("rule", "workflow", "knowledge")
SPEC_PATHS = {
    "rule": "rules/rule1.md",
    "workflow": "workflows/workflow1.md",
    "knowledge": "knowledge/knowledge1.md",
}

PROPOSAL_STATUSES = ("proposed", "approved", "applied", "rejected")


class GovernanceApprovalError(Exception):
    """Raised when a governance change is not approved or trusted."""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _signing_body(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in payload.items() if k != "signature"}


def approval_content_hash(payload: Dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k not in ("signature", "content_hash")}
    return hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()


def default_paths(base_path: Path) -> Dict[str, Path]:
    config_dir = base_path / "managed" / "config"
    return {
        "signing_config": config_dir / "governance_signing.json",
        "private_key": config_dir / "governance_signing.key",
        "proposals_dir": base_path / "managed" / "governance" / "proposals",
    }


class GovernanceSigning:
    """Ed25519 signing for governance approvals."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.paths = default_paths(base_path)

    def load_signing_config(self) -> Dict[str, Any]:
        path = self.paths["signing_config"]
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def load_private_key(self) -> Optional[Ed25519PrivateKey]:
        key_path = self.paths["private_key"]
        if not key_path.exists():
            return None
        return serialization.load_pem_private_key(key_path.read_bytes(), password=None)

    def load_public_key(self, signer_id: Optional[str] = None) -> Ed25519PublicKey:
        config = self.load_signing_config()
        signers = config.get("signers", [])
        if not signers:
            raise GovernanceApprovalError("No governance approvers configured")

        if signer_id:
            match = next((s for s in signers if s.get("id") == signer_id), None)
            if not match:
                raise GovernanceApprovalError(f"Unknown approver id: {signer_id}")
            return Ed25519PublicKey.from_public_bytes(bytes.fromhex(match["public_key_hex"]))

        active = config.get("active_signer_id") or signers[0]["id"]
        return self.load_public_key(active)

    def ensure_signing_keypair(self) -> Tuple[str, Optional[str]]:
        if self.paths["signing_config"].exists() and self.paths["private_key"].exists():
            config = self.load_signing_config()
            return config.get("active_signer_id", "default-governance-approver"), None

        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        signer_id = "default-governance-approver"
        self.paths["private_key"].parent.mkdir(parents=True, exist_ok=True)
        self.paths["private_key"].write_bytes(private_pem)

        config = {
            "version": SIGNING_CONFIG_VERSION,
            "deployment": "local-airgapped",
            "active_signer_id": signer_id,
            "signers": [
                {
                    "id": signer_id,
                    "public_key_hex": public_bytes.hex(),
                    "role": "governance_approver",
                    "created_at": _utcnow(),
                    "description": "Auto-generated on first governance approval",
                }
            ],
        }
        self.paths["signing_config"].write_text(json.dumps(config, indent=2), encoding="utf-8")
        return signer_id, private_pem.decode("utf-8")

    def sign_approval(self, approval_record: Dict[str, Any]) -> Dict[str, Any]:
        self.ensure_signing_keypair()
        private_key = self.load_private_key()
        if private_key is None:
            raise GovernanceApprovalError("Governance signing private key unavailable")

        config = self.load_signing_config()
        signer_id = config.get("active_signer_id", "default-governance-approver")
        public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

        body = _signing_body(approval_record)
        body["content_hash"] = approval_content_hash(body)
        signature = private_key.sign(_canonical_json(body).encode("utf-8"))

        signed = dict(body)
        signed["signature"] = {
            "algorithm": SIGNATURE_ALGORITHM,
            "signer_id": signer_id,
            "public_key_hex": public_bytes.hex(),
            "value": base64.b64encode(signature).decode("ascii"),
        }
        return signed

    def verify_approval(self, approval_record: Dict[str, Any]) -> Dict[str, Any]:
        signature = approval_record.get("signature")
        if not signature:
            raise GovernanceApprovalError("Governance approval is unsigned")

        body = _signing_body(approval_record)
        expected_hash = approval_content_hash(body)
        if body.get("content_hash") != expected_hash:
            raise GovernanceApprovalError("Approval content hash mismatch")

        sig_bytes = base64.b64decode(signature["value"])
        if signature.get("public_key_hex"):
            public_key = Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(signature["public_key_hex"])
            )
        else:
            public_key = self.load_public_key(signature.get("signer_id"))

        try:
            public_key.verify(sig_bytes, _canonical_json(body).encode("utf-8"))
        except InvalidSignature as exc:
            raise GovernanceApprovalError("Governance approval signature invalid") from exc

        configured = self.load_public_key(signature.get("signer_id"))
        if public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ) != configured.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ):
            raise GovernanceApprovalError("Approver public key does not match local trust store")

        return {
            "valid": True,
            "proposal_id": body.get("proposal_id"),
            "content_hash": expected_hash,
            "signer_id": signature.get("signer_id"),
        }


class GovernanceApprovalWorkflow:
    """Propose, approve, and apply governed specification changes."""

    def __init__(
        self,
        store: SqliteArtifactStore,
        base_path: Optional[Path] = None,
        audit_logger: Any = None,
    ):
        self.store = store
        self.base_path = Path(base_path) if base_path else store.base_path
        self.managed_path = self.base_path / "managed"
        self.signing = GovernanceSigning(self.base_path)
        self.paths = default_paths(self.base_path)
        self.audit_logger = audit_logger
        self._ensure_schema()
        self.bootstrap_active_specs_if_needed()

    def _ensure_schema(self) -> None:
        self.store.ensure_governance_approval_schema()

    def _log(self, event_type: str, data: Dict[str, Any]) -> None:
        if self.audit_logger is not None:
            self.audit_logger.log_event(event_type=event_type, data=data)

    def _spec_file_path(self, spec_type: str) -> Path:
        if spec_type not in SPEC_PATHS:
            raise ValueError(f"Unknown spec type: {spec_type}")
        return self.managed_path / SPEC_PATHS[spec_type]

    def _read_spec_content(self, spec_type: str) -> str:
        path = self._spec_file_path(spec_type)
        if not path.exists():
            raise FileNotFoundError(f"Specification not found: {path}")
        return path.read_text(encoding="utf-8")

    def _content_hash(self, content: str) -> str:
        return SqliteArtifactStore.compute_hash(content)

    def bootstrap_active_specs_if_needed(self) -> List[Dict[str, Any]]:
        bootstrapped = []
        for spec_type in SPEC_TYPES:
            if self.store.get_active_approval(spec_type):
                continue
            try:
                content = self._read_spec_content(spec_type)
            except FileNotFoundError:
                continue
            content_hash = self._content_hash(content)
            proposal_id = f"bootstrap-{spec_type}"
            self.store.set_active_approval(
                spec_type=spec_type,
                content_hash=content_hash,
                proposal_id=proposal_id,
                approved_at=_utcnow(),
                applied_at=_utcnow(),
            )
            bootstrapped.append(
                {"spec_type": spec_type, "proposal_id": proposal_id, "content_hash": content_hash}
            )
            self._log(
                "governance_spec_bootstrapped",
                {"spec_type": spec_type, "content_hash": content_hash},
            )
        return bootstrapped

    def verify_active_specs(self) -> Dict[str, Any]:
        issues = []
        approvals = {}
        for spec_type in SPEC_TYPES:
            active = self.store.get_active_approval(spec_type)
            if not active:
                issues.append(f"No approved baseline for {spec_type}")
                continue
            try:
                current_hash = self._content_hash(self._read_spec_content(spec_type))
            except FileNotFoundError:
                issues.append(f"Active spec file missing for {spec_type}")
                continue
            approved_hash = active["content_hash"]
            approvals[spec_type] = {
                "approved_hash": approved_hash,
                "current_hash": current_hash,
                "proposal_id": active["proposal_id"],
                "matches": current_hash == approved_hash,
            }
            if current_hash != approved_hash:
                issues.append(
                    f"{spec_type}: unapproved change detected "
                    f"(approved={approved_hash[:12]}..., current={current_hash[:12]}...)"
                )

        return {
            "valid": len(issues) == 0,
            "approvals": approvals,
            "issues": issues,
        }

    def require_approved_specs(self) -> None:
        result = self.verify_active_specs()
        if not result["valid"]:
            raise GovernanceApprovalError("; ".join(result["issues"]))

    def propose_change(
        self,
        spec_type: str,
        content: str,
        *,
        proposed_by: str = "operator",
        summary: str = "",
    ) -> Dict[str, Any]:
        if spec_type not in SPEC_TYPES:
            raise ValueError(f"Unknown spec type: {spec_type}")

        current_hash = None
        try:
            current_hash = self._content_hash(self._read_spec_content(spec_type))
        except FileNotFoundError:
            pass

        content_hash = self._content_hash(content)
        if current_hash == content_hash:
            raise GovernanceApprovalError("Proposed content is identical to the active specification")

        proposal_id = f"gov-{uuid.uuid4().hex[:12]}"
        self.paths["proposals_dir"].mkdir(parents=True, exist_ok=True)
        rel_path = f"governance/proposals/{proposal_id}.md"
        proposal_path = self.base_path / "managed" / rel_path
        proposal_path.write_text(content, encoding="utf-8")

        record = self.store.create_governance_proposal(
            proposal_id=proposal_id,
            spec_type=spec_type,
            content_hash=content_hash,
            proposed_content_relpath=rel_path,
            proposed_by=proposed_by,
            summary=summary,
            current_content_hash=current_hash,
        )
        self._log(
            "governance_change_proposed",
            {
                "proposal_id": proposal_id,
                "spec_type": spec_type,
                "proposed_by": proposed_by,
                "content_hash": content_hash,
                "summary": summary,
            },
        )
        return record

    def approve_proposal(
        self,
        proposal_id: str,
        *,
        approved_by: str = "operator",
    ) -> Dict[str, Any]:
        proposal = self.store.get_governance_proposal(proposal_id)
        if not proposal:
            raise GovernanceApprovalError(f"Proposal not found: {proposal_id}")
        if proposal["status"] != "proposed":
            raise GovernanceApprovalError(f"Proposal {proposal_id} is not awaiting approval")

        approval_record = {
            "schema_version": GOVERNANCE_SCHEMA_VERSION,
            "proposal_id": proposal_id,
            "spec_type": proposal["spec_type"],
            "proposal_content_hash": proposal["content_hash"],
            "approved_by": approved_by,
            "approved_at": _utcnow(),
        }
        signed = self.signing.sign_approval(approval_record)
        updated = self.store.update_governance_proposal(
            proposal_id,
            status="approved",
            approved_by=approved_by,
            approved_at=signed["approved_at"],
            approval_signature=json.dumps(signed),
        )
        self._log(
            "governance_change_approved",
            {
                "proposal_id": proposal_id,
                "spec_type": proposal["spec_type"],
                "approved_by": approved_by,
                "signer_id": signed["signature"]["signer_id"],
            },
        )
        return {"proposal": updated, "approval": signed}

    def reject_proposal(
        self,
        proposal_id: str,
        *,
        rejected_by: str = "operator",
        reason: str = "",
    ) -> Dict[str, Any]:
        proposal = self.store.get_governance_proposal(proposal_id)
        if not proposal:
            raise GovernanceApprovalError(f"Proposal not found: {proposal_id}")
        if proposal["status"] != "proposed":
            raise GovernanceApprovalError(f"Proposal {proposal_id} cannot be rejected in status {proposal['status']}")

        updated = self.store.update_governance_proposal(
            proposal_id,
            status="rejected",
            rejected_by=rejected_by,
            rejected_at=_utcnow(),
            rejection_reason=reason,
        )
        self._log(
            "governance_change_rejected",
            {
                "proposal_id": proposal_id,
                "spec_type": proposal["spec_type"],
                "rejected_by": rejected_by,
                "reason": reason,
            },
        )
        return updated

    def apply_proposal(self, proposal_id: str) -> Dict[str, Any]:
        proposal = self.store.get_governance_proposal(proposal_id)
        if not proposal:
            raise GovernanceApprovalError(f"Proposal not found: {proposal_id}")
        if proposal["status"] != "approved":
            raise GovernanceApprovalError(f"Proposal {proposal_id} must be approved before apply")

        if not proposal.get("approval_signature"):
            raise GovernanceApprovalError(f"Proposal {proposal_id} has no approval signature")

        signed = json.loads(proposal["approval_signature"])
        self.signing.verify_approval(signed)
        if signed.get("proposal_content_hash") != proposal["content_hash"]:
            raise GovernanceApprovalError("Approval signature does not match proposal content")

        proposal_path = self.base_path / "managed" / proposal["proposed_content_relpath"]
        if not proposal_path.exists():
            raise GovernanceApprovalError(f"Proposal content missing: {proposal_path}")

        content = proposal_path.read_text(encoding="utf-8")
        if self._content_hash(content) != proposal["content_hash"]:
            raise GovernanceApprovalError("Proposal content hash mismatch")

        target = self._spec_file_path(proposal["spec_type"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

        applied_at = _utcnow()
        self.store.set_active_approval(
            spec_type=proposal["spec_type"],
            content_hash=proposal["content_hash"],
            proposal_id=proposal_id,
            approved_at=proposal.get("approved_at") or applied_at,
            applied_at=applied_at,
        )
        updated = self.store.update_governance_proposal(
            proposal_id,
            status="applied",
            applied_at=applied_at,
            applied_content_hash=proposal["content_hash"],
        )
        self._log(
            "governance_change_applied",
            {
                "proposal_id": proposal_id,
                "spec_type": proposal["spec_type"],
                "content_hash": proposal["content_hash"],
                "target": str(target.relative_to(self.base_path)).replace("\\", "/"),
            },
        )
        return updated

    def list_proposals(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.store.list_governance_proposals(limit=limit)

    def get_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        return self.store.get_governance_proposal(proposal_id)

    def get_status(self) -> Dict[str, Any]:
        verification = self.verify_active_specs()
        return {
            "schema_version": GOVERNANCE_SCHEMA_VERSION,
            "spec_types": list(SPEC_TYPES),
            "active_approvals": {
                spec: self.store.get_active_approval(spec) for spec in SPEC_TYPES
            },
            "verification": verification,
            "pending_proposals": len(
                [p for p in self.store.list_governance_proposals(limit=100) if p["status"] == "proposed"]
            ),
            "signing_configured": self.paths["signing_config"].exists(),
        }