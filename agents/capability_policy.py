"""
APXV — Signed Capability Policy (Phase 4 / Step 2)

Versioned, Ed25519-signed capability grants for air-gapped deployments.
Unsigned or tampered policies are rejected at runtime.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import base64
import hashlib
import json
import secrets

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

POLICY_SCHEMA_VERSION = "2.0.0"
SIGNING_CONFIG_VERSION = "1.0.0"
SIGNATURE_ALGORITHM = "Ed25519"


class CapabilityPolicyError(Exception):
    """Raised when a capability policy is invalid or untrusted."""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _signing_body(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in payload.items() if k != "signature"}


def policy_content_hash(payload: Dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k not in ("signature", "content_hash")}
    return hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()


def default_paths(base_path: Path) -> Dict[str, Path]:
    config_dir = base_path / "managed" / "config"
    return {
        "policy": config_dir / "capabilities.json",
        "signing_config": config_dir / "capability_signing.json",
        "private_key": config_dir / "capability_signing.key",
        "history_dir": config_dir / "capability_policy_history",
    }


class CapabilityPolicyManager:
    """Sign, verify, version, and publish local capability policies."""

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = Path(base_path) if base_path else Path(__file__).parent.parent
        self.paths = default_paths(self.base_path)

    def load_signing_config(self) -> Dict[str, Any]:
        path = self.paths["signing_config"]
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def load_private_key(self) -> Optional[Ed25519PrivateKey]:
        key_path = self.paths["private_key"]
        if not key_path.exists():
            return None
        pem = key_path.read_bytes()
        return serialization.load_pem_private_key(pem, password=None)

    def load_public_key(self, signer_id: Optional[str] = None) -> Ed25519PublicKey:
        config = self.load_signing_config()
        signers = config.get("signers", [])
        if not signers:
            raise CapabilityPolicyError("No capability policy signers configured")

        if signer_id:
            match = next((s for s in signers if s.get("id") == signer_id), None)
            if not match:
                raise CapabilityPolicyError(f"Unknown signer id: {signer_id}")
            raw = bytes.fromhex(match["public_key_hex"])
            return Ed25519PublicKey.from_public_bytes(raw)

        active = config.get("active_signer_id") or signers[0]["id"]
        return self.load_public_key(active)

    def ensure_signing_keypair(self) -> Tuple[str, Optional[str]]:
        """
        Create default Ed25519 signer if none exists.
        Returns (signer_id, private_key_pem) — PEM shown once for operator backup.
        """
        if self.paths["signing_config"].exists() and self.paths["private_key"].exists():
            config = self.load_signing_config()
            return config.get("active_signer_id", "default-capability-signer"), None

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

        signer_id = "default-capability-signer"
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
                    "created_at": _utcnow(),
                    "description": "Auto-generated on first policy signing",
                }
            ],
        }
        self.paths["signing_config"].write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )
        return signer_id, private_pem.decode("utf-8")

    def build_policy_document(
        self,
        agents: Dict[str, List[str]],
        *,
        policy_version: int = 1,
        previous_policy_hash: Optional[str] = None,
        issued_by: str = "operator",
        description: str = "Signed local capability policy",
    ) -> Dict[str, Any]:
        normalized_agents = {
            agent_id: sorted(set(caps))
            for agent_id, caps in sorted(agents.items())
        }
        document = {
            "schema_version": POLICY_SCHEMA_VERSION,
            "policy_version": policy_version,
            "deployment": "local-airgapped",
            "description": description,
            "issued_at": _utcnow(),
            "issued_by": issued_by,
            "previous_policy_hash": previous_policy_hash,
            "agents": normalized_agents,
        }
        document["content_hash"] = policy_content_hash(document)
        return document

    def sign_document(
        self,
        document: Dict[str, Any],
        *,
        signer_id: Optional[str] = None,
        private_key: Optional[Ed25519PrivateKey] = None,
    ) -> Dict[str, Any]:
        if private_key is None:
            private_key = self.load_private_key()
        if private_key is None:
            signer_id, _ = self.ensure_signing_keypair()
            private_key = self.load_private_key()
        if private_key is None:
            raise CapabilityPolicyError("Capability signing private key unavailable")

        if signer_id is None:
            signer_id = self.load_signing_config().get("active_signer_id", "default-capability-signer")

        public_key = private_key.public_key()
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

        body = _signing_body(document)
        body["content_hash"] = policy_content_hash(body)
        signature = private_key.sign(_canonical_json(body).encode("utf-8"))

        signed = dict(body)
        signed["signature"] = {
            "algorithm": SIGNATURE_ALGORITHM,
            "signer_id": signer_id,
            "public_key_hex": public_bytes.hex(),
            "value": base64.b64encode(signature).decode("ascii"),
        }
        return signed

    def verify_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        signature = document.get("signature")
        if not signature:
            raise CapabilityPolicyError("Policy is unsigned")

        if signature.get("algorithm") != SIGNATURE_ALGORITHM:
            raise CapabilityPolicyError(f"Unsupported signature algorithm: {signature.get('algorithm')}")

        body = _signing_body(document)
        expected_hash = policy_content_hash(body)
        if body.get("content_hash") != expected_hash:
            raise CapabilityPolicyError("Policy content hash mismatch (document tampered)")

        sig_bytes = base64.b64decode(signature["value"])
        signer_id = signature.get("signer_id")

        if signature.get("public_key_hex"):
            public_key = Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(signature["public_key_hex"])
            )
        else:
            public_key = self.load_public_key(signer_id)

        try:
            public_key.verify(sig_bytes, _canonical_json(body).encode("utf-8"))
        except InvalidSignature as exc:
            raise CapabilityPolicyError("Policy signature verification failed") from exc

        configured = self.load_public_key(signer_id)
        configured_bytes = configured.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        if public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ) != configured_bytes:
            raise CapabilityPolicyError("Policy signer public key does not match local trust store")

        return {
            "valid": True,
            "policy_version": document.get("policy_version"),
            "content_hash": expected_hash,
            "signer_id": signer_id,
            "agent_count": len(document.get("agents", {})),
        }

    def load_policy(self) -> Dict[str, Any]:
        path = self.paths["policy"]
        if not path.exists():
            raise CapabilityPolicyError(f"Capability policy not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def load_verified_policy(self) -> Dict[str, Any]:
        document = self.load_policy()
        self.verify_document(document)
        return document

    def publish_policy(
        self,
        agents: Dict[str, List[str]],
        *,
        issued_by: str = "operator",
        description: str = "Signed local capability policy",
    ) -> Dict[str, Any]:
        self.ensure_signing_keypair()

        previous_hash = None
        next_version = 1
        if self.paths["policy"].exists():
            current = self.load_policy()
            if current.get("signature"):
                try:
                    self.verify_document(current)
                    previous_hash = policy_content_hash(current)
                    next_version = int(current.get("policy_version", 0)) + 1
                except CapabilityPolicyError:
                    if current.get("agents"):
                        previous_hash = policy_content_hash(current)
                        next_version = max(int(current.get("policy_version", 1)), 1)
            elif current.get("agents"):
                previous_hash = current.get("content_hash") or policy_content_hash(current)
                next_version = max(int(current.get("policy_version", 1)), 1)

        document = self.build_policy_document(
            agents,
            policy_version=next_version,
            previous_policy_hash=previous_hash,
            issued_by=issued_by,
            description=description,
        )
        signed = self.sign_document(document)
        self._write_policy(signed)
        return signed

    def migrate_legacy_policy(self) -> Optional[Dict[str, Any]]:
        path = self.paths["policy"]
        if not path.exists():
            return None

        document = json.loads(path.read_text(encoding="utf-8"))
        if document.get("signature"):
            return None
        if "agents" not in document:
            return None

        backup = path.with_suffix(".json.legacy")
        if not backup.exists():
            backup.write_text(json.dumps(document, indent=2), encoding="utf-8")

        signer_id, private_pem = self.ensure_signing_keypair()
        signed = self.publish_policy(
            document["agents"],
            issued_by="migration",
            description="Migrated from unsigned capabilities.json",
        )
        return {"signed_policy": signed, "signer_id": signer_id, "private_key_pem": private_pem}

    def _write_policy(self, signed_document: Dict[str, Any]) -> None:
        path = self.paths["policy"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(signed_document, indent=2), encoding="utf-8")

        history_dir = self.paths["history_dir"]
        history_dir.mkdir(parents=True, exist_ok=True)
        version = signed_document.get("policy_version", 0)
        history_path = history_dir / f"policy-v{version}.json"
        history_path.write_text(json.dumps(signed_document, indent=2), encoding="utf-8")

    def get_status(self) -> Dict[str, Any]:
        status: Dict[str, Any] = {
            "schema_version": POLICY_SCHEMA_VERSION,
            "policy_path": str(self.paths["policy"]),
            "signing_configured": self.paths["signing_config"].exists(),
        }
        if not self.paths["policy"].exists():
            status["loaded"] = False
            status["verified"] = False
            return status

        try:
            document = self.load_policy()
            verification = self.verify_document(document)
            status.update(
                {
                    "loaded": True,
                    "verified": True,
                    "policy_version": verification["policy_version"],
                    "content_hash": verification["content_hash"],
                    "signer_id": verification["signer_id"],
                    "agent_count": verification["agent_count"],
                    "issued_at": document.get("issued_at"),
                    "previous_policy_hash": document.get("previous_policy_hash"),
                }
            )
        except CapabilityPolicyError as exc:
            status.update({"loaded": True, "verified": False, "error": str(exc)})
        return status