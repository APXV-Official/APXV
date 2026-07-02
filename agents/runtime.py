"""
APX v1 — Local Governed Runtime (Phase 2)

Unified runtime for air-gapped, self-hosted APX deployments.
No cloud services, no external network dependencies.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from .artifact_provider import SqliteArtifactProvider
from .audit_logger import AuditLogger
from .backup_restore import BackupManager
from .capability_checker import CapabilityChecker
from .governance import GovernanceRegistry
from .store import SqliteArtifactStore


DEFAULT_RUNTIME_CONFIG = {
    "version": "2.0.0",
    "deployment": "local-airgapped",
    "store_backend": "sqlite+cas",
    "require_network": False,
}


class APXRuntime:
    """
    Production governed runtime context.

    Wires together:
    - SQLite content-addressable artifact store
    - Cryptographically chained system audit log
    - Persistent local capability policy
    - Governance specification registry
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = Path(base_path) if base_path else Path(__file__).parent.parent
        self.config_path = self.base_path / "managed" / "config"
        self.config_path.mkdir(parents=True, exist_ok=True)

        self.runtime_config = self._load_runtime_config()
        self.store = SqliteArtifactStore(self.base_path)
        self.provider = SqliteArtifactProvider(self.base_path, store=self.store)

        system_log = self.base_path / "managed" / "audit" / "system_audit.log"
        self.system_audit = AuditLogger(log_path=system_log)

        policy_path = self.config_path / "capabilities.json"
        self.capability_checker = CapabilityChecker(
            audit_logger=self.system_audit,
            policy_path=policy_path,
            base_path=self.base_path,
            require_signed_policy=True,
        )
        self.governance = GovernanceRegistry(
            store=self.store,
            audit_logger=self.system_audit,
            base_path=self.base_path,
        )
        self.backup_manager = BackupManager(
            base_path=self.base_path,
            audit_logger=self.system_audit,
        )

        migrated = self.store.migrate_legacy_artifacts()
        if migrated:
            self.system_audit.log_event(
                event_type="legacy_artifacts_migrated",
                data={"count": migrated},
            )

        self.system_audit.log_event(
            event_type="runtime_initialized",
            data={
                "deployment": self.runtime_config.get("deployment"),
                "store_backend": self.runtime_config.get("store_backend"),
            },
        )

    def _load_runtime_config(self) -> Dict[str, Any]:
        path = self.config_path / "runtime.json"
        if not path.exists():
            path.write_text(json.dumps(DEFAULT_RUNTIME_CONFIG, indent=2), encoding="utf-8")
            return DEFAULT_RUNTIME_CONFIG.copy()
        return json.loads(path.read_text(encoding="utf-8"))

    def verify_integrity(self) -> Dict[str, Any]:
        audit_logs = [
            self.base_path / "managed" / "audit" / "system_audit.log",
            self.base_path / "managed" / "audit" / "agent1_audit.log",
            self.base_path / "managed" / "audit" / "agent2_audit.log",
            self.base_path / "managed" / "audit" / "agent3_audit.log",
            self.base_path / "managed" / "audit" / "capability_checks.log",
        ]
        audit_results: Dict[str, bool] = {}
        audit_log_details: Dict[str, Dict[str, Any]] = {}
        audit_summary: Dict[str, Dict[str, Any]] = {}
        recovery_hints: List[str] = []

        for log_path in audit_logs:
            if not log_path.exists():
                continue
            logger = AuditLogger(log_path=log_path)
            detail = logger.get_status()
            name = log_path.name
            audit_results[name] = detail["chain_valid"] and detail["corrupt_line_count"] == 0
            audit_log_details[name] = detail
            audit_summary[name] = {
                "chain_valid": detail["chain_valid"],
                "corrupt_line_count": detail["corrupt_line_count"],
                "entry_count": detail["entry_count"],
                "issue": detail["issue"],
            }
            hint = detail.get("recovery_hint")
            if hint and hint not in recovery_hints:
                recovery_hints.append(hint)

        store_chain = self.store.verify_artifact_chain()
        policy_trusted = self.capability_checker.is_policy_trusted()
        governance_verification = self.governance.approval.verify_active_specs()
        healthy = (
            store_chain["valid"]
            and all(audit_results.values())
            and policy_trusted
            and governance_verification["valid"]
        )
        return {
            "store_chain_valid": store_chain["valid"],
            "store_issues": store_chain.get("issues", []),
            "audit_logs": audit_results,
            "audit_log_details": audit_log_details,
            "audit_summary": audit_summary,
            "recovery_hints": recovery_hints,
            "all_audit_valid": all(audit_results.values()) if audit_results else True,
            "capability_policy_trusted": policy_trusted,
            "capability_policy_error": self.capability_checker.get_status().get("policy_error"),
            "governance_approvals_valid": governance_verification["valid"],
            "governance_approval_issues": governance_verification.get("issues", []),
            "healthy": healthy,
        }

    def get_status(self) -> Dict[str, Any]:
        integrity = self.verify_integrity()
        return {
            "runtime_version": self.runtime_config.get("version"),
            "deployment": self.runtime_config.get("deployment"),
            "air_gapped": True,
            "store": self.store.get_status(),
            "governance": self.governance.get_status(),
            "capabilities": self.capability_checker.get_status(),
            "backups": self.backup_manager.list_backups()[:5],
            "integrity": integrity,
        }